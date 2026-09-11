# Feature Specification: Aktier Cross Signal (Kors)

**Feature Branch**: `013-aktier-cross-signal`

**Created**: 2026-09-11

**Status**: Draft

**Input**: User description: "Add a Signal / Kors column on the Aktier (`/stocks`) table that shows when a ticker has a completed Golden Cross or Death Cross, using the same detection rules as fansboda-finance RFC-013 (three-stage processes on retained weekly `sma_50`/`sma_200`). UX: new column after Trend / before Bolag; cell values Golden | Death | —; Swedish UI where appropriate; optional tooltip with crossover date. Freshness: Golden only if crossover equals that ticker’s latest metrics trading date; Death if crossover within last 8 weeks inclusive; if both qualify show the more recent. No chart markers, filters, alerts, or persisted detections table."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - See current Golden / recent Death on Aktier (Priority: P1)

An authenticated Metallen user opens Aktier, picks a supported exchange (NASDAQ, NYSE, or OMX Stockholm), and scans the table for tickers that currently show a completed Golden Cross or a recently completed Death Cross. A new **Kors** column sits after **Trend** and before **Bolag**. Each row shows `Golden`, `Death`, or an empty placeholder (`—`). Existing columns (Trend, Bolag, Symbol, Valuta, Pris, Industri) and Trend heat meaning stay unchanged.

**Why this priority**: This is the core product value — surfacing actionable cross state on the list users already use, without leaving Aktier.

**Independent Test**: With seeded weekly SMA history that yields a completed Golden this week and/or a Death within eight weeks, load `/stocks?exchange=…` as a logged-in user and verify the Kors cell text (and absence of text when neither qualifies).

**Acceptance Scenarios**:

1. **Given** a logged-in allowed user and an exchange with stocks, **When** they open Aktier for that exchange, **Then** the table header includes **Kors** immediately after **Trend** and before **Bolag**, and all existing headers remain.
2. **Given** a ticker whose latest metrics `trading_date` equals a completed Golden Cross `crossover_date`, **When** that ticker appears on the page, **Then** its Kors cell shows `Golden`.
3. **Given** a ticker with a completed Death Cross whose `crossover_date` falls within the last 8 weeks inclusive relative to that ticker’s latest metrics `trading_date`, and no fresher qualifying Golden, **When** that ticker appears on the page, **Then** its Kors cell shows `Death`.
4. **Given** a ticker with no qualifying completed Golden or Death under the freshness rules, **When** that ticker appears on the page, **Then** its Kors cell shows `—` (or equivalent empty display).
5. **Given** both a qualifying Golden and a qualifying Death for the same ticker, **When** the row is rendered, **Then** the cell shows the type of the **more recent** crossover only.

---

### User Story 2 - Understand when the cross happened (Priority: P2)

When a Kors cell shows `Golden` or `Death`, the user can hover (or otherwise use the native title/tooltip) to see the crossover date, so they can judge how fresh the signal is without opening the chart.

**Why this priority**: Improves trust and scanability; not required to ship the column itself.

**Independent Test**: Render a row with a known crossover date and confirm the tooltip/title includes that date; empty cells need no crossover tooltip.

**Acceptance Scenarios**:

1. **Given** a row showing `Golden` or `Death`, **When** the user inspects the Kors cell affordance (tooltip/title), **Then** they see the crossover date for the displayed signal.
2. **Given** a row showing `—`, **When** the user inspects the Kors cell, **Then** there is no crossover-date tooltip implying a signal.

---

### User Story 3 - Same access rules as Aktier (Priority: P1)

Unauthenticated or non-whitelisted visitors cannot see Aktier cross signals. Allowed USER and ADMIN roles see the column under the same gate as the rest of Aktier.

**Why this priority**: Constitution I — stock surfaces must stay private.

**Independent Test**: Anonymous request to `/stocks` redirects to login; logged-in allowed user sees the page including Kors.

**Acceptance Scenarios**:

1. **Given** an anonymous session, **When** requesting Aktier, **Then** access is denied the same way as today (redirect to login).
2. **Given** a logged-in user with USER or ADMIN role on the allowlist, **When** opening Aktier, **Then** they can view the Kors column with the rest of the table.

---

### Edge Cases

- Incomplete RFC-013 sequences (missing stage 1, 2, or 3) never produce a displayed signal.
- Rows with NULL `sma_50` or `sma_200` are skipped when evaluating history (same as RFC-013); they do not create false crosses.
- Equal SMA weeks (`sma_50 == sma_200`) do not count as crossover or as stage-1 regime.
- Golden whose `crossover_date` is older than the ticker’s latest metrics `trading_date` must not display (even if Death would still qualify for that older window).
- Death whose `crossover_date` is older than 8 weeks before the ticker’s latest metrics `trading_date` must clear to `—`.
- Boundary: Death on the exact 8-week-inclusive edge still shows `Death`.
- If detection cannot run for a ticker (insufficient history), show `—` without failing the whole page.
- Exchange scope remains NASDAQ, NYSE, and OMX Stockholm only (same as today’s Aktier). UK is out of scope unless already supported on Aktier (it is not).
- Pagination and per-page caching must still return correct Kors values for the symbols on that page; warming other pages must not drop or invent signals.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Aktier MUST add a **Kors** column after **Trend** and before **Bolag**. Swedish chrome for the header; cell values MUST be `Golden`, `Death`, or empty (`—`).
- **FR-002**: A displayed signal MUST represent a **completed** three-stage Golden or Death Cross per fansboda-finance **RFC-013** on retained weekly `sma_50` / `sma_200` history (stage-1 regime → convergence → strict crossover). The app MUST NOT invent a second definition of golden/death cross.
- **FR-003**: Detection MUST use the RFC-013 defaults unless product explicitly changes them later: regime window 4 valid weeks, convergence window 3 valid weeks, first-vs-last gap narrowing, strict inequality on crossover week, NULL SMA rows skipped.
- **FR-004**: **Golden freshness**: show `Golden` only when the completed Golden `crossover_date` equals that ticker’s **latest** metrics `trading_date` (current snapshot week only).
- **FR-005**: **Death freshness**: show `Death` when the completed Death `crossover_date` is within the **last 8 weeks inclusive** relative to that ticker’s latest metrics `trading_date`, then clear.
- **FR-006**: If both Golden and Death would qualify under FR-004/FR-005, the UI MUST show only the **more recent** crossover and its type.
- **FR-007**: Existing Aktier columns and Trend (z-score heat) meaning MUST remain unchanged.
- **FR-008**: Chart pages MUST NOT gain cross stage markers as part of this feature.
- **FR-009**: Aktier MUST NOT add filters such as “only golden” / “only death” in this feature.
- **FR-010**: The product MUST NOT persist a detections table or otherwise require schema migration in this application; signals are computed on demand from existing metrics history (optionally reused via the existing Aktier page cache).
- **FR-011**: Detection logic MUST be shared/ported as pure evaluation over SMA history rather than invoking the finance CLI from the web app.
- **FR-012**: Access MUST remain behind the same role gate as the rest of Aktier (logged-in, allowlisted USER/ADMIN).
- **FR-013**: Automated tests MUST cover display/freshness rules (Golden this-week only, Death 8-week inclusive window, conflict → more recent, incomplete sequences → empty) so regressions fail CI.
- **FR-014**: Optional but in-scope for P2: Kors cells that show a signal SHOULD expose the crossover date via tooltip/title; Swedish surrounding copy MAY be used where it fits existing Aktier tone.

### Key Entities

- **Aktier table row**: One ticker on a selected exchange with Trend, company, symbol, currency, price, industry, and Kors display state.
- **Metrics snapshot**: Historical weekly observation for a ticker including `trading_date`, `sma_50`, `sma_200` (and existing price/heat fields). Source of truth remains the external finance ingestion pipeline; this app reads only.
- **Completed cross event**: A Golden or Death detection with `crossover_date` (and pattern type) produced only when RFC-013’s three stages complete in order.
- **Display signal**: The single value shown in Kors after applying freshness and “more recent wins” rules: `Golden`, `Death`, or empty.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On Aktier for any supported exchange, 100% of visible rows show a Kors cell with exactly one of: `Golden`, `Death`, or empty placeholder.
- **SC-002**: In verification fixtures, every ticker with a completed Golden whose crossover equals its latest trading date shows `Golden`; Goldens from prior weeks do not.
- **SC-003**: In verification fixtures, completed Deaths appear iff crossover is within 8 weeks inclusive of the ticker’s latest trading date, and clear outside that window.
- **SC-004**: When fixtures include both qualifying types, users always see the more recent type only (no dual labels).
- **SC-005**: Anonymous users cannot view Aktier Kors data; allowlisted authenticated users can on first successful page load of an exchange table.
- **SC-006**: Reviewers confirm Trend heat and other columns behave as before (no change to heat semantics or column set beyond adding Kors).
- **SC-007**: Automated tests for freshness/display rules pass in CI before merge; a deliberate rule regression fails those tests.

## Assumptions

- RFC-013 in fansboda-finance is the canonical pattern definition (including FR-26 defaults: 4 regime weeks, 3 convergence weeks); this feature consumes that semantics rather than redefining them.
- “Last 8 weeks inclusive” is measured against each ticker’s own latest metrics `trading_date` (not wall-clock alone), counting weekly snapshot spacing consistent with retained weekly history.
- Header label **Kors** is preferred over **Signal** to match Swedish Aktier chrome; cell literals stay `Golden` / `Death` as product-specified.
- Porting/sharing pure detection logic may copy or vendor the finance pure module; calling the finance CLI process from the web request path is out of preferred design.
- Existing Aktier exchange set (NASDAQ, NYSE, OMX Stockholm) is sufficient; UK metrics are out of scope for this feature.
- Constitution constraints apply: no Neon DDL/migrations from this app; metrics remain read-only; tests gate behavior changes; stay on Flask blueprints + Jinja Aktier surface.

## Out of Scope

- Push alerts / email when a cross completes
- Chart annotations for cross stages
- Filter controls (“only golden”, etc.)
- Persisted detections table or new metrics columns owned by this app
- Changing Trend heat meaning or redesigning the explanation block
- UK exchange support on Aktier
- Redefining Golden/Death independently of RFC-013
