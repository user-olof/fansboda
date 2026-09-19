# Contract: Aktier Signal (Kors) UI & row payload

**Feature**: `013-aktier-cross-signal` (UI chrome superseded by SPEC 014)  
**Surface**: `GET /stocks?exchange={nasdaq|nyse|omx_stockholm}&page={n}` plus optional `sort` / `dir` (SPEC 014)  
**Auth**: `@role_required(Role.USER, Role.ADMIN)` — unchanged

This is a **UI/row-shape contract** for the Aktier table extension (not a new HTTP API).

## HTML table contract

### Header order

1. Trend (sortable — SPEC 014)  
2. **Signal** ← visible header (SPEC 014; was **Kors**)  
3. Bolag (sortable — SPEC 014)  
4. Symbol  
5. Valuta  
6. Pris  
7. Industri  

Header label text: **Signal** (Swedish product chrome). Internal field names may remain `kors` / `kors_title`.

### Cell values (Signal column)

| Display | Condition |
|---------|-----------|
| Red skull icon (`aria-label` / accessible name `Death`) | Qualifying completed Death under freshness rules |
| Green bull icon (`aria-label` / accessible name `Golden`) | Qualifying completed Golden under freshness rules |
| `—` | No qualifying signal (including incomplete detection / short history) |

Exactly one of the three per visible data row (SC-001). Do not render dual icons or text labels `Golden` / `Death` in the cell.

### Tooltip (P2)

- When Death or Golden: native `title` (or equivalent) includes the crossover date (ISO `YYYY-MM-DD` acceptable) via `kors_title`.
- When `—`: no title that implies a crossover date.

### Empty exchange / no rows

- Empty-state row `colspan` MUST be **7** (was 6).
- Exchange prompt and paging chrome unchanged (paging MUST preserve `sort` / `dir` when set — SPEC 014).

### Non-goals (must not appear)

- Chart stage markers  
- Filter controls for golden/death  
- Dual labels/icons in one cell  

## Sorting (SPEC 014)

- Sortable headers: Trend, Bolag, Signal only.
- Sort applies to the **full exchange dataset**, then pagination (`PAGE_SIZE` 25). Page-only sort is a defect.
- URL: keep `exchange` + `page`; add `sort=trend|bolag|signal` and `dir=asc|desc`. Invalid `sort`/`dir` → default symbol order.
- Cache: prefer complete full-row blobs (`aktier_table_v2:…`); never sort an incomplete partial page cache.

## Row payload contract (server → template / cache)

Each stock dict in `stocks` (and in cached complete `rows` / `pages[n]`) MUST include:

| Key | Type | Required | Meaning |
|-----|------|----------|---------|
| …existing keys… | | yes | Unchanged Trend/company/… |
| `kors` | `string \| null` | yes | `"Golden"`, `"Death"`, or `null`/`""` for empty |
| `kors_title` | `string` | yes when signal | Tooltip text; empty string when no signal |

Cache key: `aktier_table_v2:{user_id}:{exchange_key}`. Pages warmed after deploy MUST rebuild with these keys so clients never see Trend-only rows missing Signal after the feature ships (TTL ≤ 1h or logout clears).

## Detection semantics (normative reference)

Canonical algorithm: fansboda-finance **RFC-013** / `cross_detection.py`:

- Regime window default **4** valid weeks  
- Convergence window default **3** valid weeks (first-vs-last gap narrowing)  
- Strict crossover inequality; skip NULL SMA rows  

Product freshness (not in RFC-013): see [data-model.md](../data-model.md) and [spec.md](../spec.md) FR-004–FR-006. SPEC 014 does not change detection or freshness.

## Auth contract

| Caller | `/stocks` |
|--------|-----------|
| Anonymous | Redirect to login (existing) |
| Allowlisted USER/ADMIN | 200 with Signal column when exchange selected |

No separate kors/signal endpoint.
