# Implementation Plan: Load Only What the Aktier Page Shows

**Branch**: `033-exchange-page-load` | **Date**: 2026-11-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/033-exchange-page-load/spec.md`; plan input "don't
change the technical constraints" — spec constraints kept as written.

## Summary

Each börs press today loads the whole börs (≈ 3 300 names on NASDAQ, 52 weeks of history each)
in ≈ 8–10 database round trips of ≈ 100 ms each (VM in us-central1, Neon in Frankfurt), then
preloads every page per user in a per-worker cache (research R1). Replace that with one prepared
**börs snapshot** per börs and data version — index rows, all stock rows with Signal, Industri
choices — built by the existing row functions and kept in a file cache shared by all workers
(R2). Requests read the snapshot and sort / filter / slice in memory: no stock / index queries,
at most one version probe per 10 minutes per worker (R3). A `flask aktier-warm` command, run
after deploy and by VM cron after the Saturday pipeline, builds snapshots off the person's path;
an in-request build is the rare fallback (R4). `/stocks/warm`, its script, and the per-user page
cache are removed (R5). URLs, page contents, access rules, and layout are unchanged.

## Technical Context

**Language/Version**: Python 3.11+ (uv)

**Primary Dependencies**: Flask 3, Flask-SQLAlchemy, Flask-Login, Jinja2, `cachelib`
`FileSystemCache` (already a dependency); no new package

**Storage**: Neon read-only for stock / index data (no schema change); snapshot files in
`AKTIER_SNAPSHOT_DIR` inside the web container; session as today

**Testing**: pytest (`tests/test_routes.py`, new `tests/test_aktier_snapshot.py`); browser check

**Target Platform**: Docker (gunicorn) on the GCP VM behind Nginx; Neon in eu-central-1

**Project Type**: Server-rendered Flask web app

**Performance Goals**: ≤ 0.5 s press-to-visible for börs press, Nästa / Föregående, sort, Industri
filter, Återställ on NASDAQ, data store awake (FR-004, SC-001/002/006); typical ≈ 150–250 ms (R6)

**Constraints**: identical page contents (FR-005); whole-börs sort / filter (FR-007); no
background page loading (FR-003); no data-store keep-alive; no schema change; no new service /
worker; invite-only access unchanged

**Scale/Scope**: `src/routes/stocks.py`, new `src/services/aktier_snapshot.py`, CLI registration,
`templates/stocks.html`, `static/js/stocks.js` (removed), `src/routes/login.py`, `config.py`,
deploy workflow (warm + cron), tests

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Evidence |
|------|--------|----------|
| I. Private invite-only | PASS | `/stocks` keeps `@role_required`; `/stocks/warm` removed; CLI not web-exposed |
| II. Schema ownership outside app | PASS | No DDL; reads `*_metrics`, `*_tickers`, `indices` as today; uses the pipeline's spec-009 index |
| III. Tests gate changes | PASS | Snapshot equality, zero-query request path, paging / sort / filter, removal, CLI, access tests; browser check in quickstart |
| IV. Defense in depth | PASS | GET only; no new script source (one script removed); snapshot holds market data only, in a container-local directory; no secrets |
| V. Existing stack | PASS (justified) | File cache via existing `cachelib`; no Redis / worker / SPA. Scheduled `flask` CLI via VM cron — see Complexity Tracking |

**Post-design re-check**: unchanged — PASS.

## Project Structure

### Documentation (this feature)

```text
specs/033-exchange-page-load/
├── plan.md
├── research.md          # R1–R7
├── data-model.md        # snapshot, version memo, removed caches
├── quickstart.md
├── contracts/
│   └── aktier-load.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks
```

### Source Code (repository root)

```text
src/services/aktier_snapshot.py   # build_snapshot(exchange_key), current_version(country) memo,
                                  # get_snapshot(exchange_key) (read / fallback build), warm_all()
src/routes/stocks.py              # /stocks reads snapshot; sort/filter/slice in memory;
                                  # Server-Timing; remove warm route + per-user cache helpers
src/routes/login.py               # drop clear_aktier_table_cache call
src/__init__.py                   # register `aktier-warm` CLI command
config.py                         # AKTIER_SNAPSHOT_DIR / _TTL / _VERSION_PROBE_SECONDS
templates/stocks.html             # remove warm <script>
static/js/stocks.js               # removed
.github/workflows/deploy_to_vm.production.yaml  # run aktier-warm after up; install cron lines
tests/test_aktier_snapshot.py     # builder equality, version memo, fallback, CLI
tests/test_routes.py              # zero-query /stocks, paging/sort/filter, warm 404, no script
```

**Structure Decision**: Single Flask app; one new service module beside `cross_detection.py` /
`kors_display.py`; route keeps its helpers for row building, called by the builder.

## Rollout

1. Merge → CI tests → image push → deploy; deploy runs `aktier-warm` and installs the cron lines.
2. Measure per quickstart §3.
3. First Saturday after release: confirm the 13:00 UTC warm built the new version.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| VM cron running `flask aktier-warm` (scheduled job outside the request path) | Snapshot build reads the whole börs across the Atlantic (≈ 1–2 s); FR-004 needs it off the person's path after each weekly data update | In-request build only: the first press per börs after each update would exceed 0.5 s; in-app thread / worker: constitution V forbids a background worker; keep-alive / Redis: cost and new service |
