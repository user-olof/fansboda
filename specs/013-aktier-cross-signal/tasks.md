# Tasks: Aktier Cross Signal (Kors)

**Input**: Design documents from `/specs/013-aktier-cross-signal/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Included — FR-013 / SC-007 and constitution III require automated coverage for detection, freshness/display, and Aktier route/HTML behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing of each story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies)
- **[Story]**: Which user story this task belongs to (e.g., US1, US2, US3)
- Include exact file paths in descriptions

## Path Conventions

- Single Flask app at repository root: `src/`, `templates/`, `static/`, `tests/`
- Feature docs: `specs/013-aktier-cross-signal/`

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Confirm package layout for the RFC-013 port and product display helpers without adding dependencies or schema tooling.

- [x] T001 Confirm `src/services/` package is importable (`src/services/__init__.py` present) and reserve module paths `src/services/cross_detection.py` and `src/services/kors_display.py` per plan.md structure
- [x] T002 [P] Confirm no new Python dependencies are required (stdlib + existing Flask/SQLAlchemy stack only) and that Pipfile / project deps stay unchanged for this feature
- [x] T003 [P] Note canonical source for the port in the upcoming module docstring: `user-olof/fansboda-finance` pure `cross_detection.py` (RFC-013); do not plan CLI subprocess or finance `config`/`db` imports

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Pure detection + freshness helpers and a batch SMA history loader that every Kors user story builds on. No Neon DDL, no detections table, no finance CLI.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

- [x] T004 Port RFC-013 pure detector into `src/services/cross_detection.py` with API surface `SmaSnapshot`, `CrossPattern`, `CrossEvent`, `DEFAULT_MIN_REGIME_WEEKS=4`, `DEFAULT_CONVERGENCE_WEEKS=3`, `validate_cross_windows`, `detect_crosses`, `detect_all_patterns`; skip NULL `sma_50`/`sma_200` rows; equal SMAs never count as regime or crossover; attribute finance repo + RFC-013 in module docstring
- [x] T005 Implement freshness / “more recent wins” in `src/services/kors_display.py`: Golden only when `crossover_date == latest_trading_date`; Death when `latest_trading_date - timedelta(weeks=8) <= crossover_date <= latest_trading_date` (inclusive); if both qualify pick max `crossover_date` only; return display fields `kors` (`"Golden"` \| `"Death"` \| `None`) and tooltip-ready `kors_date` / `kors_title` (ISO `YYYY-MM-DD` when signal present, empty when not); document deterministic tie-break if equal-date Golden+Death in tests
- [x] T006 Add batch SMA history load for a page symbol slice in `src/routes/stocks.py` (or a small helper colocated there): ordered `(trading_date, sma_50, sma_200)` from the country metric model (`Metric` / `SweMetric`) with ~52-week lookback (same horizon as `get_last_weeks_metrics`), keyed by ticker, suitable for feeding `SmaSnapshot` lists — no per-ticker N+1 on the page path
- [x] T007 Extend Aktier row serialization contract in `src/routes/stocks.py` (`_stock_row` / `_serialize_row`): support cache-safe `kors` (`"Golden"` / `"Death"` / `null`) and `kors_title` (`str`, `""` when empty); never put raw `date` objects in the `aktier_table` cache blob

**Checkpoint**: Foundation ready — detection, freshness, history batching, and cache-safe row fields exist; user story UI/wiring can begin

---

## Phase 3: User Story 1 - See current Golden / recent Death on Aktier (Priority: P1) 🎯 MVP

**Goal**: Authenticated users scanning Aktier see a **Kors** column after **Trend** / before **Bolag** with `Golden`, `Death`, or `—` per FR-001–FR-007 and contracts/aktier-kors-ui.md.

**Independent Test**: With seeded weekly SMA history yielding a completed Golden this week and/or a Death within eight weeks, load `/stocks?exchange=…` as a logged-in user and verify Kors cell text (and `—` when neither qualifies).

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [x] T008 [P] [US1] Add pure RFC-013 detection tests in `tests/test_cross_detection.py` (adapt finance cases): complete Golden/Death emit; NULL SMA skip; equal SMA no emit; incomplete regime/convergence no emit; defaults 4/3 windows
- [x] T009 [P] [US1] Add freshness/display unit tests in `tests/test_kors_display.py`: Golden on latest → `Golden`; Golden on prior week → empty; Death within 8 weeks inclusive → `Death`; Death older than 8 weeks → empty; both qualify → more recent type only; incomplete events → empty; 8-week boundary inclusive still `Death`
- [x] T010 [P] [US1] Extend Aktier HTML/route tests in `tests/test_routes.py`: thead order Trend → **Kors** → Bolag; cell literals `Golden`/`Death`/`—`; empty-state `colspan` is 7; existing Trend/paging/warm assertions still pass; seeded fixtures match freshness cases in HTML

### Implementation for User Story 1

- [x] T011 [US1] Wire detection + freshness into `_build_page_rows` in `src/routes/stocks.py`: for each page slice, batch-load SMA history (T006), run `detect_all_patterns`, apply `kors_display` against each ticker’s latest `trading_date`, attach `kors` (and leave `kors_title` empty or unset until US2 if preferred) before `_serialize_row` / `_store_page` so warm pages share the same builder
- [x] T012 [US1] Ensure insufficient history or empty detector results yield `kors=None` / `—` without failing the whole Aktier page in `src/routes/stocks.py`
- [x] T013 [US1] Insert **Kors** column header and cells in `templates/stocks.html` immediately after Trend and before Bolag; render `Golden` / `Death` / `—`; update empty-state `colspan` from 6 to 7; leave Trend heat cells and other columns unchanged
- [x] T014 [P] [US1] Add optional light alignment/styling for `.kors-cell` (or equivalent) in `static/css/stocks.css` without cards, filters, icons, or layout redesign
- [x] T015 [US1] Verify `static/js/stocks.js` warm path needs no logic change beyond cache blobs already containing `kors` from `_build_page_rows`; do not add chart markers or filter controls

**Checkpoint**: User Story 1 is fully functional and testable independently (MVP)

---

## Phase 4: User Story 3 - Same access rules as Aktier (Priority: P1)

**Goal**: Anonymous / non-allowlisted visitors cannot see Aktier Kors; allowlisted USER and ADMIN see the column under the same gate as the rest of Aktier (constitution I / FR-012).

**Independent Test**: Anonymous request to `/stocks` redirects to login; logged-in allowlisted user sees the page including Kors.

### Tests for User Story 3 ⚠️

- [x] T016 [P] [US3] Assert anonymous `GET /stocks` (and exchange query if exercised) still redirects to login in `tests/test_routes.py` and/or `tests/test_access_control.py` with no Kors leakage in the response body
- [x] T017 [P] [US3] Assert allowlisted USER and ADMIN clients receive 200 on Aktier with the Kors header present in `tests/test_routes.py` (or access-control suite) — same `@role_required(Role.USER, Role.ADMIN)` surface, no new public endpoint

### Implementation for User Story 3

- [x] T018 [US3] Confirm `stocks` and warm routes in `src/routes/stocks.py` retain existing `@role_required(Role.USER, Role.ADMIN)` (or equivalent) — no auth decorator changes unless a regression is found; do not add a separate kors endpoint
- [x] T019 [US3] Confirm logout cache clear via `clear_aktier_table_cache` in `src/routes/login.py` still drops `aktier_table:*` blobs that now include kors fields (no new cache key)

**Checkpoint**: User Stories 1 and 3 both work; Kors remains private

---

## Phase 5: User Story 2 - Understand when the cross happened (Priority: P2)

**Goal**: When a Kors cell shows `Golden` or `Death`, native tooltip/title exposes the crossover date (FR-014 / P2); empty cells have no crossover-date tooltip.

**Independent Test**: Render a row with a known crossover date and confirm `title` includes that date; `—` cells have no signal tooltip.

### Tests for User Story 2 ⚠️

- [x] T020 [P] [US2] Extend `tests/test_kors_display.py` (or route tests) so display helpers produce `kors_title` containing ISO `YYYY-MM-DD` when a signal is present and `""` when empty
- [x] T021 [P] [US2] Extend `tests/test_routes.py` HTML assertions: non-empty Kors cells include `title` with the seeded crossover date; `—` cells do not imply a crossover via title

### Implementation for User Story 2

- [x] T022 [US2] Ensure `kors_display` / `_build_page_rows` always set cache-safe `kors_title` on rows in `src/routes/stocks.py` when `kors` is set (ISO date string acceptable per contracts/aktier-kors-ui.md)
- [x] T023 [US2] Bind native `title="{{ stock.kors_title }}"` (or equivalent) on Kors cells in `templates/stocks.html` only when a signal is shown; mirror Trend’s native-title pattern; no Bootstrap popover / new script sources (CSP-safe)

**Checkpoint**: All user stories independently functional

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Constitution / non-goal guards and quickstart validation across stories

- [x] T024 [P] Run quickstart.md validation commands: `uv run pytest tests/test_cross_detection.py -q`, `uv run pytest tests/test_kors_display.py -q`, `uv run pytest tests/test_routes.py -k Aktier -q`
- [x] T025 [P] Confirm non-goals remain absent: no chart stage markers in `templates/chart.html` / chart route; no golden/death filters on Aktier; no detections table / migrations / Alembic / `flask db`; no subprocess/CLI call to fansboda-finance from the stocks request path
- [x] T026 Confirm Trend heat semantics and existing columns unchanged aside from adding Kors (SC-006) via existing route/UI tests in `tests/test_routes.py`
- [x] T027 [P] Spot-check pagination/warm: warmed pages in `aktier_table` cache include `kors` keys so clients never see Trend-only rows missing Kors after deploy (contracts/aktier-kors-ui.md)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies — can start immediately
- **Foundational (Phase 2)**: Depends on Setup completion — BLOCKS all user stories
- **User Story 1 (Phase 3)**: Depends on Foundational — MVP column + detection wiring
- **User Story 3 (Phase 4)**: Depends on Foundational; best validated after US1 HTML exists so auth tests can assert Kors presence/absence
- **User Story 2 (Phase 5)**: Depends on Foundational + US1 cell rendering (tooltip attaches to existing Kors cells)
- **Polish (Phase 6)**: Depends on desired user stories being complete

### User Story Dependencies

- **User Story 1 (P1)**: After Foundational — no dependency on US2/US3 for core display
- **User Story 3 (P1)**: After Foundational — auth gate unchanged; tests strengthen once US1 ships the column
- **User Story 2 (P2)**: After US1 cells exist — independently testable tooltip behavior

### Within Each User Story

- Tests (included) MUST be written and FAIL before implementation
- Pure services (Phase 2) before route wiring
- Route/row payload before template
- Story complete before moving to next priority when staffing is sequential

### Parallel Opportunities

- T002 and T003 can run in parallel during Setup
- After T004, T005 can proceed in parallel with T006/T007 once detector types are known (prefer finishing T004 first if types are imported)
- T008, T009, T010 can run in parallel once Phase 2 APIs are sketched
- T014 can run in parallel with template work once class names are agreed
- T016 and T017 can run in parallel
- T020 and T021 can run in parallel
- T024, T025, T027 can run in parallel during Polish

---

## Parallel Example: User Story 1

```bash
# Launch all US1 tests together (expect FAIL before wiring):
Task: "Add pure RFC-013 detection tests in tests/test_cross_detection.py"
Task: "Add freshness/display unit tests in tests/test_kors_display.py"
Task: "Extend Aktier HTML/route tests in tests/test_routes.py"

# After tests exist, implementation order:
Task: "Wire detection + freshness into _build_page_rows in src/routes/stocks.py"
Task: "Insert Kors column in templates/stocks.html"
Task: "Optional .kors-cell styling in static/css/stocks.css"  # [P]
```

---

## Parallel Example: User Story 3

```bash
Task: "Anonymous /stocks redirects with no Kors leakage in tests/test_routes.py"
Task: "Allowlisted USER/ADMIN see Kors header in tests/test_routes.py"
```

---

## Parallel Example: User Story 2

```bash
Task: "kors_title ISO date unit coverage in tests/test_kors_display.py"
Task: "HTML title assertions for Kors cells in tests/test_routes.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup
2. Complete Phase 2: Foundational (CRITICAL — blocks all stories)
3. Complete Phase 3: User Story 1 (detection wired + Kors column)
4. **STOP and VALIDATE**: pytest detection + display + Aktier HTML
5. Demo Aktier Kors without tooltips if needed

### Incremental Delivery

1. Setup + Foundational → pure detector + freshness ready
2. Add User Story 1 → column live → Deploy/Demo (MVP!)
3. Add User Story 3 → auth guarantees documented in CI
4. Add User Story 2 → crossover-date tooltips
5. Polish → quickstart + non-goal audit

### Parallel Team Strategy

With multiple developers:

1. Team completes Setup + Foundational together
2. Once Foundational is done:
   - Developer A: User Story 1 (route + template)
   - Developer B: User Story 3 (auth tests) after draft HTML exists
   - Developer C: User Story 2 (tooltip) after US1 cells land
3. Stories integrate via shared row keys `kors` / `kors_title`

---

## Notes

- [P] tasks = different files, no dependencies on incomplete sibling tasks
- [Story] label maps task to US1 / US2 / US3 from spec.md
- Do **not** call fansboda-finance CLI; do **not** add detections DDL; do **not** add chart markers or filters
- Cache key remains `aktier_table:{user_id}:{exchange_key}`; TTL/staleness expectations unchanged (research R7)
- Exchange scope unchanged: NASDAQ, NYSE, OMX Stockholm only
- Commit after each task or logical group; stop at checkpoints to validate independently
