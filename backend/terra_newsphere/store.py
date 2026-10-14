import json
import os
import time
from pathlib import Path

from redis import Redis

from .geography import Geography
from .models import News

ROOT = Path(__file__).resolve().parents[2]


class NewsStore:
    def __init__(self, client: Redis | None = None, geography: Geography | None = None):
        self.redis = client if client is not None else Redis.from_url(
            os.environ.get("REDIS_URL", "redis://localhost:6379/0"), decode_responses=True,
            socket_connect_timeout=3, socket_timeout=5)
        self.geography = geography if geography is not None else Geography()
        self.write = self.redis.register_script((ROOT / "redis/write_news.lua").read_text())

    def save(self, article: News) -> bool:
        article = News.model_validate(article.model_dump())
        for location in article.locations:
            self.geography.validate(location)
        indexes = {"news:all"}
        for location in article.locations:
            indexes.add(f"news:geo:country:{location.country_code}")
            if location.adm1_id:
                indexes.add(f"news:geo:adm1:{location.country_code}:{location.adm1_id}")
            if location.adm2_id:
                indexes.add(f"news:geo:adm2:{location.country_code}:{location.adm2_id}")
        return bool(self.write(keys=[f"news:article:{article.news_id}"], args=[
            article.model_dump_json(), int(article.collected_at.timestamp()), json.dumps(sorted(indexes))]))

    def get(self, news_id: str) -> News | None:
        value = self.redis.get(f"news:article:{news_id}")
        if not value:
            return None
        data = json.loads(value)
        if data.pop("_expires_epoch") <= time.time():
            return None
        data.pop("_first_epoch")
        data.pop("_indexes")
        if data.get("locations") == {}:
            data["locations"] = []
        return News.model_validate(data)

    def list(self, country: str | None = None, adm1: str | None = None, adm2: str | None = None,
             bbox: tuple[float, float, float, float] | None = None,
             limit: int = 100, cursor: int = 0, include_unlocated: bool = False,
             include_demo: bool = True) -> tuple[list[News], int | None]:
        key = "news:all"
        if country:
            key = f"news:geo:country:{country}"
        if adm1:
            key = f"news:geo:adm1:{country}:{adm1}"
        if adm2:
            key = f"news:geo:adm2:{country}:{adm2}"
        now = time.time()
        self.redis.zremrangebyscore(key, "-inf", now)
        # ponytail: cap each scan at 500 candidates; use Redis GEO if measured density needs it.
        ids = self.redis.zrevrangebyscore(key, "+inf", f"({now}", start=cursor, num=500)
        pipe = self.redis.pipeline(transaction=False)
        for news_id in ids:
            pipe.get(f"news:article:{news_id}")
        articles = []
        consumed = 0
        for value in pipe.execute():
            consumed += 1
            if not value:
                continue
            data = json.loads(value)
            if data.pop("_expires_epoch") <= time.time():
                continue
            data.pop("_first_epoch")
            data.pop("_indexes")
            if data.get("locations") == {}:
                data["locations"] = []
            article = News.model_validate(data)
            if article.is_demo and not include_demo:
                continue
            if bbox and not (include_unlocated and not article.locations):
                west, south, east, north = bbox
                if not any(south <= loc.latitude <= north and (
                    west <= loc.longitude <= east if west <= east else
                    loc.longitude >= west or loc.longitude <= east) for loc in article.locations):
                    continue
            articles.append(article)
            if len(articles) == limit:
                break
        offset = cursor + consumed
        next_cursor = offset if offset < self.redis.zcount(key, f"({time.time()}", "+inf") else None
        return articles, next_cursor
