# Contract: Aktier Loading

**Feature**: [spec.md](../spec.md) | Research: R2–R6

## `GET /stocks` (unchanged URL and parameters)

Query: `exchange`, `page`, `sort`, `dir`, `sector_sort`, `sector_dir`, `industry` — same meaning,
validation, and fallbacks as today (specs 008, 014, 020, 022, 026, 027).

Access: `@role_required(Role.USER, Role.ADMIN)` — unchanged.

Behaviour:

| Step | Rule |
|---|---|
| No `exchange` | choose-börs view as today; no snapshot read |
| Snapshot lookup | version for the börs's country from the per-worker memo (probe ≤ 1 query when older than 10 min); read snapshot for that version from the shared file cache |
| Snapshot missing | build it in-request (fallback), store it, continue |
| Index table | `sector_rows` from the snapshot, sorted by `sector_sort` / `sector_dir` as today |
| Stock table | `filter_stock_rows(stock_rows, industry)` → `sort_stock_rows(…, sort, dir)` → `parse_page` → slice 25 |
| Industri choices | `industry_options` from the snapshot; `parse_industry_filter(…, extra_allowed=sector_labels)` |
| Database reads | 0 stock / index queries when the snapshot is ready (≤ 1 version probe) |
| Session | stores börs, page, sort, filter as today |
| Response header | `Server-Timing: app;dur=<ms>, db;dur=<ms>` |

Rendered HTML: same template output as today for the same page (columns, rows, counts, links),
minus the warm `<script>` tag.

## Removed

| Item | Replacement |
|---|---|
| `GET /stocks/warm` | none (404) |
| `static/js/stocks.js` warm fetch | none (file and `<script>` removed) |
| Per-user Aktier cache; `clear_aktier_table_cache` on logout | shared snapshot (no user data); session cleared on logout as today |

## CLI: `flask aktier-warm`

- Builds the snapshot for each börs whose current version has none; prints one line per börs
  (`nasdaq: built 3324 rows in 1.4 s` / `nasdaq: up to date`); exit 0, or 1 if any börs failed.
- No web exposure; runs inside the web container:
  `docker exec fansboda-web .venv/bin/flask --app app aktier-warm`.
- Scheduled by a VM crontab line installed (idempotently) by the production deploy workflow:
  `0 13 * * 6` and `0 6 * * *` (UTC), plus one run right after each deploy.

## Configuration

| Setting | Default | Meaning |
|---|---|---|
| `AKTIER_SNAPSHOT_DIR` | `/tmp/fansboda-aktier` (prod / dev), temp dir in tests | shared snapshot cache directory |
| `AKTIER_SNAPSHOT_TTL` | 86400 s | snapshot expiry |
| `AKTIER_VERSION_PROBE_SECONDS` | 600 s | per-worker version memo |
