# Data Model: Load Only What the Aktier Page Shows

**Feature**: [spec.md](./spec.md) | **Date**: 2026-11-09

No database table or column changes (constitution II). New in-app, file-cached structure only.

## Börs snapshot (shared, file cache)

Key: `aktier_snapshot:<exchange_key>:<version>` — `exchange_key` ∈ `nasdaq`, `nyse`,
`omx_stockholm`, `ftse`.

| Field | Type | Source / rule |
|---|---|---|
| `exchange_key` | str | börs button key |
| `version` | str | `"<metrics max trading_date>|<indices max trading_date>"` for the börs's country (R3) |
| `built_at` | ISO datetime | build time (UTC) |
| `sector_rows` | list[dict] | index-table rows exactly as `_load_sector_rows` today (Trend, Signal, label, count, currency, price, Ratio), market-first order |
| `stock_rows` | list[dict] | every displayable stock row of the börs, default symbol order, exactly as `_build_page_rows` today (`_serialize_row` output: company, ticker, currency, current_price, industry, heat_*, kors, kors_title) |
| `industry_options` | list[str] | `industry_options(stock_rows, exclude_labels=market index labels)` as today |
| `sector_labels` | list[str] | `_sector_index_labels(sector_rows)` (extra allowed filter values) |

Rules:
- `len(stock_rows)` is the börs total (names with a latest metric row, as today).
- Contains market data only — no user id, email, or session data.
- Expires after 24 h; replaced when the version changes.

## Version memo (per worker, in memory)

| Field | Type | Rule |
|---|---|---|
| `version` per country (`us`, `se`, `uk`) | str | last probed version |
| `probed_at` | monotonic seconds | re-probe when older than 600 s |

## Aktier view state (session, unchanged)

`aktier_exchange`, `aktier_page`, `aktier_sort`, `aktier_dir`, `aktier_sector_sort`,
`aktier_sector_dir`, `aktier_industry` — as today (spec 008 / 014 / 026).

## Removed

- Per-user page cache blobs `aktier_table_v2:<user_id>:<exchange>` and their helpers.
- `GET /stocks/warm` and its JSON response.
