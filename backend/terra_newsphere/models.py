from datetime import datetime, timedelta, timezone
from hashlib import sha256
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, HttpUrl, model_validator

RETENTION_SECONDS = 604800
TRACKING_PARAMS = {"fbclid", "gclid", "mc_cid", "mc_eid", "at_medium", "at_campaign"}


def canonical_url(value: str) -> str:
    parts = urlsplit(str(value))
    if parts.scheme not in {"http", "https"} or not parts.hostname or parts.username or parts.password:
        raise ValueError("A public HTTP(S) article URL is required")
    host = parts.hostname.lower()
    if ":" in host:
        host = f"[{host}]"
    if parts.port and (parts.scheme, parts.port) not in {("http", 80), ("https", 443)}:
        host += f":{parts.port}"
    tracking = TRACKING_PARAMS | ({"plink", "cooper"} if parts.hostname.lower() == "news.sbs.co.kr" else set())
    query = sorted((key, val) for key, val in parse_qsl(parts.query, keep_blank_values=True)
                   if not key.lower().startswith("utm_") and key.lower() not in tracking)
    return urlunsplit((parts.scheme.lower(), host, parts.path or "/", urlencode(query), ""))


def article_id(url: str) -> str:
    return sha256(canonical_url(url).encode()).hexdigest()


class Source(BaseModel):
    provider: str = Field(min_length=1, max_length=80)
    publisher: str = Field(min_length=1, max_length=200)
    url: HttpUrl


class Translation(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    summary: str | None = Field(default=None, max_length=2000)


class Content(BaseModel):
    title: str = Field(min_length=1, max_length=1000)
    summary: str | None = Field(default=None, max_length=2000)
    language: str = Field(default="und", max_length=40)
    thumbnail_url: HttpUrl | None = None
    translations: dict[str, Translation] = Field(default_factory=dict, max_length=10)


class Location(BaseModel):
    country_code: str = Field(pattern=r"^[A-Z]{2}$")
    country_name: str
    adm1_id: str | None = None
    adm2_id: str | None = None
    region_name: str | None = None
    district_name: str | None = None
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    location_type: str = Field(pattern=r"^(country|adm1|adm2|city)$")
    coordinate_source: str = Field(pattern=r"^(capital_fallback|region_centroid|verified_place)$")
    confidence: float = Field(ge=0, le=1)
    association_kind: str = Field(default="event", pattern=r"^(event|mentioned)$")
    dataset_version: str

    @model_validator(mode="after")
    def hierarchy(self):
        if self.adm2_id and not self.adm1_id:
            raise ValueError("ADM2 requires its validated ADM1 parent")
        if self.location_type == "adm1" and not self.adm1_id:
            raise ValueError("ADM1 ID required")
        if self.location_type == "adm2" and not self.adm2_id:
            raise ValueError("ADM2 ID required")
        if self.location_type == "country" and self.coordinate_source != "capital_fallback":
            raise ValueError("Country-only markers use a capital presentation fallback")
        return self


class News(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: int = 1
    news_id: str = Field(pattern=r"^[a-f0-9]{64}$")
    source: Source
    content: Content
    locations: list[Location] = Field(default_factory=list, max_length=20)
    category: str | None = Field(default=None, max_length=80)
    published_at: AwareDatetime | None = None
    collected_at: AwareDatetime
    expires_at: AwareDatetime
    is_demo: bool = False

    @model_validator(mode="after")
    def retention(self):
        self.collected_at = self.collected_at.astimezone(timezone.utc)
        self.expires_at = self.expires_at.astimezone(timezone.utc)
        if self.published_at:
            self.published_at = self.published_at.astimezone(timezone.utc)
        if self.expires_at != self.collected_at + timedelta(seconds=RETENTION_SECONDS):
            raise ValueError("Expiry must be exactly seven days after first collection")
        if self.collected_at > datetime.now(timezone.utc) + timedelta(seconds=30):
            raise ValueError("Collection time cannot be in the future")
        if self.news_id != article_id(str(self.source.url)):
            raise ValueError("Article ID must match its canonical URL")
        return self
