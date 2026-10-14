"""Rate-limit responses and source-specific cooldowns; no live provider queries."""
import os
import unittest
from datetime import datetime, timedelta, timezone
from email.utils import format_datetime
from unittest.mock import Mock, patch

import httpx

from collector import main as collector


class GdeltLimits(unittest.TestCase):
    def test_response_classification_and_retry_after(self):
        notice = "Please limit requests to one every 5 seconds or contact the provider."
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        for status, body, headers, minimum in [
            (200, notice, {}, 5),
            (429, "Too many requests", {"Retry-After": "7200"}, 7200),
            (429, "Too many requests", {"Retry-After": format_datetime(future)}, 7190),
            (429, "Too many requests", {"Retry-After": "invalid"}, 5),
            (429, "Too many requests", {"Retry-After": "-10"}, 5),
        ]:
            with self.subTest(status=status, headers=headers):
                with httpx.Client(transport=httpx.MockTransport(lambda request:
                        httpx.Response(status, text=body, headers=headers))) as client:
                    with self.assertRaises(collector.GdeltRateLimited) as caught:
                        collector.gdelt(client, "earthquake")
                    self.assertGreaterEqual(caught.exception.retry_after, minimum)
        for payload in [{"articles": []}, {"articles": [{"title": notice,
                "url": "https://example.com/report", "seendate": "20261014T000000Z"}]}]:
            with httpx.Client(transport=httpx.MockTransport(lambda request:
                    httpx.Response(200, json=payload))) as client:
                self.assertEqual(len(collector.gdelt(client, "earthquake")), len(payload["articles"]))
        with httpx.Client(transport=httpx.MockTransport(lambda request:
                httpx.Response(200, text="Unexpected upstream failure"))) as client:
            with self.assertRaisesRegex(ValueError, "non-JSON") as caught:
                collector.gdelt(client, "earthquake")
            self.assertNotIsInstance(caught.exception, collector.GdeltRateLimited)

    def test_cooldown_keeps_rss_running_and_resets_after_success(self):
        self.check_schedule({}, [0, 60, 180, 420, 480, 540])
        self.check_schedule({"Retry-After": "7200"}, [0])

    def check_schedule(self, headers, expected_calls):
        clock = [0]
        doc_calls, rss_calls = [], []

        def discovery(client, query):
            doc_calls.append(clock[0])
            if len(doc_calls) <= 3:
                raise collector.GdeltRateLimited(httpx.Response(429, headers=headers))
            return []

        def feed(client, url, policy):
            rss_calls.append(clock[0])
            return []

        def sleep(seconds):
            clock[0] += seconds
            if clock[0] >= 600:
                collector.running = False

        with patch.dict(os.environ, {"COLLECT_INTERVAL_SECONDS": "1", "RSS_URLS": "https://example.com/rss"}), \
                patch.object(collector, "running", True), \
                patch.object(collector.signal, "signal"), \
                patch.object(collector.Redis, "from_url", return_value=Mock()), \
                patch.object(collector, "KafkaProducer", return_value=Mock()), \
                patch.object(collector, "Geography"), \
                patch.object(collector, "gdelt", side_effect=discovery), \
                patch.object(collector, "rss", side_effect=feed), \
                patch.object(collector, "enrich_locations") as enrich, \
                patch.object(collector.time, "monotonic", side_effect=lambda: clock[0]), \
                patch.object(collector.time, "sleep", side_effect=sleep), \
                self.assertLogs("collector", level="WARNING"):
            collector.main()
            enrich.assert_not_called()
        self.assertEqual(doc_calls, expected_calls)
        self.assertEqual(rss_calls, list(range(0, 600, 60)))


if __name__ == "__main__":
    unittest.main()
