"""One focused cycle against real Redis. Run via scripts/verify.py."""
import copy
import io
import json
import os
import time
import unittest
import zipfile
from datetime import datetime, timedelta, timezone

import httpx
from fastapi.testclient import TestClient
from redis import Redis

from terra_newsphere.api import app
from terra_newsphere.models import article_id, canonical_url
from terra_newsphere.normalize import normalize
from terra_newsphere.store import NewsStore

from collector.main import gdelt, rss
from collector.gkg import enrich_locations


class NewsCycle(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.database = Redis.from_url(os.environ["TEST_REDIS_URL"], decode_responses=True)
        cls.store = NewsStore(cls.database)
        app.state.store = cls.store

    @classmethod
    def tearDownClass(cls):
        cls.database.close()

    def test_collection_processing_storage_and_api(self):
        now = datetime.now(timezone.utc).replace(microsecond=0)
        responses = {
            "/api/v2/doc/doc": {"articles": [{"url": "https://example.com/report?utm_source=demo",
                "title": "Original headline", "domain": "example.com", "language": "English",
                "seendate": now.strftime("%Y%m%dT%H%M%SZ"), "sourcecountry": "South Korea",
                "socialimage": "https://example.com/unlicensed.jpg"}]}}
        with httpx.Client(transport=httpx.MockTransport(lambda request:
                httpx.Response(200, json=responses[request.url.path]))) as client:
            events = gdelt(client, "earthquake")
        self.assertEqual(events[0]["location_references"], [])
        self.assertIsNone(events[0]["published_at"])
        self.assertNotIn("thumbnail_url", events[0]["content"])
        feed = b'''<rss version="2.0"><channel><title>Publisher</title><language>en</language>
            <item><title>RSS headline</title><link>https://example.com/report</link>
            <pubDate>Mon, 12 Oct 2026 10:00:00 GMT</pubDate><description>Do not fabricate summaries</description></item>
            </channel></rss>'''
        with httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, content=feed))) as client:
            rss_events = rss(client, "https://example.com/rss", {})
        self.assertEqual(rss_events[0]["content"]["title"], "RSS headline")
        self.assertNotIn("summary", rss_events[0]["content"])
        self.assertEqual(canonical_url("https://EXAMPLE.com:443/report?b=2&utm_campaign=a&a=1#top"),
                         "https://example.com/report?a=1&b=2")
        self.assertEqual(article_id("https://example.com/report?utm_source=x"), article_id("https://example.com/report"))
        compressed = io.BytesIO()
        fips_code = next(code for code, iso in self.store.geography.data["fips_to_iso"].items() if iso == "KR")
        columns = ["", now.strftime("%Y%m%d%H%M%S"), "1", "example.com", "https://example.com/report", "", "", "", "", "",
                   f"1#South Korea#{fips_code}##0#0#0#0"]
        with zipfile.ZipFile(compressed, "w") as archive:
            archive.writestr("sample.gkg.csv", "\t".join(columns) + "\n")
        def gkg_response(request):
            if request.url.path.endswith("lastupdate.txt"):
                return httpx.Response(200, text=f"{len(compressed.getvalue())} digest https://data.gdeltproject.org/gdeltv2/sample.gkg.csv.zip")
            return httpx.Response(200, content=compressed.getvalue())
        with httpx.Client(transport=httpx.MockTransport(gkg_response)) as client:
            enrich_locations(client, events, self.store.geography)
        self.assertEqual(events[0]["location_references"][0]["role"], "mentioned")
        self.assertEqual(events[0]["location_references"][0]["country_code"], "KR")

        raw = events[0]
        raw.update(schema_version=1, collected_at=(now - timedelta(hours=1)).isoformat())
        raw["location_references"] = [{"country_code": "KR", "role": "event", "confidence": .7}]
        article = normalize(raw, self.store.geography)
        self.assertEqual(article.locations[0].coordinate_source, "capital_fallback")
        self.assertTrue(self.store.save(article))
        key = f"news:article:{article.news_id}"
        first_expiry = self.database.expiretime(key)
        duplicate = copy.deepcopy(raw)
        duplicate["collected_at"] = now.isoformat()
        self.assertTrue(self.store.save(normalize(duplicate, self.store.geography)))
        self.assertEqual(self.database.expiretime(key), first_expiry)
        self.assertEqual(self.store.get(article.news_id).collected_at, article.collected_at)
        self.assertEqual(self.database.zcard("news:geo:country:KR"), 1)

        admin_id, admin = next((key, value) for key, value in self.store.geography.regions.items()
                               if value["location_type"] == "adm2")
        regional = copy.deepcopy(raw)
        regional["source"]["url"] = "https://example.com/district"
        regional["location_references"] = [{**admin, "role": "event", "confidence": .9}]
        district = normalize(regional, self.store.geography)
        self.assertTrue(self.store.save(district))
        self.assertEqual(self.store.list("KR", admin["adm1_id"], admin_id)[0][0].news_id, district.news_id)
        self.assertEqual(len(self.store.list("KR")[0]), 2)
        bad = copy.deepcopy(regional)
        bad["location_references"][0]["dataset_version"] = "invented"
        self.assertEqual(normalize(bad, self.store.geography).locations, [])

        # Updating an association removes the former region links.
        relocated = copy.deepcopy(regional)
        relocated["location_references"] = [{"country_code": "US", "role": "event", "confidence": .8}]
        self.store.save(normalize(relocated, self.store.geography))
        self.assertEqual(self.store.list("KR", admin["adm1_id"], admin_id)[0], [])

        stale = copy.deepcopy(raw)
        stale["source"]["url"] = "https://example.com/expired"
        stale["collected_at"] = (now - timedelta(days=7, seconds=1)).isoformat()
        expired = normalize(stale, self.store.geography)
        self.assertFalse(self.store.save(expired))
        self.assertIsNone(self.store.get(expired.news_id))

        expiring = copy.deepcopy(raw)
        expiring["source"]["url"] = "https://example.com/about-to-expire"
        expiring["collected_at"] = (now - timedelta(days=7) + timedelta(seconds=2)).isoformat()
        near_expiry = normalize(expiring, self.store.geography)
        self.store.save(near_expiry)
        no_location = copy.deepcopy(raw)
        no_location["source"]["url"] = "https://example.com/unlocated"
        no_location["location_references"] = []
        unlocated = normalize(no_location, self.store.geography)
        self.store.save(unlocated)
        self.assertEqual(self.store.get(unlocated.news_id).locations, [])

        with TestClient(app) as client:
            self.assertEqual(client.get("/api/health").status_code, 200)
            response = client.get("/api/news/markers?country=KR&limit=1")
            self.assertEqual(response.status_code, 200)
            self.assertEqual(response.headers["cache-control"], "no-store")
            self.assertEqual(len(response.json()["items"]), 1)
            self.assertEqual(client.get(f"/api/news/{article.news_id}").json()["content"]["title"], "Original headline")
            self.assertEqual(client.get("/api/news/markers?adm1=unvalidated").status_code, 422)
            self.assertEqual(client.get("/api/news/markers?limit=10000").status_code, 422)
            self.assertEqual(client.get("/api/news/markers?bbox=nan,0,180,90").status_code, 422)
            self.assertEqual(client.get("/api/news/markers?bbox=170,-90,-170,90").status_code, 200)
            self.assertEqual(client.get("/api/news/markers?bbox=-180,-90,180,90").status_code, 200)
            self.assertEqual(client.get("/api/news/missing").status_code, 404)
            time.sleep(2.1)
            self.assertEqual(client.get(f"/api/news/{near_expiry.news_id}").status_code, 404)
            self.assertFalse(self.store.save(near_expiry))
            self.database.zadd("news:geo:country:KR", {near_expiry.news_id: time.time() + 100})
            items = client.get("/api/news/markers?country=KR").json()["items"]
            self.assertNotIn(near_expiry.news_id, [item["news_id"] for item in items])


if __name__ == "__main__":
    unittest.main()
