# Research: Load Only What the Aktier Page Shows

**Feature**: [spec.md](./spec.md) | **Date**: 2026-11-09

Plan input: "don't change the technical constraints" — the spec's constraints (0.5 s for börs
press, paging, sort, Industri filter, Återställ while the data store is awake; whole-börs sort /
filter; identical page contents; no data-store keep-alive; no schema change; existing stack) are
kept as written.

## R1 — Where the time goes today

- **Finding**: every börs press runs `_ensure_full_rows` (to build the Industri choices) which
  loads the **whole** börs: all tickers, the latest metric row per name, and 52 weeks of SMA
  history per name, then computes Signal for every name. Then `static/js/stocks.js` calls
  `/stocks/warm`, which loads every page again into a per-user cache. The cache is Flask-Caching
  `SimpleCache` (in-process): each gunicorn worker has its own copy, so the next request often
  lands on a worker with nothing kept.
- **Finding (latency)**: the web VM runs in GCP `us-central1`; Neon runs in AWS `eu-central-1`
  (Frankfurt). Each database round trip costs ≈ 100 ms before any query work. A börs press makes
  ≈ 8–10 round trips (tickers, distinct symbols, latest rows, sectors, history, index latest,
  index history, …) ≈ 1 s of pure latency — the 0.5 s target cannot be met by making individual
  queries faster (fansboda-finance spec 009 already made per-stock lookups ≈ 1 ms).
- **Finding (user lookup)**: `load_user` already caches the user for an hour; no round trip on
  most requests.
- **Conclusion**: the request path must make **at most one** short database round trip, and
  usually none. Whole-börs sort / filter (spec Q1 = A) need all names' Trend, Signal, Bolag,
  Industri at hand — so they must be prepared ahead, not computed per press.

## R2 — Prepared börs snapshot, shared by all users and workers

- **Decision**: per börs key (`nasdaq`, `nyse`, `omx_stockholm`, `ftse`) build one **börs
  snapshot**: the index-table rows (with Signal, as `_load_sector_rows` produces today), every
  stock row of the börs in default symbol order (as `_build_page_rows` produces today, Signal
  included), the Industri choices, and the data version it was built from. Store it in a
  **file-based cache shared by all gunicorn workers** (`cachelib.FileSystemCache`, already a
  dependency) under a dedicated directory, separate from Flask-Caching (user cache unchanged).
- **Rationale**: the snapshot is the same for every user (market data only), changes once a week,
  and is small (NASDAQ ≈ 3 300 rows ≈ 1–2 MB pickled). Serving every press from it needs no
  per-press database reads; sorting / filtering 3 300 dicts in memory with the existing
  `sort_stock_rows` / `filter_stock_rows` takes milliseconds, so whole-börs sort and filter meet
  0.5 s (FR-007, SC-006). Building it with the existing row functions keeps page contents
  identical (FR-005).
- **Interpretation of FR-001 / FR-002 / SC-003**: a press **delivers** only page 1 (≤ 25 rows) to
  the person and reads no other pages from the data store; the whole-börs data needed for the
  total, the Industri choices, and whole-börs sort / filter is prepared once per data update, not
  loaded per press. No pages are loaded in the background after a press (FR-003).
- **Alternatives considered**:
  - Per-press SQL for page 1 (latest rows + history for 25 names): ≈ 4–6 round trips ≈ 0.5 s+
    from us-central1 — misses the target, and sort / filter by Signal would still need every
    name's history.
  - Keep per-user `SimpleCache`: per worker, per user — misses most presses (R1).
  - Redis / Memcached: new datastore and service (constitution V) — not needed for ≈ 5 MB of
    weekly data.
  - Storing Signal in the database: schema belongs to the pipeline (constitution II), and the
    pipeline leaves Golden / Death Cross to this app.
  - In-process memory per worker: rebuild per worker, more RAM on a VM with ≈ 160 MB free.

## R3 — Data version and refresh

- **Decision**: data version = the latest `trading_date` of the börs's metrics table plus the
  latest `trading_date` of its indices (one query, two index-backed `MAX`es, ≈ 1 round trip).
  The version is probed at most once per **10 minutes** per worker (in-process memo); between
  probes, requests use the snapshot for the last seen version with **no** database round trip.
  A snapshot also expires after **24 h** as a safety net (e.g. a manual re-run that changes
  history without a newer date).
- **Rationale**: data changes once a week (Saturday run) or on rare manual re-runs; a 10-minute
  delay before new data shows is acceptable and keeps nearly all requests at 0 round trips.
- **Alternatives considered**: probe every request (+≈ 100 ms each; budget too tight);
  `MAX(updated_at)` (not indexed — scans the table); time-based weekly key (breaks on late or
  manual runs).

## R4 — Building the snapshot without the person waiting

- **Decision**: a Flask CLI command `flask aktier-warm` builds (or confirms) the snapshots for
  all four börser for the current data version. It runs (a) after each deploy, from the deploy
  workflow (`docker exec fansboda-web … flask aktier-warm`), and (b) from a VM cron line
  installed by the deploy workflow, Saturdays 13:00 UTC (after the pipeline's 11:00 UTC run) and
  daily 06:00 UTC; it only rebuilds when the version changed. A request that finds no snapshot
  for the current version builds it in-request as a fallback (slow, ≈ 1–2 s, rare).
- **Rationale**: the build reads the whole börs (52 weeks of history for ≈ 3 300 names ≈ 150 k rows
  across the Atlantic) and takes ≈ 1–2 s; it must be off the person's path for FR-004. A
  scheduled CLI command is not an in-app background worker (constitution V) and adds no
  service. Two warm runs a week + one a day wake the data store briefly — negligible free-tier
  compute.
- **Build query plan (≈ 5 round trips per börs)**: tickers of the country table (filter börs by
  `exchange_name_matches` in Python, as today); latest metric row per symbol (`DISTINCT ON
  (ticker) … ORDER BY ticker, trading_date DESC`, served by the spec-009 `(ticker, trading_date)`
  index); 52-week SMA history for those symbols (one query, as `_batch_sma_history`); index
  latest rows + 52-week index history (as `_latest_index_records` / `_index_sma_history`).
- **Alternatives considered**: build in a thread after the response (in-app background worker —
  constitution V); build on container start inside gunicorn (blocks health check / boot on a
  slow data store; deploy step does the same job without blocking).

## R5 — Removing per-user page caching and the warm request

- **Decision**: remove `/stocks/warm`, `static/js/stocks.js`'s warm fetch (the script is then
  unused and removed with its `<script>` tag), the per-user Aktier cache helpers
  (`_aktier_cache_key`, `_store_page`, `_store_full_rows`, `_ensure_full_rows`,
  `_load_table_page`, `_warm_exchange_pages`, …), and `clear_aktier_table_cache` (and its logout
  call). Session keeps the selected börs, page, sort, and filter as today (chart round-trip).
- **Rationale**: FR-003 (no background page loading). The snapshot holds no user data, so there
  is nothing per user to drop on logout; the session (cleared on logout) holds the view state
  (FR-008).

## R6 — 0.5 s budget (data store awake)

| Part | Estimate |
|---|---|
| Person ↔ VM (Sweden ↔ us-central1), TLS kept alive | ≈ 120–150 ms |
| Version probe (≤ 1 per 10 min per worker) | 0 ms (≈ 100 ms when due) |
| Read + unpickle snapshot from local disk | ≈ 10–30 ms |
| Sort / filter / slice ≤ 3 300 rows | ≈ 5 ms |
| Render template | ≈ 10–30 ms |
| **Typical total** | **≈ 150–250 ms** (≈ 350 ms when the probe is due) |

- **Decision**: add a `Server-Timing` response header on `/stocks` (`app`, `db`) to verify the
  server part in the browser's dev tools (quickstart); browser-observed total checked with 20
  presses per SC-001 / SC-002 / SC-006.
- The first press after the data store has paused may exceed 0.5 s (spec Q2 = A); only the
  version probe touches the data store on the request path.

## R7 — Testing

- **Decision**: pytest — snapshot builder output equals today's row functions on the fixture
  data (FR-005); `/stocks` with a ready snapshot runs **zero** stock / index queries (SQLAlchemy
  `before_cursor_execute` counter); sort / filter / paging over the snapshot match today's
  expectations; version change triggers rebuild; missing snapshot falls back to an in-request
  build; `/stocks/warm` is gone (404) and the page has no warm script; `flask aktier-warm`
  builds all four; access rules unchanged. Browser check of all four börser (constitution III).
