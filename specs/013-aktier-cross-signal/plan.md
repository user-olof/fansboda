# Implementation Plan: Aktier Cross Signal (Kors)

**Branch**: `013-aktier-cross-signal` | **Date**: 2026-09-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/013-aktier-cross-signal/spec.md`

**Note**: This plan is produced by `/speckit-plan`. Implementation and `/speckit-tasks` are out of scope for this step.

## Summary

Add a **Kors** column on Aktier (`/stocks`) after **Trend** / before **Bolag**, showing `Golden`, `Death`, or `—` for each row. Detection MUST reuse fansboda-finance **RFC-013** semantics by porting the pure `cross_detection.py` module into this Flask app (no finance CLI, no Neon detections table). A thin display layer applies product freshness: Golden only when `crossover_date` equals the ticker’s latest metrics `trading_date`; Death when within the last **8 weeks inclusive** of that date; if both qualify, the more recent wins. Signals are computed when building page rows and stored in the existing Aktier page cache so warm/page hits stay consistent.

## Technical Context

**Language/Version**: Python 3.11+ (project requires `>=3.11`; Pipfile notes 3.13)

**Primary Dependencies**: Flask 3 + blueprints, SQLAlchemy / Flask-SQLAlchemy, Jinja2, Bootstrap 5, Flask-Caching (`SimpleCache` in app; `NullCache` in tests)

**Storage**: Existing Neon `us_metrics` / `swe_metrics` (and ticker tables) — read-only for SMA history. **No** new tables/columns/migrations from this app.

**Testing**: pytest (`tests/test_routes.py`, new pure-unit module for detection/freshness)

**Target Platform**: Gunicorn behind Nginx on GCP VM; Docker Compose for local/prod

**Project Type**: Single Flask web application (Jinja templates + static CSS/JS)

**Performance Goals**: Keep Aktier first-page latency acceptable for ≤25 symbols/page; batch-load SMA history per page slice; reuse 1h `aktier_table` cache so warm does not re-detect every request

**Constraints**: Constitution I–V (private auth, no schema ownership, tests gate, defense in depth, stay on stack). FR-011: port/share pure RFC-013 — do not spawn finance CLI from web requests. No chart markers, filters, alerts, or detections persistence.

**Scale/Scope**: Three exchanges (NASDAQ, NYSE, OMX Stockholm), page size 25, retained weekly SMA history (reuse ~52-week lookback already used for charts — enough for 8-week Death window + regime)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Notes |
|------|--------|-------|
| I. Private invite-only access | PASS | Keep `@role_required(Role.USER, Role.ADMIN)` on `/stocks` (and warm). No new public surface. |
| II. Schema ownership outside this app | PASS | Compute on demand from existing `sma_50`/`sma_200`/`trading_date`. No detections table, no Alembic/Flask-Migrate, no `create_all` in app startup. |
| III. Tests gate changes | PASS | Plan includes unit tests for RFC-013 port + freshness/display rules and route/HTML assertions for Kors column. |
| IV. Defense in depth | PASS | No new script sources; tooltip via native `title` (same as Trend). No secret/credential changes. |
| V. Stay on existing stack | PASS | Extend `src/routes/stocks.py`, `templates/stocks.html`, optional `static/css/stocks.css`, pure helper under `src/` (e.g. `src/services/` or top-level module). No SPA/worker/new DB. |

**Post-design re-check**: PASS — design adds only a pure Python detector + display filter + template column; cache blob gains serializable fields; no DDL.

## Project Structure

### Documentation (this feature)

```text
specs/013-aktier-cross-signal/
├── plan.md              # This file
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/           # Phase 1
│   └── aktier-kors-ui.md
├── checklists/
│   └── requirements.md  # From specify (already merged)
├── spec.md
└── tasks.md             # NOT created by plan (next: /speckit-tasks)
```

### Source Code (repository root)

```text
src/
├── routes/stocks.py          # Wire history load + kors into _build_page_rows / _stock_row
├── services/
│   ├── cross_detection.py    # Ported RFC-013 pure detector (from fansboda-finance)
│   └── kors_display.py       # Freshness + “more recent wins” → display value
├── models/metrics.py         # Existing Metric (read-only)
├── models/swe_metrics.py     # Existing SweMetric (read-only)
└── ...

templates/stocks.html         # Kors header/cell after Trend; colspan 7
static/css/stocks.css         # Optional kors-cell styling
static/js/stocks.js           # Unchanged warm trigger (cache must include kors)

tests/
├── test_cross_detection.py   # Ported/adapted pure RFC-013 cases
├── test_kors_display.py      # Freshness / conflict rules
└── test_routes.py            # Aktier HTML + auth; Kors assertions
```

**Structure Decision**: Stay a single Flask app. Put pure RFC-013 detection in `src/services/cross_detection.py` (vendored from `user-olof/fansboda-finance` `cross_detection.py`) and product freshness in `src/services/kors_display.py`. Route orchestration remains in `src/routes/stocks.py`; UI in existing Jinja/CSS. No new blueprint.

## Complexity Tracking

> No constitution violations requiring justification.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| — | — | — |
