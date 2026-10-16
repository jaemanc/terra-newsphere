import unittest
from datetime import datetime, timezone
from email.utils import format_datetime
from unittest.mock import patch

import httpx

from collector.feed_metadata import mentioned_locations, plain_text
from collector.main import rss
from terra_newsphere.geography import Geography


class FeedMetadata(unittest.TestCase):
    def test_grounded_summary_thumbnail_and_uncertain_country_mentions(self):
        published = format_datetime(datetime.now(timezone.utc))
        feed = f'''<rss version="2.0" xmlns:media="http://search.yahoo.com/mrss/">
          <channel><title>Publisher</title><language>en</language><item>
          <title>China and Russia discuss energy</title><link>https://example.com/story</link>
          <pubDate>{published}</pubDate><description><![CDATA[<p>South Korea joins the talks.</p>]]></description>
          <media:thumbnail url="https://ichef.bbci.co.uk/small.jpg" width="240" height="135" />
          </item></channel></rss>'''
        policy = {"allow_summaries": True, "allow_thumbnails": True,
                  "thumbnail_hosts": ["ichef.bbci.co.uk"], "allow_location_mentions": True}
        geography = Geography()
        with httpx.Client(transport=httpx.MockTransport(lambda request:
                httpx.Response(200, text=feed))) as client:
            event = rss(client, "https://example.com/feed", policy, geography)[0]
            unlicensed = rss(client, "https://example.com/feed", {}, geography)[0]
            wrong_host = rss(client, "https://example.com/feed", {**policy, "thumbnail_hosts": ["allowed.example"]}, geography)[0]
        self.assertEqual(event["content"]["summary"], "South Korea joins the talks.")
        self.assertEqual(event["content"]["thumbnail_url"], "https://ichef.bbci.co.uk/small.jpg")
        self.assertNotIn("summary", unlicensed["content"])
        self.assertNotIn("thumbnail_url", wrong_host["content"])
        self.assertEqual({ref["country_code"] for ref in event["location_references"]}, {"CN", "RU", "KR"})
        for reference in event["location_references"]:
            location = geography.resolve(reference)
            self.assertEqual(location.association_kind, "mentioned")
            self.assertEqual(location.coordinate_source, "capital_fallback")
            geography.validate(location)

    def test_no_ambiguous_or_publisher_guesses(self):
        geography = Geography()
        self.assertEqual(mentioned_locations("Jordan visits Georgia; turkey recipes for us", geography), [])
        refs = mentioned_locations("Nigeria news: UK and US talks", geography)
        self.assertEqual({ref["country_code"] for ref in refs}, {"NG", "GB", "US"})
        self.assertEqual(plain_text("<p>Safe <b>snippet</b> &amp; text.</p><script>hidden()</script>"), "Safe snippet & text.")
        refs = mentioned_locations("미국은 중국과 회담, 북한의 대응. 인도네시아는 방문", geography)
        self.assertEqual({ref["country_code"] for ref in refs}, {"US", "CN", "KP", "ID"})
        self.assertEqual(mentioned_locations("한국 소식과 인도네시아인 인터뷰", geography), [])

    def test_retry_only_transient_rss_transport_once(self):
        attempts = []

        def transient(request):
            attempts.append(request)
            if len(attempts) == 1:
                raise httpx.RemoteProtocolError("Upstream connection closed")
            return httpx.Response(200, text="<rss><channel /></rss>")

        with httpx.Client(transport=httpx.MockTransport(transient)) as client, \
                patch("collector.main.time.sleep") as sleep:
            self.assertEqual(rss(client, "https://example.com/feed", {}), [])
            sleep.assert_called_once_with(1)
        self.assertEqual(len(attempts), 2)
        attempts.clear()

        def throttled(request):
            attempts.append(request)
            return httpx.Response(429)

        with httpx.Client(transport=httpx.MockTransport(throttled)) as client:
            with self.assertRaises(httpx.HTTPStatusError):
                rss(client, "https://example.com/feed", {})
        self.assertEqual(len(attempts), 1)


if __name__ == "__main__":
    unittest.main()
