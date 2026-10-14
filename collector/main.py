"""GDELT discovery + optional, explicitly configured publisher RSS metadata."""
import json
import logging
import math
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
from collector.feed_metadata import mentioned_locations, plain_text

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


def gdelt(client: httpx.Client, query: str, *, timespan: str = "1h", maxrecords: int = 100) -> list[dict]:
    response = client.get("https://api.gdeltproject.org/api/v2/doc/doc", params={
        "query": query, "mode": "artlist", "format": "json", "maxrecords": maxrecords,
        "timespan": timespan, "sort": "datedesc"})
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


def rss(client: httpx.Client, feed_url: str, policy: dict, geography: Geography | None = None) -> list[dict]:
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
        if policy.get("allow_summaries") and entry.get("summary"):
            summary = plain_text(entry.summary)
            if summary:
                content["summary"] = summary[:2000]
        # Feed policies require operator verification of hotlink/thumbnail permission.
        if policy.get("allow_thumbnails"):
            thumbnails = entry.get("media_thumbnail", [])
            for thumbnail in thumbnails:
                image = thumbnail.get("url", "")
                allowed = policy.get("thumbnail_hosts", [])
                if image.startswith("https://") and (not allowed or urlsplit(image).hostname in allowed):
                    content["thumbnail_url"] = image
                    break
        references = list(policy.get("event_locations", []))
        if geography and policy.get("allow_location_mentions"):
            references.extend(mentioned_locations(content["title"] + " " + content.get("summary", ""), geography))
        events.append({"source": {"provider": "RSS", "publisher": policy.get("publisher") or feed.feed.get("title") or
                                  urlsplit(feed_url).hostname, "url": entry.link},
                       "content": content, "published_at": published_at.isoformat(),
                       "source_discovered_at": published_at.isoformat(),
                       "location_references": references[:20]})
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
    bootstrap = True
    initial_doc = True
    cooldown_key = "collector:gdelt:cooldown"
    gdelt_backoff = int(database.get(cooldown_key) or 0)
    geography = Geography()
    try:
        with httpx.Client(timeout=30, follow_redirects=True, headers={
                "User-Agent": "TerraNewsphere/0.1 (news metadata collector)"}) as client:
            while running:
                # Publish the available feeds first so a throttled DOC request cannot delay them.
                sources = [(url.strip(), policies.get(url.strip(), {})) for url in
                           os.environ.get("RSS_URLS", "").split(",") if url.strip()] + [("GDELT", None)]
                if bootstrap:
                    log.info("Initial collection: configured RSS feeds and GDELT last 7 days (up to 250 records)")
                for source, policy in sources:
                    if not running:
                        break
                    if policy is None and time.monotonic() < next_gdelt_request:
                        continue
                    if policy is None and not database.set(cooldown_key, gdelt_backoff, nx=True, ex=5):
                        # The same Redis gate also preserves provider cooldowns across restarts.
                        log.info("GDELT DOC deferred by the shared provider cooldown")
                        continue
                    try:
                        events = gdelt(client, os.environ.get("GDELT_QUERY", "(climate OR earthquake OR economy OR technology)"),
                                       timespan="7d" if initial_doc else "1h", maxrecords=250 if initial_doc else 100) \
                            if policy is None else rss(client, source.strip(), policy, geography)
                        if policy is None:
                            initial_doc = False
                            gdelt_backoff = 0
                            next_gdelt_request = time.monotonic() + interval
                            database.set(cooldown_key, 0, ex=interval)
                        if policy is None and events:
                            for event in events:
                                event["location_references"] = mentioned_locations(event["content"]["title"], geography)
                            try:
                                enrich_locations(client, events, geography)
                            except (httpx.HTTPError, ValueError, zipfile.BadZipFile):
                                log.warning("GKG unavailable; retaining only explicit source mentions")
                        published = 0
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
                            published += 1
                        log.info("Published %d candidates from %s", published, "GDELT" if policy is None else source)
                    except GdeltRateLimited as error:
                        gdelt_backoff = min(max(interval, gdelt_backoff * 2), max(interval, 3600))
                        delay = max(gdelt_backoff, error.retry_after)
                        next_gdelt_request = time.monotonic() + delay
                        database.set(cooldown_key, gdelt_backoff, ex=math.ceil(delay))
                        log.warning("GDELT DOC rate limited (HTTP 429 or throttle body); retry in at least %.0fs", delay)
                    except (httpx.HTTPError, ValueError, KeyError) as error:
                        log.warning("Source unavailable: %s", type(error).__name__)
                    # Redis/Kafka failure stops the process so the supervisor can restart it.
                if bootstrap:
                    log.info("Initial collection complete; Kafka/Spark will write validated records to Redis")
                    bootstrap = False
                for _ in range(interval):
                    if not running:
                        break
                    time.sleep(1)
    finally:
        producer.close(timeout=10)
        database.close()


if __name__ == "__main__":
    main()
