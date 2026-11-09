# Feature Specification: Load Only What the Aktier Page Shows

**Feature Branch**: `033-exchange-page-load`

**Created**: 2026-11-09

**Status**: Draft

**Input**: User description: "when i click on a stock exchange button, only download the market/index data and the first 25 stocks visible on page 1. When I click on the button "Nasta" then download the following 25 stocks and so on. I want maximum 0.5 second wait time for the user"

## Context *(2026-11-09)*

- Today, pressing a börs button loads **every** stock of that börs (all names, their latest prices, and a year of SMA history for each) before page 1 is shown — only to build the **Industri** filter choices — and the page then asks for all remaining pages in the background. On NASDAQ that is ≈3 300 names per press.
- The stock data store was made faster for single-stock and 25-stock lookups on 2026-11-09 (fansboda-finance spec 009): a page of 25 names now takes ≈1 ms to look up, while whole-börs reads still take ≈0.1–0.3 s each, and several of them run per press.
- This feature changes **what** Aktier loads and **when**, not how stocks or indices are calculated.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A börs press shows the index table and page 1 quickly (Priority: P1) 🎯 MVP

A signed-in invited person opens **Aktier** and presses a börs button (NASDAQ, NYSE, OMX Stockholm, FTSE). Only what page 1 shows is loaded: the börs's index table (market index and sector indices) and the first 25 names of the stock table. The person sees both tables, the total number of names for the börs, and **Nästa** / **Föregående**, within 0.5 seconds.

**Why this priority**: The wait after a börs press is the reported problem; it is the first thing every visit does.

**Independent Test**: Sign in, press NASDAQ (the largest börs). Time from press to both tables visible is ≤ 0.5 s; page 1 shows the same 25 names, values, Trend colours, Signal, and Industri as today; the total count is the same as today; no other page of names is loaded.

**Acceptance Scenarios**:

1. **Given** a signed-in invited person on Aktier, **When** they press a börs button, **Then** the index table and the first 25 names appear within 0.5 s.
2. **Given** that first page, **When** they look at it, **Then** the names, order (default name/symbol order), values, Trend colours, Signal, Industri, and total count are the same as before this change.
3. **Given** that first page, **When** nothing else is pressed, **Then** no further pages of names are loaded in the background.
4. **Given** a börs with 25 or fewer names, **When** they press it, **Then** all its names show on one page and **Nästa** is not usable.
5. **Given** the **Industri** filter on the stock table, **When** they open it on page 1, **Then** it offers the same sector types as today without the whole börs being loaded first.

---

### User Story 2 - Nästa / Föregående load one page at a time (Priority: P1)

The same person presses **Nästa**. Only the next 25 names are loaded and shown, within 0.5 s. **Föregående** returns to the previous 25, within 0.5 s (immediately if that page was already shown in this visit).

**Why this priority**: Paging is the other everyday action; without it the fast first page is a dead end.

**Independent Test**: On NASDAQ, press **Nästa** five times and **Föregående** twice; every press shows its 25 names within 0.5 s, each page equals the matching page of today's list, and only the requested page was loaded.

**Acceptance Scenarios**:

1. **Given** page N of a börs, **When** they press **Nästa**, **Then** names N×25+1 … N×25+25 (or the remaining names) appear within 0.5 s, and only those names were loaded.
2. **Given** page N > 1, **When** they press **Föregående**, **Then** the previous 25 appear within 0.5 s.
3. **Given** a page already shown in this visit, **When** they return to it (paging or coming back from a chart), **Then** it appears without loading again.
4. **Given** the first page, **Then** **Föregående** is not usable; **given** the last page, **then** **Nästa** is not usable.
5. **Given** the index table, **When** they page the stock table, **Then** the index table is not reloaded and keeps its order.

---

### User Story 3 - Sort and Industri filter still work (Priority: P2)

The person sorts the stock table by **Trend**, **Signal**, or **Bolag**, or filters it by an **Industri** sector type, and pages through the result.

**Why this priority**: These exist today (specs 014, 026); the faster loading must not break them, but they are used less often than a plain press and paging.

**Independent Test**: On NASDAQ sort by Trend, then filter by Technology, then page with **Nästa**; results match today's ordering and filtering over the whole börs, and every press shows its page within 0.5 s.

**Acceptance Scenarios**:

1. **Given** a börs, **When** they sort by Trend, Signal, or Bolag, **Then** the order is the same as today, across the whole börs (not only the loaded page), from page 1, within 0.5 s.
2. **Given** a sector type chosen in **Industri**, **Then** only names of that sector type appear, across the whole börs, from page 1, within 0.5 s.
3. **Given** a sort or filter is on, **When** they press **Nästa**, **Then** the next 25 of the sorted / filtered list appear within 0.5 s.
4. **Given** stock **Återställ**, **When** pressed, **Then** sort and filter clear and page 1 of the default order appears within 0.5 s.

---

### Edge Cases

- Signed-out or non-invited access stays blocked; nothing is loaded or shown.
- Switching börs drops the previous börs's pages, sort, and filter, and loads only the new börs's index table and page 1.
- A page number beyond the last page (old link, list shrank after the weekly update) shows the last page, as today.
- Names stored without a latest price row are not counted or shown, as today; the total equals the number of names that can be shown.
- The weekly data update (Saturday) changes prices: pages shown before and after it may differ; pages already kept from before the update are not mixed with new pages in one list without a reload.
- Opening a chart and returning restores börs, page, sort, and filter without loading more than that page (spec 008 behaviour kept).
- The first request after the stock data store has been idle (it pauses after a few idle minutes to stay free) may be slower than 0.5 s; the limit applies while the data store is awake. The data store is not kept awake for this feature.
- Table columns, Trend colours, Signal rules, heat scale, index table contents and sort, mobile layout, login, and the electricity landing page are unchanged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Pressing a börs button MUST load only that börs's index-table rows and the stock-table rows for page 1 (≤ 25 names), plus what is needed for the total count and the Industri filter choices.
- **FR-002**: Pressing **Nästa** or **Föregående** (or opening a page link) MUST load only the requested page's ≤ 25 names, unless that page is already kept for this visit.
- **FR-003**: Aktier MUST NOT load further pages in the background.
- **FR-004**: From press to visible tables MUST take ≤ 0.5 s for a börs press, **Nästa**, **Föregående**, a sort, an Industri filter choice, and stock **Återställ**, on the largest börs, while the data store is awake.
- **FR-005**: Page contents, default order, values, Trend colours, Signal, Industri, and total count MUST equal today's for the same page.
- **FR-006**: **Industri** filter choices MUST be the börs's stored sector types, as today, obtained without loading every name of the börs.
- **FR-007**: Sort (Trend, Signal, Bolag) and the Industri filter MUST keep applying to the whole börs, as today, and their pages MUST then load one page at a time.
- **FR-008**: Kept pages MUST be reused when returning to a page or from a chart in the same signed-in visit, and dropped on logout, as today.
- **FR-009**: Access rules, table layout, chart pages, login, and the electricity landing page MUST NOT change.
- **FR-010**: This feature MUST NOT change stored stock or index data or how it is calculated.

### Key Entities

- **Börs view**: the selected börs's index table plus one page of the stock table, with total count, current page, sort, and filter.
- **Stock page**: up to 25 stock rows in the current order; loaded on demand, kept for the visit.
- **Industri choices**: the börs's stored sector types, taken from the börs's sector indices / stored names, not from loading every page.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On NASDAQ, 95 % of börs presses show both tables within 0.5 s (measured from press to visible tables, 20 presses).
- **SC-002**: 95 % of **Nästa** / **Föregående** presses show the new page within 0.5 s.
- **SC-006**: 95 % of sort, Industri filter, and Återställ presses on NASDAQ show page 1 of the result within 0.5 s.
- **SC-003**: A börs press loads at most 25 stock rows; each page press at most 25 more (0 when kept).
- **SC-004**: 100 % of pages match today's page contents and order for the same börs, page, sort, and filter.
- **SC-005**: Sort, Industri filter, Återställ, chart round-trip, and access rules behave as today in a review pass on all four börser.

## Assumptions

- Page size stays 25; button labels stay **Nästa** / **Föregående** ("Nasta" in the request).
- "Market/index data" means the index table for the chosen börs (market index and sector indices) with its Signal, as shown today.
- The 0.5 s limit is measured as the person sees it on a normal connection, server and data store included, for the largest börs (NASDAQ ≈ 3 300 names).
- The faster per-stock lookups delivered on 2026-11-09 (fansboda-finance spec 009) are in place.
- Total count may be computed without loading the names' prices and history.
- One data store and one web server, as today; no new paid service.
- All timing targets assume the data store is awake; it is not kept awake (clarified 2026-11-09, Q2: A).
- Sort and Industri filter keep whole-börs scope and meet the same 0.5 s limit (clarified 2026-11-09, Q1: A); this likely needs the values they sort and filter on (Trend, Signal, Bolag, Industri) to be ready for lookup rather than computed from every name's history on each press — a design question for the plan.
