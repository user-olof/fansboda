# Data Model: Aktier Cross Signal (Kors)

**Feature**: `013-aktier-cross-signal`  
**Date**: 2026-09-11

No Neon schema changes. Entities below are **read models** and **in-memory** shapes used by detection and the Aktier UI.

## Existing persisted entities (read-only)

### Metrics snapshot (`Metric` / `SweMetric`)

Source of truth for SMA history (external finance pipeline).

| Field | Use |
|-------|-----|
| `ticker` | Join key / row identity |
| `trading_date` | Order series; latest = freshness anchor; crossover date |
| `sma_50` | RFC-013 shorter MA |
| `sma_200` | RFC-013 longer MA |
| `current_price`, `company`, `currency`, `z_score`, … | Existing Aktier columns / Trend (unchanged) |

**Validation**: Rows with NULL `sma_50` or `sma_200` are skipped by the detector (RFC-013 FR-25). Equal SMAs never count as regime or crossover.

### Ticker (`Ticker` / `SweTicker`)

| Field | Use |
|-------|-----|
| `symbol` | Match metrics |
| `exchange_name` | Exchange filter (NASDAQ / NYSE / OMX Stockholm) |
| `sector` | Industri display (unchanged) |

`MarketMetric` / `SweMarketMetric` are **not** used for Kors.

## In-memory entities (application)

### `SmaSnapshot` (ported)

| Field | Type | Notes |
|-------|------|-------|
| `trading_date` | `date` | Weekly retained snapshot |
| `sma_50` | `Decimal \| None` | |
| `sma_200` | `Decimal \| None` | |

### `CrossEvent` (ported detection output)

| Field | Type | Notes |
|-------|------|-------|
| `pattern` | `golden` \| `death` | |
| `ticker` | `str` | |
| `country` | `str` | Optional for Aktier (`us` / `swe`); may be blank in web path |
| `crossover_date` | `date` | Stage-3 week |
| `regime_start_date` | `date` | |
| `regime_weeks` | `int` | Default 4 |
| `convergence_first_gap` / `convergence_last_gap` | `Decimal` | Stage-2 evidence |
| `sma_50` / `sma_200` | `Decimal` | Values on crossover week |

### Display signal (product)

| Field | Type | Notes |
|-------|------|-------|
| `kors` | `"Golden"` \| `"Death"` \| `None` | Template shows `—` when `None` |
| `kors_date` | `date \| None` | Crossover date for tooltip when signal present |
| `kors_title` | `str` | Optional preformatted `title` text |

Derived **only** after freshness rules (see Relationships).

### Aktier table row (extended)

Existing row dict from `_stock_row` plus:

| Field | Serialization |
|-------|----------------|
| `kors` | `"Golden"` / `"Death"` / `null` or omit → empty |
| `kors_title` | string or `""` |

Must be JSON-cache friendly (no raw `date` objects in the blob — use ISO string in `kors_title` or store `kors_date` as ISO date string).

## Relationships

```text
Ticker 1──* Metrics snapshots (ordered by trading_date)
                │
                ▼
         CrossEvent*  (RFC-013 pure detect on valid SMA weeks)
                │
                ▼  freshness filter vs latest trading_date
         Display signal (0 or 1 label)
                │
                ▼
         Aktier table row.kors
```

## State / rules (display)

| Rule | Behavior |
|------|----------|
| Incomplete RFC-013 sequence | No event → `—` |
| Golden freshness | Show only if `crossover_date == latest_trading_date` |
| Death freshness | Show if `latest_trading_date - 8 weeks <= crossover_date <= latest_trading_date` (inclusive) |
| Conflict | Both qualify → type of max `crossover_date` only |
| Insufficient history | Detector returns [] → `—`; page still renders |

## Persistence

**None** for detections. Cache is ephemeral process cache of table pages, not a source of truth.
