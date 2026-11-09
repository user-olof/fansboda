# Quickstart: Validate Aktier Loading

**Feature**: [spec.md](./spec.md) | Contract: [aktier-load.md](./contracts/aktier-load.md)

## 1. Tests

```bash
uv run pytest -q
```

Expected: all pass, including snapshot equality with today's rows, zero stock / index queries
on `/stocks` with a ready snapshot, sort / filter / paging over the snapshot, version-change
rebuild, missing-snapshot fallback, `/stocks/warm` → 404, `flask aktier-warm`, access rules.

## 2. Local (dev database)

```bash
uv run flask --app app aktier-warm      # 4 lines: built … rows
uv run flask --app app aktier-warm      # 4 lines: up to date
uv run python app.py
```

Sign in, press each börs, page with Nästa / Föregående, sort Trend / Signal / Bolag, pick an
Industri type, press Återställ, open a chart and return. In dev tools → Network:
- `/stocks` responses carry `Server-Timing` with `db` ≈ 0 (except a due version probe);
- no `/stocks/warm` request; one document request per press.

Compare page 1, 2, and the last page of NASDAQ (default, Trend-sorted, Technology-filtered) with
the same pages on the current production site: names, order, Trend colours, Signal, totals equal.

## 3. Production (after deploy)

1. Deploy log shows `aktier-warm` output for 4 börser; `crontab -l` on the VM lists the two
   warm lines.
2. With the data store awake, press NASDAQ 20 times (alternate with OMX) and page / sort / filter
   20 times each; record the browser-reported time per document. Expected ≥ 95 % ≤ 0.5 s
   (SC-001, SC-002, SC-006).
3. After the next Saturday run (≥ 13:00 UTC): the page shows the new week's data without a slow
   press.
