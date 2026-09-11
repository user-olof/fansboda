# Research: Aktier Cross Signal (Kors)

**Feature**: `001-aktier-cross-signal`  
**Date**: 2026-09-11

## R1 — How to obtain RFC-013 detection without calling the finance CLI

**Decision**: Vendor/port the pure module `cross_detection.py` from [fansboda-finance](https://github.com/user-olof/fansboda-finance) (`dev`) into this app (target: `src/services/cross_detection.py`). Call `detect_all_patterns` / `detect_crosses` in-process from the stocks route builders.

**Rationale**:
- Spec FR-011 and Assumptions forbid invoking the finance CLI from web requests.
- RFC-013 already separates pure logic (no DB/env/yfinance) from CLI orchestration (`detect_crosses.py`).
- Defaults match FR-003 / FR-26: `DEFAULT_MIN_REGIME_WEEKS=4`, `DEFAULT_CONVERGENCE_WEEKS=3`.
- Constitution V prefers small local changes; a pure module is the smallest correct reuse.

**Alternatives considered**:
| Option | Why rejected |
|--------|----------------|
| Subprocess `detect_crosses.py` per request/page | Latency, deploy coupling, process overhead, ops risk |
| HTTP call to finance service | No such service; adds network dependency |
| Reimplement from prose only | Drift risk vs canonical tests; FR-002 says do not invent a second definition |
| Shared private package | Heavier than needed for a private Metallen stack; can revisit later |

**Port notes**:
- Keep API surface: `SmaSnapshot`, `CrossPattern`, `CrossEvent`, `detect_crosses`, `detect_all_patterns`, window defaults, `validate_cross_windows`.
- Prefer adapting finance `tests/test_cross_detection.py` cases so CI fails on semantic drift.
- Attribute source in module docstring (repo + RFC-013). Do not import finance’s `config`/`db`.

## R2 — Where to compute and attach Kors on Aktier

**Decision**: Extend `_build_page_rows` / `_stock_row` in `src/routes/stocks.py` so each serialized row includes kors fields **before** `_store_page` writes the `aktier_table:{user}:{exchange}` cache blob.

**Rationale**:
- Cache stores full row dicts for 1h; warm (`/stocks/warm` + `static/js/stocks.js`) fills other pages with the same builder.
- Computing only in the template would miss cache/warm consistency and force N+1 work at render time.
- Latest-metric path alone is insufficient — RFC-013 needs ordered weekly SMA history.

**Alternatives considered**:
| Option | Why rejected |
|--------|----------------|
| Compute only on cache miss for page 1 | Warmed pages would lack or invent signals |
| Separate kors cache key | Dual invalidation; logout only clears `aktier_table` today |
| Detect at chart time | Spec is Aktier-table-only; charts must not gain markers (FR-008) |

## R3 — History load depth and batching

**Decision**: For each page’s symbol slice, batch-query ordered `(trading_date, sma_50, sma_200)` from the country metric model with a lookback of **52 weeks** (same horizon as `get_last_weeks_metrics`), keyed by ticker. Feed valid series into the detector.

**Rationale**:
- Death freshness is 8 weeks inclusive; regime needs 4 valid weeks before crossover → need history beyond 8 weeks to detect an edge Death.
- Chart already uses 52 weeks; reuse avoids a new magic number debate.
- Page size is 25 — one (or few) IN-list history queries beats per-ticker round trips.

**Alternatives considered**:
| Option | Why rejected |
|--------|----------------|
| Only 8+4 weeks | Brittle if NULLs skip weeks; harder to detect older regime leading into window |
| Full unbounded history | Unnecessary payload; retention already weekly-capped upstream |
| Reuse chart helper as-is per ticker | N+1 queries on the page path |

## R4 — Freshness / display rules layer

**Decision**: Add `src/services/kors_display.py` that, given completed `CrossEvent`s plus `latest_trading_date`, returns a single display signal:

1. Collect Golden events where `crossover_date == latest_trading_date`.
2. Collect Death events where `crossover_date >= latest_trading_date - 8 weeks` (inclusive calendar weeks via `timedelta(weeks=8)`).
3. If both non-empty, pick the event with the max `crossover_date` (ties: prefer that single date’s type; equal dates of both types are pathological — pick Death or Golden deterministically and document in tests; prefer **more recent type only** when dates differ).
4. Map to UI: `Golden` / `Death` / `None` → template `—`; optional `title` with ISO crossover date (P2).

**Rationale**: Spec FR-004–FR-006 are product rules, not part of RFC-013 emission. Keeping them separate preserves a clean port of finance detection.

**Alternatives considered**:
| Option | Why rejected |
|--------|----------------|
| Bake freshness into detector | Diverges from finance module; harder to sync |
| Wall-clock “now” for 8 weeks | Spec: relative to ticker’s latest metrics `trading_date` |

## R5 — UI contract

**Decision**: Insert **Kors** column after Trend / before Bolag; cell text `Golden` | `Death` | `—`; P2 tooltip via native `title` (mirror Trend). Update empty-state `colspan` to 7. Optional light CSS class for alignment; no cards/filters/icons required.

**Rationale**: Matches FR-001 / FR-014 and existing Aktier patterns. No Bootstrap popover (avoids CSP/script churn).

## R6 — Auth and non-goals

**Decision**: No auth changes. Out of scope remains: chart markers, filters, alerts, detections table, UK Aktier support, Trend heat changes.

**Rationale**: Spec user story 3 + Out of Scope; Constitution I/II.

## R7 — Cache staleness expectations

**Decision**: Accept existing 1h TTL and logout-only explicit clear. Document that Kors can lag Neon ingestion by up to TTL, same as Trend. Ensure `_serialize_row` handles any new date/string fields safely (ISO date string or omit when empty).

**Rationale**: Changing invalidation to metric ingest would require a push from finance or polling — out of scope. Wrong signals from *omitting* kors in the builder are the defect to avoid.

## Resolved clarifications

All Technical Context unknowns resolved against the live repo + fansboda-finance RFC-013 / `cross_detection.py`. No remaining **NEEDS CLARIFICATION**.
