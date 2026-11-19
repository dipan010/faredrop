# faredrop: handoff prompt for the next session

Paste everything below the line into a new Claude Code chat opened at the repo root.

---

You're continuing work on **faredrop**, my personal fare-deal alert for Indian cities.
I'm turning it into a consumer product. Read `CLAUDE.md`, then `STATUS.md` (Handoff), then
`docs/build-progress.md`, before you do anything else.

## Where things stand (as of 2026-11-19)

**The engine (exists, runs free on GitHub Actions):**
- Workflows:
  - `collect.yml` runs every 2 h and collects Travelpayouts prices (discovery and baselines only).
  - `gf.yml` runs hourly and does the Google Flights lookups, capped by `GF_DAILY_LOOKUPS`=60. It's scraping, so the cap is only raised after days without a block.
  - `calendar.yml` runs the calendar scan.
- The DB is encrypted SQLite on the `data` release (`dbstore.py`; never weaken its guards).
- The `deal` table:
  - Google deals have `source='google_flights'` and `observation_id = -gf_quote.id`.
  - `gf_status` is one of still/gone/skipped/error. Other fields: `notified_at`, `fingerprint`.
  - The judging columns in `gf_quote` are usual, range_low, range_high, airline and via.
- Emails:
  - `notify.py` sends them; `notify._card` renders email-safe HTML.
  - Near-duplicates are suppressed within `NOTIFY_DUP_DAYS`=14 and `NOTIFY_DUP_DEPART_DAYS`=7, unless the new fare is at least 5% cheaper (`NOTIFY_DUP_CHEAPER`).
  - `digest.booking_url` builds the Google Flights link.
- `MIN_ABS_SAVING`=4000.
- Existing backend capabilities, counted against the product designs: 11 exist, 8 are partial, 14 are missing.

**Product decisions (mine, don't change them):**
- Email only. WhatsApp is dropped.
- No test cards in the UI. That's a separate background job.
- Hide the cities and destinations added on 13/14 Nov from the UI. Their deals, verdicts, budget changes and data stay.
- The product allowlist:
  - Airports: BLR MAA COK HYD GOI GOX BOM CCU.
  - Destinations (25): DXB AUH SHJ DOH MCT BAH KWI SIN KUL BKK HKT DPS SGN CMB MLE KTM HKG TYO SEL LON PAR FRA AMS IST SYD.
  - Regions: gulf, sea, near (CMB MLE KTM), east (HKG TYO SEL), europe (LON PAR FRA AMS IST), aus (SYD).
- Free tools only. Explain what "free" means before recommending anything.

**Designs and docs produced:**
- Design canvas, a clickable prototype with about 48 boards: https://claude.ai/artifact/GBnLGrXQ5L1bnpGKmnPGDr
  - Web: landing, onboarding, sign-in, feed, deal detail (plus one-stop and no-range variants), saved, settings, upgrade/expired/empty.
  - Phone versions of every screen.
  - Emails: alert, weekly digest, price change, account emails.
  - Manage Plus, the share page and its preview, ops health, feedback, dark mode, and the legal/housekeeping pages.
  - Read it with the Artifact tool (`read`). My earlier local copy was in a scratchpad and may be gone.
- Architecture page with diagrams, 17 D1 tables, the ingest payload and a per-user near-duplicate checker: https://claude.ai/artifact/6rCxMX8jAVoeionrv1dJJ8
- `docs/hld.md` and `docs/lld.md`, committed in ea2cc1c.
- `docs/build-plan.md`: phases 0–9, one prompt each, plus "Shared context".
- `docs/build-progress.md`: the live tracker, currently at phase 0, not started.
- `.claude/skills/build/SKILL.md`: the `/build` skill (resume, status, phase N, next, side).

**Target architecture:**
- Hosting: Cloudflare Worker (TypeScript) + D1 + Pages.
- Exporter `src/export.py`:
  - Read-only, the last non-blocking step in `gf.yml`.
  - POSTs a full snapshot signed with HMAC-SHA256 (`X-Faredrop-Timestamp`/`X-Faredrop-Signature`, 300 s window, `run_id` idempotency).
- Email via Resend: 100/day free, so `EMAIL_DAILY_CAP`=95.
- Payments later via Razorpay. Ops pages behind Cloudflare Access.
- Frontend: Astro + Preact islands + TypeScript + plain CSS tokens in `web/`, built on fixtures first, tested with Playwright + axe.

**Build phases:**

| # | Phase | Needs |
|---|---|---|
| 0 | Canvas → UI spec | — |
| 1 | Frontend foundations | 0 |
| 2 | Public pages on fixtures | 1 |
| 3 | Exporter | 0 |
| 4 | Read-only site live | 2, 3 |
| 5 | Product API core | 3 |
| 6 | Account pages | 4, 5 |
| 7 | Matching and sending | 5, 6 |
| 8 | Retention | 7 |
| 9 | Plus | 8 |

Side thread: live-deal re-checks.

**Git state:**
- Branch `docs/product-design`. Commit ea2cc1c holds the HLD, LLD, build plan and the STATUS update. It isn't pushed or merged.
- Uncommitted build-system files: `CLAUDE.md`, `docs/build-plan.md`, `docs/build-progress.md`, `.claude/skills/build/`, `docs/next-session-prompt.md`.
- Uncommitted changes of mine, not part of the build (don't touch, stage or stash them): `src/config.py`, `src/notify.py`, `tests/test_pipeline.py`, `routes/places.json`.

**Problems hit before (avoid repeating them):**
- Canvas publish conflicts. Always read the remote copy and merge before republishing.
- Don't put `sc-for` inside `<select>`/`<tbody>`: the parser hoists it.
- Use ’ instead of apostrophes inside single-quoted JS strings in canvas files.
- No invented facts in the UI: no made-up durations, airlines, "often cheaper" claims or domains. Use real data from the DB, or leave it out.
- The 13/14 Nov hide rule applies to routes only, not to deals or data.
- Every themed screen needs `:focus-visible`.

**Open decisions I still owe:**
- Plus price.
- Domain.
- Email provider (Resend proposed).
- Whether Free gets any instant alerts.
- The re-check budget for live Google deals. They aren't re-checked on a schedule, so "checked X ago" can be days old.

**Hard rules:**
- No secret or key is ever committed, printed, or put in a URL; the repo is public.
- Commit messages carry no `Co-Authored-By` or any other trailer.
- Setting repository secrets and creating accounts are my job.
- Never pull GitHub's DB into `data/faredrop.db`. Decrypt into a scratch path to inspect it.
- Google data stays in `gf_raw`/`gf_quote`.
- Never tune thresholds on `tools/simulate.py` output.

## What to do now

1. Ask me whether to commit the uncommitted build-system files listed above to `docs/product-design`. Commit only those files, with no trailer.
2. Then run the `build` skill (`/build`). Start phase 0 from the tracker:
   - Read `project/canvas.json` from the design canvas.
   - Group the 48 boards into pages.
   - Write the UI spec on branch `phase-0-ui-spec`.
   - Update `docs/build-progress.md` as you go.
