# Contract: Aktier Kors UI & row payload

**Feature**: `013-aktier-cross-signal`  
**Surface**: `GET /stocks?exchange={nasdaq|nyse|omx_stockholm}&page={n}` (existing)  
**Auth**: `@role_required(Role.USER, Role.ADMIN)` — unchanged

This is a **UI/row-shape contract** for the Aktier table extension (not a new HTTP API).

## HTML table contract

### Header order

1. Trend  
2. **Kors** ← new  
3. Bolag  
4. Symbol  
5. Valuta  
6. Pris  
7. Industri  

Header label text: **Kors** (Swedish chrome).

### Cell values

| Display | Condition |
|---------|-----------|
| `Golden` | Qualifying completed Golden under freshness rules |
| `Death` | Qualifying completed Death under freshness rules (and wins conflicts) |
| `—` | No qualifying signal (including incomplete detection / short history) |

Exactly one of the three per visible data row (SC-001).

### Tooltip (P2)

- When `Golden` or `Death`: native `title` (or equivalent) includes the crossover date (ISO `YYYY-MM-DD` acceptable).
- When `—`: no title that implies a crossover date.

### Empty exchange / no rows

- Empty-state row `colspan` MUST be **7** (was 6).
- Exchange prompt and paging chrome unchanged.

### Non-goals (must not appear)

- Chart stage markers  
- Filter controls for golden/death  
- Dual labels in one cell  

## Row payload contract (server → template / cache)

Each stock dict in `stocks` (and in cached `pages[n]`) MUST include:

| Key | Type | Required | Meaning |
|-----|------|----------|---------|
| …existing keys… | | yes | Unchanged Trend/company/… |
| `kors` | `string \| null` | yes | `"Golden"`, `"Death"`, or `null`/`""` for empty |
| `kors_title` | `string` | yes when signal | Tooltip text; empty string when no signal |

Cache key remains `aktier_table:{user_id}:{exchange_key}`. Pages warmed after deploy MUST rebuild with these keys so clients never see Trend-only rows missing Kors after the feature ships (TTL ≤ 1h or logout clears).

## Detection semantics (normative reference)

Canonical algorithm: fansboda-finance **RFC-013** / `cross_detection.py`:

- Regime window default **4** valid weeks  
- Convergence window default **3** valid weeks (first-vs-last gap narrowing)  
- Strict crossover inequality; skip NULL SMA rows  

Product freshness (not in RFC-013): see [data-model.md](../data-model.md) and [spec.md](../spec.md) FR-004–FR-006.

## Auth contract

| Caller | `/stocks` |
|--------|-----------|
| Anonymous | Redirect to login (existing) |
| Allowlisted USER/ADMIN | 200 with Kors column when exchange selected |

No separate kors endpoint.
