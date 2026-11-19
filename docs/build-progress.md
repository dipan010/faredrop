# Build progress

The live tracker for the product build in `docs/build-plan.md`. Every build
session reads this first and updates it as it works, so any new chat can pick
up mid-phase. Run `/build` (or say "continue the build") to resume.

Last updated: 2026-11-15 (tracker created; nothing built yet)

## Now

- **Current phase:** 0 · Canvas → written UI spec
- **Status:** not started
- **Branch:** `phase-0-ui-spec` (create from `main` when starting)
- **Next step:** read `project/canvas.json` from the design canvas and list the
  48 boards grouped into pages (phase 0, step 1).
- **Blocked on owner:** nothing
- **Can run in parallel:** phase 3 (exporter) only needs phase 0.

## Phases

Status values: not started · in progress · blocked · done.

| # | Phase | Needs | Status | Branch | Started | Done |
|---|---|---|---|---|---|---|
| 0 | Canvas → written UI spec | — | not started | | | |
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

- [ ] (filled in when phase 0 starts)

## Blocked on owner

Things only the owner can do (accounts, secrets, domain, purchases, approvals,
product decisions). Each item says exactly what to do and which phase waits.

- (none yet)

## Problems and issues

Open problems found while building: failing tests, bugs, things that didn't
work, surprises in the data. Each: date, phase, what happened, current state.
Move to the decisions log or delete when resolved.

- (none yet)

## Gaps and open questions

Mismatches between the canvas, the specs and the code, or anything the plan
didn't cover. Each: date, phase, the gap, proposed resolution.

- 2026-11-15 · plan · Plus price, domain, email provider, and whether Free gets
  any instant alerts are undecided (needed by phases 5 and 9, not before).
- 2026-11-15 · plan · Live Google deals aren't re-checked on a schedule, so
  "checked X ago" can show days. Side thread measures it; owner decides.

## Decisions log

Decisions made during the build, newest first, with who decided.

- 2026-11-15 · owner · Build follows `docs/build-plan.md`; one phase at a time
  per thread, tracked here.

## Session log

Newest first. One entry per session: date, phase, what was done, where it
stopped.

- 2026-11-15 · setup · Tracker, `/build` skill and CLAUDE.md pointer created.
  Next: start phase 0.
