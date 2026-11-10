---

description: "Task list for 033 — load only what the Aktier page shows"
---

# Tasks: Load Only What the Aktier Page Shows

**Input**: Design documents from `/specs/033-exchange-page-load/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/aktier-load.md, quickstart.md

**Tests**: Included — constitution III requires route / behaviour tests and a browser check.

**Organization**: Tasks are grouped by user story so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: US1 = börs press shows index table + page 1 quickly (P1); US2 = Nästa / Föregående one page at a time (P1); US3 = sort and Industri filter still work (P2)
- Single Flask project; tests in `tests/`; run with `uv run pytest -q`
- Never point local runs at production secrets; measurements on production are read-only page loads

---

## Phase 1: Setup

**Purpose**: Green baseline and configuration.

- [X] T001 Run `uv run pytest -q` from the repo root and record the pass count (baseline)
- [X] T002 Add `AKTIER_SNAPSHOT_DIR` (default `/tmp/fansboda-aktier`, env override), `AKTIER_SNAPSHOT_TTL` (86400) and `AKTIER_VERSION_PROBE_SECONDS` (600) to the base `Config` in `config.py`; in `TestConfig` set `AKTIER_SNAPSHOT_DIR` to a per-process temp dir (`<tempdir>/aktier-test-<pid>`, created on first use) and `AKTIER_VERSION_PROBE_SECONDS = 0` (contracts/aktier-load.md "Configuration")

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: The börs snapshot — built from today's row functions, stored in a shared file cache, versioned — that every story reads (research R2–R4).

- [X] T003 [P] Write `tests/test_aktier_snapshot.py` (fixtures as in `TestAktierPaging` in `tests/test_routes.py`: >25 NYSE names with metrics + sector index rows): (a) `build_snapshot("nyse")["stock_rows"]` equals `_build_page_rows(<all symbols from _matching_symbols_with_metrics("nyse")>, Metric, Ticker, country="us")` (both helpers stay after T010), `sector_rows` equals `_load_sector_rows("us")`, `industry_options` / `sector_labels` equal today's helpers; (b) `get_snapshot` returns the stored snapshot without stock / index queries on a second call (count statements with a SQLAlchemy `before_cursor_execute` listener on `db.engine`); (c) a new latest `trading_date` (insert a newer metric row, memo expired) yields a new version and a rebuilt snapshot; (d) an empty cache dir triggers an in-request build; (e) `warm_all()` builds all four börser and returns per-börs status `built` then `up to date`; (f) the snapshot contains no user fields
- [X] T004 Create `src/services/aktier_snapshot.py`: module-level `FileSystemCache` from `cachelib` created lazily from `current_app.config["AKTIER_SNAPSHOT_DIR"]` (`threshold=50`, `default_timeout=AKTIER_SNAPSHOT_TTL`); `current_version(country)` — one query `SELECT (SELECT max(trading_date) FROM <metrics>), (SELECT max(trading_date) FROM indices WHERE country = :c)` via the existing models (`db.session.query(func.max(model.trading_date))` ×2 in one `select`), memoized per process for `AKTIER_VERSION_PROBE_SECONDS` keyed by country (`us` / `se` / `uk`), returns `"<metrics date>|<indices date>"`; `build_snapshot(exchange_key)` — calls the existing helpers in `src/routes/stocks.py` (`_matching_symbols_with_metrics`, `_build_page_rows`, `_load_sector_rows`, `industry_options`, `_market_index_labels`, `_sector_index_labels`) and returns the dict in data-model.md; `get_snapshot(exchange_key)` — key `aktier_snapshot:<exchange_key>:<version>`, read or build + store; `warm_all()` — for each key in `EXCHANGE_QUERY` build when missing, return `{key: ("built"|"up to date", rows, seconds)}` (research R2–R4; import stocks helpers inside functions to avoid a circular import)
- [X] T005 Register a Flask CLI command `aktier-warm` in `src/__init__.py` (`@app.cli.command("aktier-warm")` inside `create_app`, after blueprints): calls `warm_all()`, prints `"<key>: built <n> rows in <s> s"` / `"<key>: up to date"`, exits 1 (`sys.exit(1)`) if any börs raised (contracts "CLI")
- [X] T006 Run `uv run pytest tests/test_aktier_snapshot.py -q` and fix failures

**Checkpoint**: Snapshots build, store, version, and warm; routes unchanged so far.

---

## Phase 3: User Story 1 - A börs press shows the index table and page 1 quickly (Priority: P1) 🎯 MVP

**Goal**: `/stocks?exchange=…` renders the index table and page 1 from the snapshot with no stock / index queries; no background page loading (FR-001, FR-003, FR-004, FR-005, FR-006).

**Independent Test**: With a warm snapshot, `GET /stocks?exchange=nyse` returns the same index rows, first 25 names, total, and Industri choices as before, runs 0 stock / index queries, carries `Server-Timing`, and the HTML has no `stocks.js`; `/stocks/warm` → 404.

### Tests for User Story 1

- [X] T007 [P] [US1] In `tests/test_routes.py` add `TestAktierSnapshotLoad`: (a) after one request (snapshot built), a second `GET /stocks?exchange=nyse` executes 0 statements touching `*_metrics`, `*_tickers`, or `indices` (listener as in T003; version memo still fresh — set `AKTIER_VERSION_PROBE_SECONDS` high for this test); (b) response has a `Server-Timing` header with `app;dur=`; (c) page shows "1–25 av N" and the first 25 symbols in symbol order; (d) Industri menu lists the same sector types as before; (e) HTML has no `js/stocks.js`; (f) `GET /stocks/warm?exchange=nyse` → 404 for a logged-in user
- [X] T008 [P] [US1] Update `TestAktierPaging` / `TestAktierRoutes` in `tests/test_routes.py`: remove `test_warm_fills_pages_for_logged_in_user`, `test_warm_unknown_exchange_is_not_ok`, and the warm part of the signed-out test (`/stocks/warm` assertions near line 760); keep signed-out `/stocks` redirect assertions

### Implementation for User Story 1

- [X] T009 [US1] In `src/routes/stocks.py` `stocks()`: when an exchange is selected, `snap = get_snapshot(selected_exchange)`; `sector_rows = snap["sector_rows"]` (then `sort_sector_rows` as today); `industry_choices = snap["industry_options"]`; `industry_filter = parse_industry_filter(request.args.get("industry"), industry_choices, extra_allowed=snap["sector_labels"])`; `rows = sort_stock_rows(filter_stock_rows(snap["stock_rows"], industry_filter), sort_key, direction)`; `stock_total = len(rows)`; `stock_page = parse_page(request.args.get("page"), stock_total)`; `stock_rows = _slice_page(rows, stock_page)`; keep `_remember_aktier_view` and the template context unchanged
- [X] T010 [US1] In `src/routes/stocks.py` remove `warm_stocks` (`/stocks/warm`), `_aktier_cache_key`, `clear_aktier_table_cache`, `_cached_page`, `_empty_cache_blob`, `_blob_complete_rows`, `_store_cache_blob`, `_store_page`, `_store_full_rows`, `_ensure_full_rows`, `_load_table_page`, `_warm_exchange_pages`, `AKTIER_CACHE_TIMEOUT`, and now-unused imports (`jsonify` only if unused, `cache`); keep the row builders used by the snapshot
- [X] T011 [US1] In `src/routes/login.py` logout: remove the `clear_aktier_table_cache` import and call (session is still cleared)
- [X] T012 [P] [US1] Delete `static/js/stocks.js` and the `{% block scripts %}` `stocks.js` `<script>` in `templates/stocks.html`
- [X] T013 [US1] Add `Server-Timing` to `/stocks` responses in `src/routes/stocks.py`: measure total handler time and time spent in `current_version` / snapshot build (expose `last_db_ms` from `aktier_snapshot` for the current request via `flask.g`), set `response.headers["Server-Timing"] = f"app;dur={app_ms:.0f}, db;dur={db_ms:.0f}"` (research R6)
- [X] T014 [US1] Run `uv run pytest tests/test_routes.py tests/test_aktier_snapshot.py -q` and fix failures (existing Aktier tests must pass unchanged in meaning)

**Checkpoint**: Börs press served from the snapshot; MVP.

---

## Phase 4: User Story 2 - Nästa / Föregående load one page at a time (Priority: P1)

**Goal**: Paging reads the same snapshot; each page delivers ≤ 25 rows; chart round-trip restores the view (FR-002, FR-008).

**Independent Test**: With a warm snapshot, `page=2`, `page=3`, last page, and `page=999` return the matching 25 / remaining rows with 0 stock / index queries; chart back link returns to the same page.

### Tests for User Story 2

- [X] T015 [P] [US2] In `tests/test_routes.py` `TestAktierSnapshotLoad` add: pages 2 and last equal the matching slices of the full symbol-ordered list, `page=999` clamps to the last page, each request after the first runs 0 stock / index statements, and `Föregående` / `Nästa` are disabled on first / last page; chart return (`_aktier_return_url`) restores börs + page (existing `TestAktierPaging` chart-back tests keep passing)

### Implementation for User Story 2

- [X] T016 [US2] Confirm no paging code path in `src/routes/stocks.py` queries stocks (the `_matching_symbols_with_metrics` / `_build_page_rows` calls remain only inside `build_snapshot`); remove any leftover per-page query path; run `uv run pytest tests/test_routes.py -q -k "Paging or SnapshotLoad"` and fix failures

**Checkpoint**: Paging from the snapshot.

---

## Phase 5: User Story 3 - Sort and Industri filter still work (Priority: P2)

**Goal**: Trend / Signal / Bolag sort and the Industri filter apply to the whole börs from the snapshot, page 1 within 0.5 s (FR-007, SC-006).

**Independent Test**: With a warm snapshot, sort by each column, filter by a sector type, combine with paging and Återställ — results equal today's whole-börs ordering / filtering, 0 stock / index statements per request.

### Tests for User Story 3

- [X] T017 [P] [US3] In `tests/test_routes.py` add to `TestAktierSnapshotLoad`: sort `trend` desc / `signal` asc / `bolag` asc and an `industry` filter each return the same first page as `sort_stock_rows(filter_stock_rows(all_rows, …))` over the full fixture list, with 0 stock / index statements; filter + page 2; unknown `industry` shows all names; stock Återställ link returns default order page 1. Existing `TestAktierSort`, `TestIndustriSectorFilter`, `TestIndexRowFilter`, `TestSectorPrisSort` keep passing

### Implementation for User Story 3

- [X] T018 [US3] Run `uv run pytest tests/test_routes.py -q -k "Sort or Industri or IndexRow or SnapshotLoad"` and fix any ordering / filter differences in `src/routes/stocks.py` (T009 already routes sort / filter through the snapshot)

**Checkpoint**: All three stories served from the snapshot.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T019 In `.github/workflows/deploy_to_vm.production.yaml` add a step after "Pull and Run Docker image…": wait until `docker inspect -f '{{.State.Health.Status}}' fansboda-web` is `healthy` (poll ≤ 180 s), then `docker exec fansboda-web .venv/bin/flask --app app aktier-warm` (do not fail the deploy if warm fails — log it); and idempotently install two crontab lines for the VM user (`0 13 * * 6` and `0 6 * * *`, each `docker exec fansboda-web .venv/bin/flask --app app aktier-warm >> ~/fansboda/aktier-warm.log 2>&1`) using `( crontab -l 2>/dev/null | grep -v 'aktier-warm'; echo …; echo … ) | crontab -` (research R4)
- [X] T020 [P] Add a short "Aktier snapshot" note to `ARCHITECTURE_EXPLAINED.md`: what the snapshot holds, where it lives (`AKTIER_SNAPSHOT_DIR`), when it is built (deploy, cron, fallback), and `flask --app app aktier-warm`
- [X] T021 Run the full suite `uv run pytest -q`; confirm pass count ≥ baseline minus the removed warm tests
- [X] T022 Browser check per quickstart §2 on the dev database (constitution III): all four börser, Nästa / Föregående, each sort, an Industri filter, both Återställ, chart round-trip, mobile width; `Server-Timing` `db` ≈ 0 on repeat presses; no `/stocks/warm` request
- [ ] T023 Hand the owner the production checks (quickstart §3): deploy log warm output, `crontab -l`, 20-press timing for press / paging / sort / filter (≥ 95 % ≤ 0.5 s), and the first Saturday after release

---

## Dependencies & Execution Order

- **Setup (T001–T002)** → **Foundational (T003–T006)** → user stories.
- **US1 (T007–T014)** first: it switches `/stocks` to the snapshot and removes the old cache; **US2 (T015–T016)** and **US3 (T017–T018)** verify paging and sort / filter on that path and can run in either order after US1.
- `tests/test_routes.py` is edited by T007, T008, T015, T017 — do them sequentially.
- **Polish (T019–T023)** after the stories; T019 and T020 are independent of each other.

### Parallel Opportunities

- T003 (snapshot tests) alongside T002 (config) — different files.
- T007 / T008 (tests) alongside T012 (template + JS removal).
- T019 (workflow) alongside T020 (architecture note).

## Parallel Example: User Story 1

```text
T007 Snapshot-load route tests in tests/test_routes.py
T012 Remove stocks.js and its <script> tag in templates/stocks.html
```

## Implementation Strategy

### MVP (User Story 1)

T001–T014: börs press served from the snapshot — the reported wait is gone for page 1. Paging and sort / filter already go through the same path (T009) and are confirmed by US2 / US3.

### Full delivery

1. US1 → US2 → US3 tests green.
2. Deploy step + cron (T019), note (T020), full suite (T021), browser check (T022).
3. Owner measures on production (T023).
