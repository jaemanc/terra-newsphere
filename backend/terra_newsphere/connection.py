"""Read service credentials from mounted secrets, never from browser assets."""
import os
from pathlib import Path

from redis import Redis


def redis_client() -> Redis:
    credentials = {}
    password_file = os.environ.get("REDIS_PASSWORD_FILE")
    if password_file:
        password = Path(password_file).read_text().strip()
        if not password or not os.environ.get("REDIS_USERNAME"):
            raise ValueError("Redis secret and username are required")
        credentials = {"username": os.environ["REDIS_USERNAME"], "password": password}
    return Redis.from_url(os.environ.get("REDIS_URL", "redis://localhost:6379/0"),
                          decode_responses=True, socket_connect_timeout=3, socket_timeout=5,
                          max_connections=32, **credentials)
