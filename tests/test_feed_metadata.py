import unittest
from datetime import datetime, timezone
from email.utils import format_datetime

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


if __name__ == "__main__":
    unittest.main()
