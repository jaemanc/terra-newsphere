from datetime import datetime, timedelta, timezone

from .geography import Geography
from .models import Content, News, Source, article_id, canonical_url


def normalize(raw: dict, geography: Geography) -> News:
    if raw.get("schema_version") != 1:
        raise ValueError("Unsupported raw event version")
    source = dict(raw["source"])
    source["url"] = canonical_url(source["url"])
    first = datetime.fromisoformat(raw["collected_at"]).astimezone(timezone.utc)
    # ISO datetime must carry a timezone; naive values are not trusted.
    if datetime.fromisoformat(raw["collected_at"]).tzinfo is None:
        raise ValueError("Timezone required")
    locations = []
    for reference in raw.get("location_references", [])[:20]:
        location = geography.resolve(reference)
        if location and location not in locations:
            locations.append(location)
    return News(news_id=article_id(source["url"]), source=Source(**source),
                content=Content(**raw["content"]), locations=locations,
                category=raw.get("category"), published_at=raw.get("published_at"),
                collected_at=first, expires_at=first + timedelta(days=7),
                is_demo=raw.get("is_demo", False))
