---
name: build
description: Continue the faredrop product build. Reads docs/build-progress.md, resumes the current phase from docs/build-plan.md exactly where it stopped (or starts the next one), and keeps the tracker updated. Use when the user types /build, or says "continue the build", "resume", "next phase", "build status", or names a build phase.
---

# Continue the faredrop product build

The plan is `docs/build-plan.md` (phases, one prompt each, plus "Shared
context"). The live state is `docs/build-progress.md`. Never ask the user to
paste a phase prompt: read it from the plan.

## Arguments

- none, `continue`, `resume` → resume the current phase.
- `status` → report the tracker's state (phase, progress, blockers, problems,
  next step) and stop; change nothing.
- `phase N` → work on phase N. First check its "Needs" in the tracker's table
  are `done`; if not, say which are missing and ask before going ahead.
- `next` → if the current phase is `done`, start the next phase whose needs are
  met; otherwise resume the current one.
- `side` → the live-deal re-check side thread.

## 1. Load context (every session)

1. `docs/build-progress.md` (the whole file).
2. `docs/build-plan.md`: "Shared context" and the current phase's prompt and
   "Done when". Follow both as if the user had pasted them.
3. `STATUS.md` Handoff, and whatever the phase prompt says to read.

## 2. Reconcile before working

The tracker can be stale if a session ended abruptly. Check it against reality:
`git status`, `git branch --show-current`, `git log --oneline -5`, whether the
files the checklist claims exist, and (if code exists) whether the phase's
tests pass. If reality and tracker disagree, trust reality, fix the tracker,
and note the correction in the session log.

If the working tree has uncommitted changes that aren't part of this phase,
don't touch, stage or stash them; mention them.

## 3. Starting a phase

- Set the phase's row to `in progress` with today's date and the branch.
- Branch `phase-N-<slug>` from the latest `main` (or from the previous phase's
  branch if it isn't merged yet; say which).
- Fill "Current phase checklist" from the phase prompt's numbered steps and its
  "Done when", as checkboxes. Set "Next step" to the first item.

## 4. Work loop

Repeat until a stop condition:

1. Take the first unticked checklist item (or the "Next step").
2. Do it, following Shared context rules: free tools, no secrets, collector
   safety, tests for engine changes, no product decisions changed.
3. **Update the tracker right away**: tick the item, rewrite "Next step" as a
   concrete action a cold session could start on, bump "Last updated".
4. Anything that went wrong or surprised you → "Problems and issues" now, not
   at the end. Anything unclear or contradictory → "Gaps and open questions"
   with a proposed resolution. Anything only the owner can do → "Blocked on
   owner" with exact instructions, and carry on with other unblocked items.

Checkpoint the tracker before any long or risky operation (big refactors,
dependency installs, deploys) so an interruption loses nothing.

## 5. Stop conditions

- **Phase done:** every "Done when" item verified (run the tests, don't assume).
  Mark the row `done` with the date, write a short handoff in the session log,
  set "Current phase" to the next phase whose needs are met, clear and refill
  nothing yet (the next session fills the checklist), and update the
  product-build line in `STATUS.md` Open items. Then ask the user before
  committing or merging.
- **Blocked:** nothing left that doesn't need the owner. Set status `blocked`,
  make "Blocked on owner" precise, and stop.
- **Long session:** if the conversation is getting long, checkpoint the tracker
  with an exact "Next step" and suggest continuing with `/build` in a new chat.

## 6. Every session ends with

- The tracker updated: "Now" block, checklist, problems, gaps, a session log
  entry (date, phase, what was done, where it stopped).
- A short message to the user: what was done, what's next, what is needed from
  them (if anything).
- Commits only after asking, on the phase branch, with no `Co-Authored-By` or
  other trailer (CLAUDE.md).

## Never

- Publish to the design canvas or the architecture page unless the phase says so.
- Write or print secrets, or create accounts, buy things or set secrets for the
  owner: list them under "Blocked on owner".
- Change the product decisions in "Shared context"; record a disagreement as a
  gap instead.
- Mark an item done that wasn't verified.
