# AGENTS.md — TerraNewsphere

## 1. Project Overview

TerraNewsphere is a real-time global news visualization platform that displays geographically associated news on an interactive 3D globe. Users explore news by rotating and zooming the globe, hovering over news markers, and selecting a marker to open a compact article preview.

Prioritize maintainability, lightweight deployment, and responsive UI behavior.

## 2. Technology Stack

- **Backend, collectors, and data processing language:** Python 3
- **Backend API:** FastAPI
- **Event broker:** Apache Kafka (KRaft mode)
- **Stream processing:** Apache Spark 4.x / PySpark Structured Streaming, single-node local mode
- **Only runtime news database and cache:** Redis
- **Frontend:** React + CesiumJS (JavaScript/TypeScript is allowed for the browser UI)
- **Deployment:** Docker-compatible OCI images and Kubernetes (K3s)
- **Host:** OCI VM.Standard.A1.Flex (ARM64), Ubuntu 26.04 LTS

Select ARM64-compatible images. Pin tested dependency and container image versions, including a specific Spark 4.x patch release; do not deploy a multi-node Spark cluster.

## 3. System Architecture

News ingestion and processing:

```text
GDELT / RSS / permitted news APIs
        -> Python Collector
        -> Kafka topic: news.raw
        -> PySpark Structured Streaming (Spark 4.x, local mode)
        -> Redis (news records and location indexes; maximum 7-day retention)
        -> FastAPI
        -> React / CesiumJS (news markers and previews)
```

Static globe geography is separate:

```text
Bundled, optimized country / ADM1 / ADM2 files
        -> frontend static assets (or same-project static hosting)
        -> CesiumJS globe
```

Do not use Spark directly for interactive user queries. The frontend retrieves current news from FastAPI/Redis and independently loads geographic boundary files.

## 4. News Collection

- Use **GDELT** as the primary international news/event discovery source.
- Supplement with RSS and officially provided news APIs for article titles, thumbnails, or other missing metadata.
- Prefer APIs/RSS to direct crawling; crawl only where permitted and necessary, following rate limits, robots.txt where applicable, publisher terms, and copyright restrictions.
- Collect available article URL, title, publisher, source language, publication time, collection time, available image URL, and geographic references.
- Treat discovery/event feeds separately from article content: do not assume GDELT provides full copyrighted article text or licensed thumbnail images.
- Do not invent summaries when only a headline is available. Preserve the original source URL.
- Normalize canonical URLs; produce stable article IDs to deduplicate repeated ingestion.
- Preserve the **first** collection timestamp for retention calculations, even if the same article is re-collected.

## 5. Kafka and Spark Processing

### Kafka
- Publish incoming events to `news.raw`.
- Use Kafka for decoupled ingestion, buffering, and replay.
- Set bounded Kafka topic retention appropriate to available disk space; Kafka retention is **independent** of Redis news retention.
- Avoid unnecessary topics and oversized messages.

### Spark
- Use **Apache Spark 4.x (PySpark)**, with a specifically pinned tested 4.x release.
- Run **one local Spark application** with `local[1]` initially; allow measured tuning to `local[2]` if resources permit.
- Do not create a multi-node Spark cluster or multiple distributed executors.
- Consume Kafka using Structured Streaming.
- Validate, normalize, and deduplicate news; resolve geographic references and maintain location associations.
- Perform necessary region/time aggregations while preserving event time and collection time separately.
- Configure small shuffle partition counts, conservative JVM memory usage, and durable streaming checkpoints.
- Keep Redis writes idempotent; Structured Streaming retries or `foreachBatch` re-execution must not duplicate news or extend expiry.
- Avoid unbounded `collect()` and heavy local computation.

## 6. Geographic Data and Static Globe Assets

### Data sources and scope
- Use **Natural Earth** for global country boundaries (ADM0).
- Use **geoBoundaries** for country-level administrative subdivisions (ADM1 and ADM2), where available.
- The intended detail is **country and administrative region/district**, not streets, building footprints, satellite imagery, or high-resolution 3D terrain.
- Globally, administrative hierarchies differ. Do not assume all countries use Korean-style city/county/district structures.
- Preserve relevant geographic data licenses and attribution.

### Bundling and loading
- Bundle geographic boundaries in the project as versioned **static files**, preferably simplified TopoJSON (or GeoJSON if necessary).
- Do not store geographic boundaries in Redis, and do not require a paid/external geography API at runtime.
- Simplify polygon geometries and reduce unnecessary detail before packaging; document data source, version, and processing steps.
- Load ADM0 boundaries initially; lazy-load only relevant ADM1/ADM2 files as the user zooms.
- Do not load the entire world's detailed administrative geometry into the browser at once.
- Keep the geographic files on disk/static hosting as part of the deployed project, not embedded in the Redis database.

Suggested layout:

```text
frontend/public/geo/
├── countries.topojson
├── adm1/
│   ├── KR.topojson
│   └── US.topojson
└── adm2/
    ├── KR.topojson
    └── US.topojson
```

### Geographic identifiers
- Use ISO 3166-1 alpha-2 country codes (e.g. `KR`).
- Use **validated, stable ADM1/ADM2 IDs from the chosen geographic dataset**, including its version; do not assume they match official national administrative codes.
- Maintain a consistent mapping between extracted news locations and static geographic IDs.
- Allow multiple locations per news item.
- Distinguish an article's publisher location from the location of the reported event.
- Use verified city/district coordinates when the story identifies one; fall back to a relevant administrative centroid when only that region is known.
- When only a country is known, place its marker at the country's **capital** (as a presentation fallback, not a claim that the event happened there).
- Do not fabricate coordinates or region IDs for ambiguous locations. Record uncertainty and avoid presenting inferred locations as exact.

## 7. Redis-Only News Storage and 7-Day Retention

- **Redis is the sole runtime datastore for news records, news indexes, and cached API results.** Do not add PostgreSQL, MySQL, MongoDB, PostGIS, or any other database.
- Store processed article JSON as Redis strings or hashes, with indexes for country, ADM1, and ADM2 lookups.
- News can remain available for **at most 604800 seconds (168 hours)** after the first successful collection.
- Set `expires_at = first_collected_at + 604800 seconds`; repeated collection or updates must **not** extend the original retention window.
- Apply per-article TTL based on the **remaining** lifetime, not a new 7-day TTL on every write.
- Maintain region indexes (e.g. Redis Sorted Sets with expiration timestamps as scores) and remove stale members through query-time filtering and/or bounded cleanup tasks.
- Region-level queries must include news associated with appropriate child regions; design indexing or hierarchical lookups accordingly.
- Ensure APIs never return expired records, including records referenced by an index after their article key has expired.
- Expire auxiliary cached news representations by the earliest applicable source expiry and do not preserve 7-day-old news in secondary caches, snapshots, exports, or backups. Configure Redis persistence/backup retention consistently with this requirement, or disable persistence for purely ephemeral data.
- **Static geographic assets are exempt from the news TTL**, because they are application data rather than stored news.
- Limit Kafka retention and Spark checkpoints separately so that their storage policies do not unintentionally preserve news data beyond the intended retention policy. If strict deletion of all news-derived content is required, explicitly manage these artifacts as well.
- Avoid storing large image binaries in Redis; store only permitted lightweight image URLs or metadata.

Suggested keys:

```text
news:article:{news_id}
news:geo:country:{country_code}
news:geo:adm1:{country_code}:{adm1_id}
news:geo:adm2:{country_code}:{adm2_id}
```

For geographic Sorted Sets, store expiration timestamp as the score and purge/ignore scores older than the current time. Verify referenced article keys still exist before returning results.

## 8. Standard Processed News JSON Schema

Use a stable normalized JSON structure **for processed records stored in Redis**. Raw Kafka messages may use a source-specific schema; transform and validate them before storage.

```json
{
  "news_id": "news_1024",
  "source": {
    "provider": "GDELT",
    "publisher": "Example News",
    "url": "https://example.com/news/1024"
  },
  "content": {
    "title": "서울 AI 산업 투자 확대",
    "summary": "서울 지역의 AI 산업에 대한 투자가 확대되고 있다.",
    "language": "ko",
    "thumbnail_url": "https://example.com/images/1024-small.webp",
    "translations": {
      "en": {
        "title": "AI Investment Expands in Seoul",
        "summary": "Investment in Seoul's AI industry is expanding."
      }
    }
  },
  "locations": [
    {
      "country_code": "KR",
      "adm1_id": "KR-11",
      "adm2_id": "KR-11680",
      "country_name": "South Korea",
      "region_name": "Seoul",
      "district_name": "Gangnam-gu",
      "latitude": 37.5172,
      "longitude": 127.0473,
      "location_type": "district",
      "confidence": 0.98
    }
  ],
  "category": "technology",
  "published_at": "2026-10-12T10:00:00+09:00",
  "collected_at": "2026-10-12T10:05:00+09:00",
  "expires_at": "2026-10-19T10:05:00+09:00"
}
```

**The example data and region IDs above are illustrative only**, not validated administrative IDs. Production records must be validated against the selected geography dataset. In real records, `summary`, `thumbnail_url`, translations, region IDs, and coordinates can be absent/null when the source does not provide trustworthy information.

### Field and validation rules
- `news_id`: Stable unique identifier, preferably derived from a normalized canonical article URL.
- `source`: Provider, publisher, and original article URL.
- `content`: Original title, optional grounded summary, language, optional thumbnail, optional translations.
- `locations`: Zero or more validated geographic associations; do not invent unsupported values.
- `category`: News classification if known.
- `published_at`: Article publication time when available; do not substitute collection time without distinguishing them.
- `collected_at`: First successful collection timestamp (immutable for retention).
- `expires_at`: Exactly 7 days after `collected_at`.
- Use ISO 8601 timezone-aware timestamps, internally normalizing to UTC where appropriate.
- Use Pydantic to validate normalized records before Redis writes.
- Make schema changes backward-compatible where practical, and version the schema when necessary.
- Preserve original titles; translate only when a reliable translation is actually available. Never fabricate article content.

## 9. API and Globe UI / UX

### API
- Use FastAPI to query Redis for current news by country, ADM1, ADM2, and/or geographic bounding box.
- Apply pagination or result limits and never return all global articles to the browser at once.
- Return lightweight marker/previews, not full article bodies, when rendering the globe.
- Keep all returned results within the strict 7-day retention period.

### Globe interaction
- Render an interactive CesiumJS 3D Earth with rotation and zoom.
- Show country boundaries at global zoom; load ADM1 then ADM2 boundaries progressively on closer zoom.
- Display news markers according to validated location or configured fallback location.
- Group/cluster news markers when the view is zoomed out.
- Query Redis-backed news separately from local static geography files when the visible region changes; debounce repeated map interactions.

### Hover preview
- Show a small lightweight thumbnail plus the main news headline on mouse hover.
- Keep the tooltip compact; avoid expensive network calls and excessive animation.

### Click preview
- Show a small speech-bubble-style news card anchored to the selected globe location.
- Include thumbnail (if available), headline, publisher, and concise **grounded** summary (if available).
- Make the original article link clickable and open it in a new tab using safe external-link attributes.
- Keep the card compact and avoid covering most of the globe.

### Thumbnail policy
- Prefer publisher/API-authorized thumbnail URLs.
- Use appropriately small images, modern formats when available, lazy loading, and a simple fallback image.
- Respect image copyright and source hotlinking restrictions; do not assume every news source supplies thumbnails.

## 10. Multilingual UI

- Automatically select a supported UI language using browser language preferences (`Accept-Language` / browser locale).
- Optionally use **approximate region** as a fallback signal, not as a definitive indicator of language.
- Allow users to manually override the UI language; persist their preference in the browser.
- Fall back to English when no supported locale is detected.
- Localize navigation, labels, controls, tooltips, and preview presentation.
- Keep the article's original language distinct from UI language: show stored translations only when available, otherwise display the original headline and summary.
- Do not claim a translation or summary exists when it has not been produced.
- Do not request precise location permissions solely to determine interface language.

## 11. Development and Testing Rules

- Use Python for backend, collector, and data processing components; frontend JS/TS is permitted where necessary.
- Keep modules small and responsibilities separated.
- Use environment variables or secrets managers for credentials; never hardcode keys.
- Prefer established and lightweight libraries; avoid unnecessary abstractions or infrastructure services.
- **Avoid excessive testing**: add only focused, essential tests for news parsing, deduplication, geographic mapping, expiry behavior, and critical API responses.
- Run targeted tests for changed components; do not add heavy end-to-end suites without a clear need.
- Do not silently change architectural constraints (Redis-only, Spark 4.x single-node, local static globe data, 7-day news retention).

## 12. OCI ARM64 Resource Constraints

- Target OCI A1.Flex ARM64 with Ubuntu 26.04 LTS and K3s, using the actual CPU/RAM available in the account.
- Keep Kafka KRaft, one local Spark 4.x application, Redis, and FastAPI within configured memory and CPU budgets.
- Avoid additional databases, heavyweight monitoring services, and unnecessary background jobs.
- Use small Kafka/Spark batch sizes and Spark shuffle partition counts appropriate to a single node.
- Ensure adequate disk budget for Kafka logs, Spark temporary/shuffle data, checkpoints, and Redis persistence if enabled.
- Validate container images and native Python/Java dependencies for `linux/arm64`.

## 13. Implementation Priorities

1. Build lightweight CesiumJS globe with bundled ADM0 geographic data.
2. Add lazily loaded ADM1 / ADM2 boundaries and stable geographic identifiers.
3. Create FastAPI marker/preview endpoints with a minimal Redis dataset.
4. Build a Python GDELT collector; add RSS/API supplementation where needed.
5. Add Kafka ingestion and single-node Spark 4.x normalization, geolocation, and deduplication.
6. Persist only processed news and indexes in Redis with strict 7-day expiration.
7. Implement compact hover thumbnails and clickable speech-bubble previews with original-source links.
8. Implement locale detection, manual language switching, and safe fallback behavior.
9. Profile memory, latency, and rendering behavior; optimize only measured bottlenecks.

Maintain the separation between **versioned static geography** and **ephemeral Redis news** throughout the project.

## 14. Resuming Implementation

Before continuing implementation after an interruption, read `docs/implementation-progress.md`, inspect the current files and `git status`, and resume the first unfinished step. Update that document after each substantial batch of changes. Do not overwrite existing work or restart completed steps. The user requested separate top-level `kafka/`, `spark/`, and `redis/` directories, minimal abstractions, and one combined validation cycle at the end; preserve these preferences. If validation has already started, record actual results and rerun only checks affected by fixes.

## 15. Branch Workflow

Use `feature/<task>` branches from `dev`, merge through pull requests into `dev`, and promote tested `dev` through a pull request into `prd`. Use merge commits for promotion so long-lived branches retain shared ancestry. The default branch is `dev`; preserve `main` as historical work and do not develop on it. `prd` is reserved for production releases. There is no production server yet; current work is local development and testing only. See `docs/branching.md` for the required checks and local run procedure.
