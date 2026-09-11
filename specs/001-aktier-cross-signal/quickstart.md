# Quickstart: Validate Aktier Kors

**Feature**: `001-aktier-cross-signal`  
**Plan**: [plan.md](./plan.md) · **Spec**: [spec.md](./spec.md) · **UI contract**: [contracts/aktier-kors-ui.md](./contracts/aktier-kors-ui.md)

Validation guide for implementers after `/speckit-tasks` / implement — not an implementation dump.

## Prerequisites

- Repo on a branch that includes this plan and the merged spec.
- Local env: `uv sync` (or project-equivalent), test DB as used by pytest (`TestConfig` / in-memory SQLite).
- Auth: allowlisted test user fixtures in `tests/conftest.py` (`client_with_user`).

## 1. Pure detection (RFC-013 port)

```bash
uv run pytest tests/test_cross_detection.py -q
```

**Expect**: Golden/Death complete sequences emit; NULL SMA skips; equal SMA no emit; incomplete regime/convergence no emit; defaults 4/3 windows.

## 2. Freshness / display rules

```bash
uv run pytest tests/test_kors_display.py -q
```

**Expect** (fixtures):

| Case | Result |
|------|--------|
| Golden on latest `trading_date` | `Golden` |
| Golden on prior week only | empty |
| Death within 8 weeks inclusive of latest | `Death` |
| Death older than 8 weeks | empty |
| Both qualify | more recent type only |
| Incomplete sequence | empty |

## 3. Aktier route / HTML

```bash
uv run pytest tests/test_routes.py -k Aktier -q
```

**Expect**:

- Anonymous `/stocks` → redirect login.
- Logged-in user: thead order Trend → **Kors** → Bolag; cells show literals or `—`.
- Seeded history fixtures match freshness cases in HTML (and `title` when P2 shipped).
- Existing Trend / Industri / paging / warm tests still pass.

## 4. Manual browser smoke (after implement)

1. Log in as allowlisted USER.  
2. Open Aktier → NASDAQ (or NYSE / OMX Stockholm).  
3. Confirm **Kors** column placement and no chart markers on Bolag→chart.  
4. Hover a non-empty Kors cell → crossover date tooltip.  
5. Change page / wait for warm; Kors still populated (not blank while Trend is filled).

## 5. Constitution sanity

- No migration files or `flask db` steps added.  
- No subprocess/CLI call to fansboda-finance from `stocks` request path.  
- CI pytest gate still required before merge.

## Out of scope for this validation

Implementing filters, alerts, detections DDL, or UK exchange — must remain absent.
