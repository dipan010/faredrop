# Build progress

The live tracker for the product build in `docs/build-plan.md`. Every build
session reads this first and updates it as it works, so any new chat can pick
up mid-phase. Run `/build` (or say "continue the build") to resume.

Last updated: 2026-11-19 (phase 0 done and committed)

## Now

- **Current phase:** 1 · Frontend foundations (phase 0 done 2026-11-19)
- **Status:** not started
- **Branch:** `phase-1-foundations`, to be created from `phase-0-ui-spec`
  (or from `main` once `docs/product-design` and `phase-0-ui-spec` are merged)
- **Next step:** when phase 1 starts, fill this checklist from its prompt in
  `docs/build-plan.md`. Before scaffolding `web/`, read `docs/ui-spec.md`
  sections 3–4 (tokens and components) and gaps G31–G33.
- **Blocked on owner:** nothing for phase 1. Phase 6 needs G15/G42 decided
  (see "Blocked on owner").
- **Can run in parallel:** phase 3 (exporter) now; its inputs are gaps G3,
  G7, G8, G26, G34–G36.

## Phases

Status values: not started · in progress · blocked · done.

| # | Phase | Needs | Status | Branch | Started | Done |
|---|---|---|---|---|---|---|
| 0 | Canvas → written UI spec | — | done | phase-0-ui-spec | 2026-11-19 | 2026-11-19 |
| 1 | Frontend foundations | 0 | not started | | | |
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

- [x] 1. Read canvas files (41 boards, not 48: see gaps) (`project/canvas.json`, then each `.dc.html`); group the 48 boards into ~20 pages
- [x] 2. Per page: route, purpose, sections, controls, states, data (lld names), phase, source boards
- [x] 3. Design tokens exactly from the canvas (light/dark vars, type, spacing, radii, focus), contrast pairs
- [x] 4. Reusable components (~20): props, variants, states, used by
- [x] 5. Copy: every user-facing string per page; placeholders marked
- [x] 6. `docs/fixtures/snapshot.sample.json` shaped like lld §3, canvas deals only
- [x] 7. Gaps/contradictions canvas vs lld, each with a proposed resolution
- [x] Done when: spec covers every board; token table matches canvas; fixtures validate against lld field list; gaps listed
  (verified by script: 41/41 boards in §1 and Appendix A; 36/36 tokens match the
  canvas blocks; `tools/check_fixture.py` 0 failures, 1 known gap G35; G1–G45 defined)

## Blocked on owner

Things only the owner can do (accounts, secrets, domain, purchases, approvals,
product decisions). Each item says exactly what to do and which phase waits.

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

- 2026-11-19 · 0 · The canvas has 41 boards, not the 48 the plan and handoff
  say (G37). All 41 are covered. Proposed: say 41 in the plan when it's next
  edited.
- 2026-11-19 · 0 · Light `--faint` (#9A9DA4) is 2.7:1 on white, under the 3:1
  that non-text checkbox and radio borders need (G31). Proposed #8A8D94
  (3.3:1); phase 1's axe run confirms it.

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

## Decisions log

Decisions made during the build, newest first, with who decided.

- 2026-11-15 · owner · Build follows `docs/build-plan.md`; one phase at a time
  per thread, tracked here.

## Session log

Newest first. One entry per session: date, phase, what was done, where it
stopped.

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
