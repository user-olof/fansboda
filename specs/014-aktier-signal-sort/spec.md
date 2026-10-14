# SPEC 014 — Aktier Signal column rename, icons, and full-dataset sort

**Status**: Implemented (CPO-approved)  
**Base**: `dev`  
**Supersedes UI chrome** in [013 contracts/aktier-kors-ui.md](../013-aktier-cross-signal/contracts/aktier-kors-ui.md) (header **Signal**, icon cells). Does **not** change kors detection or freshness (`kors_display.py`).

## Outcomes

1. Visible header **Kors → Signal** on `/stocks` (all exchanges).
2. Signal cell: Death → small red skull icon; Golden → small green bull icon; `—` for empty; a11y via `aria-label`; keep `kors_title` tooltip.
3. Sortable **Trend**, **Bolag**, **Signal** — sort full exchange dataset, then paginate (`PAGE_SIZE` 25).

## FR summary

| ID | Rule |
|----|------|
| FR-1 | Header label Signal; internal `kors*` fields may remain |
| FR-2 | Icons + a11y; no dual icons; no filters |
| FR-3 | Full-dataset sort then page; URL `sort`+`dir`; cache v2 / complete rows only |

See contract update and acceptance criteria in the implementing PR.
