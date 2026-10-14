"""Focused trust-boundary checks; live ACL/proxy checks live in check_security.py."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx

from collector.download import download
from terra_newsphere.connection import redis_client
from scripts.security_setup import prepare


class Security(unittest.TestCase):
    def test_env_credentials_preserve_existing_secrets_and_stay_private(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / ".env.example").write_text("WEB_PORT=8080\nREDIS_API_PASSWORD=\n")
            directory = root / ".runtime/security"
            directory.mkdir(parents=True)
            (directory / "redis_api").write_text("existing-test-password")
            prepare(root)
            first = (root / ".env").read_text()
            self.assertIn("REDIS_API_PASSWORD=existing-test-password", first)
            self.assertEqual((root / ".env").stat().st_mode & 0o777, 0o600)
            prepare(root)
            self.assertEqual((root / ".env").read_text(), first)
            for role in ("api", "collector", "processor", "health"):
                self.assertTrue((directory / f"redis_{role}").read_text())
            (root / ".env").write_text(first.replace("existing-test-password", "updated-test-password"))
            prepare(root)
            self.assertEqual((directory / "redis_api").read_text(), "updated-test-password")
            (root / ".env").write_text(first.replace("existing-test-password", '" leading-space"'))
            with self.assertRaises(ValueError):
                prepare(root)

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
