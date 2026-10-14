"""Bound decoded bytes and reject redirects away from a configured source host."""
from urllib.parse import urlsplit

import httpx


def download(client: httpx.Client, url: str, *, params=None, max_bytes=4 * 1024 * 1024) -> httpx.Response:
    original = urlsplit(url)
    if original.scheme != "https" or not original.hostname or original.username or original.password:
        raise ValueError("Collector sources require HTTPS without URL credentials")
    # Handle redirects ourselves, before any request to a different host is made.
    for _ in range(4):
        with client.stream("GET", url, params=params, follow_redirects=False) as response:
            if response.is_redirect:
                target = response.url.join(response.headers["location"])
                if target.scheme != "https" or target.host != original.hostname or (target.port or 443) != (original.port or 443):
                    raise ValueError("Source redirect changed its HTTPS origin")
                url, params = str(target), None
                continue
            data = bytearray()
            for chunk in response.iter_bytes(chunk_size=65536):
                if len(data) + len(chunk) > max_bytes:
                    raise ValueError("Source response exceeds decoded byte limit")
                data.extend(chunk)
            headers = dict(response.headers)
            headers.pop("content-encoding", None)
            headers.pop("content-length", None)
            return httpx.Response(response.status_code, headers=headers, content=bytes(data), request=response.request)
    raise ValueError("Too many source redirects")
