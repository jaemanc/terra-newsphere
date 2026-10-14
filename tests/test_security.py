"""Focused trust-boundary checks; live ACL/proxy checks live in check_security.py."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from collector.download import download
from terra_newsphere.connection import redis_client


class Security(unittest.TestCase):
    def test_bounded_download_and_redirect_origin(self):
        requests = []

        def respond(request):
            requests.append(str(request.url))
            if request.url.path == "/same":
                return httpx.Response(302, headers={"location": "/payload"})
            if request.url.path == "/external":
                return httpx.Response(302, headers={"location": "https://169.254.169.254/metadata"})
            return httpx.Response(200, content=b"123456789")

        with httpx.Client(transport=httpx.MockTransport(respond), follow_redirects=True) as client:
            self.assertEqual(download(client, "https://example.com/same").content, b"123456789")
            with self.assertRaises(ValueError):
                download(client, "https://example.com/payload", max_bytes=8)
            with self.assertRaises(ValueError):
                download(client, "https://example.com/external")
            with self.assertRaises(ValueError):
                download(client, "http://example.com/feed")
        self.assertFalse(any("169.254" in request for request in requests))

    def test_secret_connection_and_fail_closed(self):
        with tempfile.TemporaryDirectory() as folder:
            password = Path(folder) / "secret"
            password.write_text("test-password")
            with patch.dict("os.environ", {"REDIS_USERNAME": "api", "REDIS_PASSWORD_FILE": str(password)}), \
                    patch("terra_newsphere.connection.Redis.from_url") as connect:
                redis_client()
                self.assertEqual(connect.call_args.kwargs["username"], "api")
                self.assertEqual(connect.call_args.kwargs["password"], "test-password")
                password.write_text("")
                with self.assertRaises(ValueError):
                    redis_client()
