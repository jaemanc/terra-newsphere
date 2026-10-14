"""GDELT discovery + optional, explicitly configured publisher RSS metadata."""
import json
import logging
import os
import signal
import time
import zipfile
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from urllib.parse import urlsplit

import feedparser
import httpx
from kafka import KafkaProducer
from redis import Redis

from terra_newsphere.models import RETENTION_SECONDS, article_id, canonical_url
from terra_newsphere.geography import Geography
from collector.gkg import enrich_locations

log = logging.getLogger("collector")
running = True


class GdeltRateLimited(ValueError):
    """GDELT can return its throttle notice with HTTP 200 instead of 429."""

    def __init__(self, response: httpx.Response):
        super().__init__("GDELT DOC rate limited")
        self.retry_after = 5
        header = response.headers.get("Retry-After", "")
        try:
            self.retry_after = max(5, int(header))
        except ValueError:
            try:
                deadline = parsedate_to_datetime(header)
                if deadline.tzinfo is not None:
                    self.retry_after = max(5, (deadline - datetime.now(timezone.utc)).total_seconds())
            except (ValueError, TypeError, OverflowError):
                pass


def gdelt(client: httpx.Client, query: str) -> list[dict]:
    response = client.get("https://api.gdeltproject.org/api/v2/doc/doc", params={
        "query": query, "mode": "artlist", "format": "json", "maxrecords": 100,
        "timespan": "1h", "sort": "datedesc"})
    if response.status_code == 429:
        raise GdeltRateLimited(response)
    response.raise_for_status()
    try:
        payload = response.json()
    except ValueError:
        if response.text.strip().lower().startswith("please limit requests to one every"):
            raise GdeltRateLimited(response) from None
        raise ValueError("GDELT DOC returned a non-JSON response") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("articles"), list):
        notice = (payload.get("message") or payload.get("error")) if isinstance(payload, dict) else None
        if isinstance(notice, str) and notice.strip().lower().startswith("please limit requests to one every"):
            raise GdeltRateLimited(response)
        raise ValueError("GDELT DOC returned an invalid article response")
    events = []
    for item in payload["articles"]:
        try:
            discovered = datetime.strptime(item["seendate"], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            events.append({"source": {"provider": "GDELT", "publisher": item.get("domain") or
                                      urlsplit(item["url"]).hostname, "url": item["url"]},
                           "content": {"title": item["title"], "language": item.get("language") or "und"},
                           # seendate is discovery time, not article publication time.
                           "published_at": None, "source_discovered_at": discovered.isoformat(),
                           "location_references": [],
                           "publisher_country": item.get("sourcecountry")})
        except (KeyError, ValueError):
            log.warning("Skipped malformed GDELT metadata")
    # DOC sourcecountry is the publisher location. Never turn it into an event marker.
    # socialimage is intentionally omitted: GDELT discovery does not license thumbnails.
    return events


def rss(client: httpx.Client, feed_url: str, policy: dict) -> list[dict]:
    response = client.get(feed_url)
    response.raise_for_status()
    feed = feedparser.parse(response.content)
    events = []
    for entry in feed.entries[:100]:
        published = entry.get("published_parsed")
        if not published or not entry.get("link") or not entry.get("title"):
            continue
        published_at = datetime(*published[:6], tzinfo=timezone.utc)
        content = {"title": entry.title, "language": feed.feed.get("language") or "und"}
        # Feed policies require operator verification of hotlink/thumbnail permission.
        if policy.get("allow_thumbnails"):
            thumbnails = entry.get("media_thumbnail", [])
            if thumbnails and thumbnails[0].get("url", "").startswith("https://"):
                content["thumbnail_url"] = thumbnails[0]["url"]
        events.append({"source": {"provider": "RSS", "publisher": feed.feed.get("title") or
                                  urlsplit(feed_url).hostname, "url": entry.link},
                       "content": content, "published_at": published_at.isoformat(),
                       "source_discovered_at": published_at.isoformat(),
                       "location_references": policy.get("event_locations", [])})
    return events


def stop(signum, frame):
    global running
    running = False


def main():
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    database = Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                              decode_responses=True, socket_timeout=5)
    producer = KafkaProducer(bootstrap_servers=os.environ.get("KAFKA_BOOTSTRAP_SERVERS", "localhost:9092").split(","),
                             acks="all", retries=5, max_request_size=131072,
                             key_serializer=lambda key: key.encode(),
                             value_serializer=lambda value: json.dumps(value, ensure_ascii=False).encode())
    policy_file = Path(os.environ.get("RSS_POLICY_FILE", "collector/rss-policy.json"))
    policies = json.loads(policy_file.read_text()) if policy_file.exists() else {}
    interval = max(60, int(os.environ.get("COLLECT_INTERVAL_SECONDS", "900")))
    next_gdelt_request = 0
    gdelt_backoff = 0
    geography = Geography()
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers={
                "User-Agent": "TerraNewsphere/0.1 (news metadata collector)"}) as client:
            while running:
                sources = [("GDELT", None)] + [(url, policies.get(url, {})) for url in
                           os.environ.get("RSS_URLS", "").split(",") if url.strip()]
                for source, policy in sources:
                    if policy is None and time.monotonic() < next_gdelt_request:
                        continue
                    try:
                        events = gdelt(client, os.environ.get("GDELT_QUERY", "(climate OR earthquake OR economy OR technology)")) if policy is None else rss(client, source.strip(), policy)
                        if policy is None:
                            gdelt_backoff = 0
                            next_gdelt_request = time.monotonic() + interval
                        if policy is None and events:
                            try:
                                enrich_locations(client, events, geography)
                            except (httpx.HTTPError, ValueError, zipfile.BadZipFile):
                                log.warning("GKG enrichment unavailable; keeping uncertain articles unlocated")
                        for event in events:
                            now = datetime.now(timezone.utc)
                            discovery = datetime.fromisoformat(event["source_discovered_at"])
                            if discovery < now - timedelta(seconds=RETENTION_SECONDS) or discovery > now:
                                continue
                            event["source"]["url"] = canonical_url(event["source"]["url"])
                            news_id = article_id(event["source"]["url"])
                            seen_key = f"news:seen:{news_id}"
                            database.set(seen_key, now.isoformat(), nx=True, ex=RETENTION_SECONDS)
                            first = database.get(seen_key)
                            if first is None:
                                continue
                            event.update(schema_version=1, collected_at=first)
                            producer.send(os.environ.get("KAFKA_TOPIC", "news.raw"), key=news_id, value=event).get(timeout=30)
                        log.info("Published %d candidates from %s", len(events), "GDELT" if policy is None else "RSS")
                    except GdeltRateLimited as error:
                        gdelt_backoff = min(max(interval, gdelt_backoff * 2), max(interval, 3600))
                        delay = max(gdelt_backoff, error.retry_after)
                        next_gdelt_request = time.monotonic() + delay
                        log.warning("GDELT DOC rate limited (HTTP 429 or throttle body); retry in at least %.0fs", delay)
                    except (httpx.HTTPError, ValueError, KeyError) as error:
                        log.warning("Source unavailable: %s", type(error).__name__)
                    # Redis/Kafka failure stops the process so the supervisor can restart it.
                for _ in range(interval):
                    if not running:
                        break
                    time.sleep(1)
    finally:
        producer.close(timeout=10)
        database.close()


if __name__ == "__main__":
    main()
