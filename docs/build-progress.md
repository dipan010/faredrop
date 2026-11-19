# Build progress

The live tracker for the product build in `docs/build-plan.md`. Every build
session reads this first and updates it as it works, so any new chat can pick
up mid-phase. Run `/build` (or say "continue the build") to resume.

Last updated: 2026-11-19 (phase 1 done; CI green)

## Now

- **Current phase:** 2 · Public pages on fixtures (phase 1 done 2026-11-19)
- **Status:** not started
- **Branch:** `phase-2-public-pages`, to be created from `phase-1-foundations`
  (none of phases 0–1 is merged to `main` yet)
- **Next step:** when phase 2 starts, fill this checklist from its prompt in
  `docs/build-plan.md`. Build pages from the components in `web/src/components/`
  and the copy in `docs/ui-spec.md` Appendix A. G53: keep `/dev/` out of
  production.
- **Blocked on owner:** nothing for phase 1. Phase 6 needs G15/G42 decided
  (see "Blocked on owner").
- **Can run in parallel:** phase 3 (exporter) now; its inputs are gaps G3,
  G7, G8, G26, G34–G36.

## Phases

Status values: not started · in progress · blocked · done.

| # | Phase | Needs | Status | Branch | Started | Done |
|---|---|---|---|---|---|---|
| 0 | Canvas → written UI spec | — | done | phase-0-ui-spec | 2026-11-19 | 2026-11-19 |
| 1 | Frontend foundations | 0 | done | phase-1-foundations | 2026-11-19 | 2026-11-19 |
| 2 | Public pages on fixtures | 1 | not started | | | |
| 3 | Exporter | 0 | not started | | | |
| 4 | Read-only site live | 2, 3 | not started | | | |
| 5 | Product API core | 3 | not started | | | |
| 6 | Account pages | 4, 5 | not started | | | |
| 7 | Matching and sending | 5, 6 | not started | | | |
| 8 | Retention | 7 | not started | | | |
| 9 | Plus | 8 | not started | | | |
| — | Side: live-deal re-checks | — | not started | | | |

## Current phase checklist

Copied from the phase's prompt and "Done when" in `docs/build-plan.md` when the
phase starts. Tick items as they are finished; add sub-items as work reveals
them.

- [x] 1. Scaffold `web/` (pinned exact: astro 7.4.5, @astrojs/preact 6.1.1,
  preact 11.1.1, typescript 6.0.3, @astrojs/check 0.9.12, @playwright/test and
  playwright-core 1.64.1, @axe-core/playwright 4.14.0, @fontsource inter and
  space-grotesk 5.3.0; each the newest release at least 2 weeks old).
  Cloudflare Pages free limits are in `web/README.md`, read from the docs.
- [x] 2. `tokens.css` generated from the spec table. `npm run tokens`: all 36
  tokens match in 3 blocks, and 46 contrast pairs pass, including the 3:1
  for `--faint` (G31 → `#82858C`). Fonts are self-hosted via @fontsource
  (G32). `:focus-visible` comes from the canvas. ThemeSwitch cycles
  system/light/dark, stores the choice in localStorage inside try/catch, and
  an inline head script sets it before first paint (G33).
- [x] 3. C1–C31 are in `web/src/components/`: chrome in `.astro`, the rest in
  Preact `.tsx`. The islands are chips, code input, switch, option cards,
  booking panel and sheet, watch route, toast, accordion, bar chart and theme
  switch.
- [x] 4. `/dev/components` shows every component in a light and a dark
  panel. Playwright screenshots were taken at 390 and 1440.
- [x] 5. Playwright + axe (`web/tests/gallery.spec.ts`), 7 tests pass
  locally:
  - axe at 390 and 1440 in both page themes, with no rules disabled;
  - no horizontal overflow;
  - the email shell;
  - the theme switch;
  - the sheet's focus trap.

  The `web` job is added to `check.yml` and needs no secrets. Not yet run
  on GitHub (it needs a push).
- [x] 6. `web/src/data/`:
  - LLD types (snapshot, API shapes) and the spec §2 formatters;
  - a fixture adapter that validates against LLD §3 at build time (a broken
    fixture fails `astro build`, which I tested);
  - a fixture clock;
  - an `apiSource` stub.
- [x] Done when:
  - [x] axe passes;
  - [x] the CI job is green: run 44515248672 on 7713f18, both `check` and
    `web` passed. The first run failed because `@types/node` was missing
    (fixed).
  - [x] the gallery matches the canvas side by side in both themes and both
    widths. The owner looked on 2026-11-19 and said it "looks fine". They will
    raise any differences once the product pages are built.
- Out of scope: product pages, backend, deployment

## Blocked on owner

Things only the owner can do (accounts, secrets, domain, purchases, approvals,
product decisions). Each item says exactly what to do and which phase waits.

- **G51:** approve or reword the strings that have no board
  (`docs/ui-spec.md` §7, "Found in phase 1").

- **Push and merge when ready:** `docs/product-design` (HLD, LLD, plan, build
  files) and `phase-0-ui-spec` (spec, fixtures) are committed locally, not
  pushed.
- **Before phase 6** (`docs/ui-spec.md` §7):
  - G15/G42: whether Free gets any instant alerts, and whether sign-up starts
    a 14-day trial. These set the setup defaults and My alerts limits.
  - G18: whether "Send me a sample alert" counts as a test card. Keep it or
    drop it.
  - G16: the consent wording at sign-up (or accept the proposed line).
- **Before phase 2 copy is final:**
  - G38: drop "Saved-deal tracking" and "Filters that stick" from the Plus
    perks, or gate them in the LLD.
  - G39: drop "and month" from the Plus card.
  - G43: which deals the landing page's "recent deals" may show (CCU→FRA is
    rated wrong).
  - G44: soften "Still there an hour later".
  - G9: drop the airline-site booking link.
- **Before phase 9:** G25, hosted checkout instead of our own card and UPI
  field (proposed: yes).
- **Optional, any time:** G34, allow copying real sibling-deal rows (prices)
  from a decrypted scratch copy of the DB into the fixture for phase 2's group
  chips. Otherwise phase 2 waits for phase 3's real snapshot.

## Problems and issues

Open problems found while building: failing tests, bugs, things that didn't
work, surprises in the data. Each: date, phase, what happened, current state.
Move to the decisions log or delete when resolved.

- 2026-11-19 · 1 · `npm audit` flags astro ≤ 7.4.6 (GHSA-r3h5-4585-7x3w,
  moderate). It is in `@astrojs/node`'s image endpoint, which a static Pages
  build doesn't use. Staying on 7.4.5 (the 2-week rule); move to ≥ 7.4.7 once
  it is 2 weeks old (after 2026-11-20 or so).
- 2026-11-19 · 1 · G31's proposed `#8A8D94` is 3.05:1 on `--bg` and 2.91:1 on
  `--chip`, so it fails where unchecked boxes sit on chips. Used `#82858C`
  (3.24:1 or better on surface, bg, surface2 and chip). axe can't check this
  (it only checks text contrast), so `web/scripts/check-tokens.mjs` does.
- 2026-11-19 · 0 · The canvas has 41 boards, not the 48 the plan and handoff
  say (G37). All 41 are covered. Proposed: say 41 in the plan when it's next
  edited.
- 2026-11-19 · 0 · Light `--faint` (#9A9DA4) is 2.7:1 on white, under the 3:1
  that non-text checkbox and radio borders need (G31). Proposed #8A8D94
  (3.3:1); phase 1's axe run confirms it.
- 2026-11-19 · 1 · Astro 7's `astro preview` detaches into the background
  when it has no terminal, so Playwright's webServer saw an early exit, and a
  leftover daemon then served a stale build. Fixed: tests serve `dist/` with
  `web/scripts/serve.mjs`.
- 2026-11-19 · 1 · `@axe-core/playwright` pulled `playwright-core` 1.65.1
  (released that day) as a peer, which broke the types against
  `@playwright/test` 1.64.1. Fixed: `playwright-core` is pinned to 1.64.1.
  Transitive deps (vite and others) follow their ranges, pinned by
  `package-lock.json`.
- 2026-11-19 · 1 · Astro sends anonymous telemetry by default. Turned off in
  every npm script and in CI (`ASTRO_TELEMETRY_DISABLED=1`).

## Gaps and open questions

Mismatches between the canvas, the specs and the code, or anything the plan
didn't cover. Each: date, phase, the gap, proposed resolution.

- 2026-11-15 · plan · Plus price, domain, email provider, and whether Free gets
  any instant alerts are undecided (needed by phases 5 and 9, not before).
- 2026-11-15 · plan · Live Google deals aren't re-checked on a schedule, so
  "checked X ago" can show days. Side thread measures it; owner decides.
- 2026-11-19 · 0 · 45 canvas↔LLD gaps, each with a proposed resolution, are in
  `docs/ui-spec.md` §7 (G1–G45), tagged owner / spec / lld / data.
  - **LLD changes proposed** (to apply when phase 3/5 touch the LLD):
    - G7: `usual_is_estimate`;
    - G8: `found_by`;
    - G26: an `ops` block;
    - G36: `pipeline.dup_rule`;
    - G22: reason storage;
    - G23: a contact endpoint;
    - G24: export as a download;
    - G27/G28: verdict names and the owner's write path;
    - G29: the digest is live-only.
  - **Screens with no board** (G2): the sign-in code email, the
    account-deleted email, the `/f/` thank-you page, the watch email and
    receipts.
- 2026-11-19 · 1 · Phase 1 added gaps G46–G53, written into
  `docs/ui-spec.md` §7 under "Found in phase 1", each with a resolution:
  - G46: the price-bar scale rule;
  - G47: where emails render (phase 7);
  - G48: the dark logo arrow colour;
  - G49: shared components are Preact `.tsx`, not plain Astro;
  - G50: `tokens.css` vs the LLD's `theme.css`;
  - **G51:** copy with no board needs the owner's OK;
  - G52: API response bodies are proposed in `types.ts`;
  - G53: exclude `/dev/` from production in phase 4.

  BookingPanel hides the airline-site row by default (G9 applied
  provisionally, `airlineLink` prop).

## Decisions log

Decisions made during the build, newest first, with who decided.

- 2026-11-19 · owner · Phase 1 gallery accepted against the canvas ("looks
  fine"). Any visual differences get raised after the product pages are built.
- 2026-11-15 · owner · Build follows `docs/build-plan.md`; one phase at a time
  per thread, tracked here.

## Session log

Newest first. One entry per session: date, phase, what was done, where it
stopped.

- 2026-11-19 · 1 · Phase 1 done.
  - The owner accepted the gallery against the canvas.
  - Committed cbb4ae7 and 7713f18 (the fix adds `@types/node` for CI) and
    pushed `phase-1-foundations`. That push also published `docs/product-design`
    and `phase-0-ui-spec`, with the owner's OK.
  - CI is green on both jobs.
  - Handoff: phase 2 builds the public pages from `web/src/components` on the
    sample fixture. Phase 3 (the exporter) can run in parallel.
  - Still open for the owner: G51 copy, and the phase 2 copy items G38, G39,
    G43, G44 and G9.
- 2026-11-19 · 1 · Started phase 1 on `phase-1-foundations`, branched from
  `phase-0-ui-spec`.
  - Built `web/`: pinned toolchain, tokens and the check script, fonts,
    theme switch, all 31 components, the gallery, the data module, Playwright
    + axe (7 tests pass locally), the CI job and `web/README.md`.
  - Updated spec G31 to `#82858C`.
  - Stopped at the owner's canvas sign-off and the push for CI. Nothing is
    committed yet.
  - The owner's WIP in `src/`, `tests/` and `routes/` was not touched.
- 2026-11-19 · 0 · Committed the build files to `docs/product-design`
  (5206662, owner approved). Branched `phase-0-ui-spec` from it, because
  `main` lacks the HLD, LLD and plan.
  - Read all 41 canvas boards (version `1795082767-d03c`).
  - Wrote `docs/ui-spec.md`: the board→page map, 19 pages + 5 emails, a token
    table generated from the canvas CSS, contrast pairs (light computed), the
    email palette, type, spacing, radii and focus, 31 components, the fixture
    summary, placeholders, gaps G1–G45, and Appendix A with verbatim copy
    generated from the boards.
  - Wrote `docs/fixtures/snapshot.sample.json`: 7 deals, values from the
    canvas, STATUS and history only. Its sources are in
    `docs/fixtures/README.md`.
  - Added `tools/check_fixture.py`, which reads the contract from `docs/lld.md`
    and was tested against a deliberately broken copy (it caught all 7 errors).
  - Updated the STATUS.md product-build line.
  - The owner approved the commit on `phase-0-ui-spec`.
    The owner's WIP (`src/config.py`, `src/notify.py`,
    `tests/test_pipeline.py`, `routes/places.json`) was not touched.

- 2026-11-15 · setup · Tracker, `/build` skill and CLAUDE.md pointer created.
  Next: start phase 0.
