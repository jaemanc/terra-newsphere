# Actual news collection

A normal `docker compose up` starts the collector and Spark as well as the API/frontend; ingestion is no longer an opt-in profile. The collector starts its first collection immediately, before the recurring interval. It fetches each configured RSS feed (up to 100 available entries per feed), publishes entries from the last seven days, then performs the initial GDELT DOC lookup over `7d` with `maxrecords=250`. This is a bounded bootstrap of available recent coverage, not a complete global archive. If DOC is throttled, its initial lookup remains pending until a successful response; RSS continues. Later DOC requests use `1h`/250 and the normal interval.

RSS retries a transient connection/protocol failure once after one second; HTTP rate-limit status responses are not immediately retried.

Every initial and recurring event follows collector → `news.raw` → single local Spark application → validated Redis record and region indexes. No separate bootstrap datastore or direct unvalidated Redis seed is used. Redis may take several Spark microbatches to fill. The empty frontend refreshes every five seconds, then every minute after data arrives. Recollection preserves the first collection time and the original seven-day expiry.

`collector:gdelt:cooldown` is an expiring Redis request gate. It prevents DOC retries within five seconds across collector restarts and preserves the provider cooldown/backoff. It contains only the backoff value and has a TTL equal to the current request window, independently of article retention.

## Local supplementary RSS feeds

Local Compose and `.env.example` configure 39 official feeds, including 20 BBC News feeds: world, Asia, Europe, US/Canada, Africa, Middle East, Latin America, business, technology, science/environment, UK, health, politics, education, entertainment/arts, England, Scotland, Wales, Northern Ireland and BBC Verify. `RSS_URLS` can override the set; an explicitly empty value disables RSS. Kubernetes has no BBC default; choose licensed sources for its intended use.

Checked 2026-10-14 against the live [BBC terms](https://www.bbc.com/pages/terms-of-use), section **Metadata and RSS feeds**, and the feed's own copyright/terms link. BBC permits individuals to display its News RSS feed with unchanged supplied material and a prominent BBC News credit/link. Business use requires permission/licensing. These are personal local development defaults, not a grant for commercial redistribution. Keep the supplied headline, short description and original media thumbnail URL; do not scrape article bodies or increase thumbnail resolution. The visible card includes the original article link labelled BBC News. The source check and allowed thumbnail host `ichef.bbci.co.uk` are recorded in `collector/rss-policy.json`.

Additional personal-local sources were checked on 2026-10-15:

- [SBS official RSS](https://news.sbs.co.kr/news/rss.do): seven feeds (latest, politics, economy, society, international, culture and sport), under its personal/noncommercial RSS terms. Supplied snippets and `img.sbs.co.kr` thumbnails retain the SBS source link.
- [Le Monde RSS](https://www.lemonde.fr/en/about-us/article/2026/03/27/le-monde-rss-feeds_6751860_115.html): ten English section feeds for personal reading; supplied titles/snippets/URLs only, no third-party images.
- [UN Geneva RSS](https://www.ungeneva.org/en/news-media/rss): its all-press-items feed, with source credit; no images.

These local RSS defaults do not grant commercial/collective redistribution rights. Do not scrape paywalled/full article bodies. `.env` can override the feed set; K3s still has no default supplementary feeds.

Other feeds need explicit policies before displaying their descriptions or thumbnails. Source-provided HTML descriptions are converted to plain text; scripts/styles are ignored. No generated summary, translation or image is substituted. Missing thumbnails use the existing neutral fallback. GDELT's `socialimage` remains excluded because discovery does not license it.

## Place associations and presentation

An exact, unambiguous country name in a supplied headline/description can create a **mentioned** association with confidence 0.5. Codes are checked against the versioned geography dataset. Ambiguous names such as Jordan (person/country), Georgia (state/country), Chad and Turkey are excluded from automatic name matching. Generic Korea is not mapped to either Korea. Short abbreviations US/UK/UAE require uppercase. Publisher nationality and feed section are never used as event locations. Existing GKG metadata may add country mentions without discarding existing references.

These are not precise event locations. Country-only news uses the validated capital presentation fallback and displays the uncertainty in its preview. Do not manufacture administrative IDs or exact city coordinates. Articles with no confirmed association remain visible in the global list as **Location unconfirmed**, with an unanchored preview and no globe marker. Region-filtered lists continue to use actual validated region indexes.

The UI requests `include_demo=false` so fixtures never inflate real news counts. API defaults remain backward compatible for pipeline verification; demo records are always explicitly flagged. Marker responses include source URL and a provided short summary. Lists return up to 200 per response in latest-collection order. The browser displays one page of up to 500 items through at most three sequential requests. Previous/Next navigation can reach older articles without silently dropping them from an appended list. Refresh keeps the current page; changing the geographic filter starts again at page one. The prominent count comes from `/api/news/stats` for all stored, live, non-demo records, separately from the current page count. Stats inspect up to 10,000 candidates in batches of 500 and explicitly return a lower bound above that budget; missing keys and expired records never count. Orange markers and clusters carry a single-line original/available translated headline (26 characters, 18 on mobile); truncated text ends with literal `...`. A cluster previews its latest dated article, using collection time when publication time is unavailable. Its caption and point open the same real article, with the existing source and uncertainty information. No view counts are invented.


## AI-focused RSS addition (2026-10-19)

The local feed set adds [Le Monde Artificial Intelligence](https://www.lemonde.fr/en/artificial-intelligence/rss_full.xml), a dedicated AI news section listed on its [official RSS page](https://www.lemonde.fr/en/about-us/article/2026/03/27/le-monde-rss-feeds_6751860_115.html). This raises the enabled feed count from 38 to 39. The existing personal-local reading scope applies: original titles, supplied short snippets and source links only, no images or commercial redistribution grant. The 900-second post-cycle interval, canonical URL deduplication and first-collection seven-day expiry are unchanged.

The feed and its robots rules were checked live, and the deployed collector successfully published six recent candidates. These are candidates, not guaranteed new unique records: other Le Monde sections may overlap and remain deduplicated.

Other AI-focused candidates were evaluated but not enabled:

- [TechAmerica.ai RSS terms](https://techamerica.ai/rss-terms) allow attributed noncommercial headline/short-summary display, and a manual feed check returned 30 entries (13 recent). However, the actual collector received HTTP 403. Remove it from the active configuration rather than bypass automated-access restrictions.
- AI Times, THE DECODER and TechForge AI News: sufficient feed redistribution permission was not established.
- MIT News: RSS syndication requires author/republication attribution that the current preview does not preserve; defer until those requirements can be met.
- AI News Circle: no usable feed entries. BAIR: no available entries from the past seven days.

RSS availability alone is not treated as a redistribution license. Locations still come from validated article mentions, never publisher nationality. Existing Le Monde and new AI section use the same original-URL article IDs.
