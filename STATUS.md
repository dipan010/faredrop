# faredrop — Status

Last reviewed: 2026-10-20 (repo reorganised into folders; dated history moved to `docs/history.md`)

| Built | Documented | Hosted | Posted |
|---|---|---|---|
| ✅ Travelpayouts collector (history) + Google Flights deal finder (`src/gfcollect.py`) + confirm/notify/health, 193 token-free checks, CI | ✅ README, this file, `docs/history.md`, CLAUDE.md rules | ✅ GitHub Actions (`collect.yml` every 2 h, `gf.yml` hourly); encrypted history on the `data` release; laptop is watchdog only | ❌ |

## Handoff — where the project is (2026-10-19)

**What it is.** A personal fare-deal alert in the style of Zomunk, for Indian departure cities, run free on GitHub Actions. Repo: https://github.com/dipan010/faredrop (public). Email alerts go to the owner. Deals can be rated on a private review page: https://claude.ai/artifact/FKn5RLNgx8sxmbBpLoYZc4

**How it works now**
1. **History (Travelpayouts, `collect.yml`, every 2 h, idempotent per UTC day):** 302 international routes from 21 Indian origins (`routes/routes.json`, added add-only by `src/routes.py`). One `/v1/prices/calendar` call per route, plus the per-month `/v1/prices/cheap` walk for the original 23 BLR routes: 440 cells a day. Complete every day since Oct 4 (Oct 3 was lost on the laptop era). 6,737 raw responses and 145 route-month baselines as of Oct 19. Used for discovery and as a sanity check, **never as a judge of a deal**: its cheapest fares are often Russian-market seller prices (see "Finding 2026-10-12" in `docs/history.md`).
2. **Deals (Google Flights, `gfcollect.py`, `gf.yml` hourly plus a step in `collect.yml`):** watches `ALERT_ORIGINS` (BLR, MAA, COK, HYD, GOI, GOX) × 25 destinations (`routes/gf_routes.json`), any 2–21-night trip 7–180 days out. 25% of lookups explore the 16 other origins for review only (never emailed). An unfiltered search reads Google's own price insights (usual price, typical range, ~62-day history). Candidate = fare ≤ bottom of the typical range and ≥ ₹4,000 under usual. Confirmed **in a later run** with a filtered search (≤1 stop, no self-transfers): the fare must reproduce within 5%, and Google's usual must fit Travelpayouts' typical (0.6–1.6×) with the deal below it. Only then is it a deal; email goes out only for `ALERT_ORIGINS`.
3. **Google budget:** 80 requests a day (40 until 2026-10-19), 15 per run, shared with the re-check (`verify.py`, which confirms Travelpayouts deals from alert cities only). Spaced ~40 s; one retry 90 s after a refusal; a refused confirmation is owed to the next run; a page that prices nothing is recorded and skipped; discovery skips a route whose last 3 pages all priced nothing (`GF_DEAD_LOOKUPS`), then probes it with one lookup after 14 days, doubling the wait with each further empty page, up to 60.
4. **Storage and safety:** history = AES-256 snapshots on the `data` prerelease (`dbstore.py`: never restores empty, never uploads a smaller DB, newest 12 plus one a day kept). Key `FAREDROP_DB_KEY` is in `~/.faredrop.env`, the repo secret, and the user's password manager. Secrets in the repo: `TRAVEL_PAYOUTS_API_KEY`, `FAREDROP_DB_KEY`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`. Alerts: `health.py` (per-day coverage, once), `watchdog.py` on the laptop (alerts if snapshots go >30 h stale).

**Results so far**
- Google since the Oct 16 fix: uses the full 40/day, ~80% answered (Oct 16–19: 30/40, 32/40, 32/40, 32/38), against ~70% at 13–15/day on Oct 14–15. The cap was spent by ~06Z each day. 119 lookups: 64 with insights, 55 priced nothing (46%).
- **The "priced nothing" pages cluster on routes:** GOI→SHJ 11/11, GOI→HKT 9/9, GOI→KTM 9/9, GOI→MLE 8/8 = 37 of the 55. GOI took 60 of 75 discovery lookups (its Travelpayouts fares look cheapest against their medians); BLR, COK and MAA discovery priced every page. Judging searches are also limited to ≤1 stop (`MAX_STOPS`), so these routes have no ≤1-stop itinerary from GOI on Google: perhaps the flights use Mopa (GOX), perhaps no 1-stop connection exists. Either way nothing emailable is lost by skipping them.
- Status check 2026-10-19: all `collect.yml` and `gf.yml` runs since Oct 12 succeeded (none cancelled); Travelpayouts 440/440 every day Oct 12–19. No new Google candidate since Oct 17 (4 in all: 2 confirmed, 2 rejected by the cross-check). One unconfirmed Travelpayouts deal, DEL→MOW Nov 10–Dec 7 ₹29,719 (Oct 17): not an alert city, so never checked on Google or emailed, and left off the review page.
- Deal emails: **GOI→DXB 1–15 Nov, ₹33,883 vs Google's usual ₹38,609** (emailed Oct 17; not yet on the review page). The **GOI→CMB ₹46,552** email on Oct 12 was **wrong**: Google served an incomplete page. That led to the later-run confirmation and the Travelpayouts cross-check. Since then, two GOI→CMB candidates were correctly rejected (Google's usual ~₹69k vs Travelpayouts' ~₹31k).
- Review verdicts (2026-10-19): the 3 DEL Travelpayouts "deals" wrong; GOI→CMB (Oct 12, before the later-run confirmation) **wrong**; GOI→DXB (confirmed, TP typical ~₹37,900 over 51 fares) **good**. Google deal emails: 1 good, 1 wrong; since the Oct 12 fix, 1 of 1 good (n too small to mean much). 1 of ~15 rated deals toward tuning.

**Next actions, in order**
1. [x] GOI→DXB added to the review page and rated good; GOI→CMB rated wrong (2026-10-19).
2. [x] Budget 40 → 80 a day (user's decision, 2026-10-19), `GF_PER_RUN` stays 15. "Days without a block" read as no wholesale refusal; ~20% single refusals still happen daily. **Watch Oct 20–22:** answer rate (stop raising, or step back, if it falls well under ~75%; Oct 19, first day: 62 of 69 answered, the 80 cap not reached because GitHub started few runs), and Travelpayouts still 440/440 (gf runs now work later into the day and share the `collect` concurrency group).
3. [x] Priced nothing: four GOI routes (see Results). Discovery now skips dead routes (user's decision, 2026-10-19); on Oct 19's data that is GOI→HKT/KTM/MLE/SGN/SHJ. Check on Oct 22 that the empty-page share fell. Back-off added the same day (a plain 14-day window would have cost 3 lookups per dead route per 14 days): GOI→SGN gets its probe ~Nov 2, the other four wait 60 days.
4. [x] **Goa's Mopa airport (GOX) added 2026-10-19 (user's decision; its deals are emailed).** A laptop probe (3 lookups, Nov 20–27): GOI→SHJ priced nothing, GOX→SHJ ₹60,903 Air Arabia non-stop with insights, GOX→MLE nothing. Travelpayouts' reference data puts GOX in city GOI and we query by city, so its "GOI" fares cover both airports; they drive discovery and the cross-check for both (`TP_CITY`). One-time cost: up to ~75 lookups (3 per GOX route) to learn which of the 25 exist, during which GOX takes most new lookups. **Check by Oct 22:** which GOX routes price; whether a GOX deal passes the cross-check; and **compare GOX→CMB's Google usual with GOI's ₹67–69k** (same on Oct 12 and twice Oct 17). If GOX's is far lower, the Oct 12 GOI→CMB email was an airport mismatch (a Dabolim-only market judged against Travelpayouts' all-Goa ₹31k and the user's all-Goa ₹22,410), not an incomplete page: revise that finding, change no rules over it. Note: Goa takes most discovery picks (60 of 75, Oct 16–19), and GOX, unseen so far, takes them first; revisit in item 6.
5. [x] **Dates agreed 2026-10-19:** usable = Oct 17 (first correct confirmed deal email); done ≈ Nov 9–16, when ~15 deals are rated. It holds only if the review page is refreshed every 2–3 days in a session and the user rates as deals arrive. Old note: Re-plan the dates: "usable" slipped from Oct 18. Deals now flow, about 1 confirmed per 2–3 days. Tuning needs ~15 rated deals, so "done" is likely early-to-mid November, not Oct 30. Agree a new date with the user.
6. After about 2 weeks of data: candidate and deal rate by `gf_quote.reason` (discovery vs exploration vs review), then move budget to what finds deals; tune `GF_BELOW_RANGE_LOW` / `MIN_ABS_SAVING` on verdicts.
7. Then the decision point (personal tool vs product) and Stage 3 (holiday-aware ranking).

**How to inspect production data:** decrypt the newest `data` asset into a scratch path, never into `data/faredrop.db`. The `gh` CLI isn't logged in; use the git keychain credential as `GH_TOKEN` (`git credential fill`), never printing it. See `src/dbstore.py` for the openssl parameters.

**First Mopa deal (2026-10-19):** GOX→SHJ Feb 18–25, ₹30,335 Air Arabia non-stop, vs Google's usual ₹36,782 (range ₹31,500–50,000) and Travelpayouts' Goa typical ~₹45,100. Judged in the first run with GOX (20:15Z), confirmed by the manual collect run that verified the new layout (21:23Z), emailed, added to the review page. The same trip priced nothing from GOI on 42 runs, Oct 13–16. GOX→CMB (Oct 28–30) and GOX→IST priced nothing, so the Oct 12 CMB question is still open.

**Layout (2026-10-20):** code in `src/`, route lists in `routes/`, tests in `tests/`, one-offs in `tools/`, the laptop's launchd job in `laptop/` (reloaded at `laptop/daily.sh` and checked: watchdog ran, exit 0). Workflows call `python3 src/<script>.py`.

## Open items (curated 2026-10-20 from the old phase and stage lists)
- [ ] **Review page:** refresh every 2–3 days, in a session ("refresh the review page"): decrypt GitHub's newest snapshot into a scratch path, add deals not yet on the page to `deals`, never touch `verdicts`. Automate only if Stage 1 shows the page earns its keep. Fix the footer on the next republish (it says "typical" is the Travelpayouts median; for Google deals it is Google's usual).
- [ ] **Track (Stage 1):** deals/week for `ALERT_ORIGINS`, the share rated good, the Google confirmation rate.
- [ ] **Tune on verdicts only, never on `tools/simulate.py`:** `GF_BELOW_RANGE_LOW`, `MIN_ABS_SAVING` for Google deals; `DEAL_RATIO`, `MISTAKE_Z` for Travelpayouts (now discovery and cross-check only).
- [ ] **Baseline modelling:** calendar fares are per-day minima, `/cheap` per-month minima; check whether pooling them skews baselines, split by `fare_observation.source` if so.
- [ ] **Snapshots** grow with every run; consider skipping the upload when a run changed nothing.
- [ ] **End-of-Stage-1 write-up** (the AI-quality story below), with alert precision before and after.
- [ ] Optional: a read-only digest page; a write-up comparing it with the Zomunk model.
- Closed by later work (details in `docs/history.md`): Google Flights as a source (built 2026-10-12), Google answer-rate measurement (done 2026-10-16), `QUOTES_PER_CALL` yield check (3.0 fares per call, 2026-10-12), `VERIFY_SUPPRESS_GONE` (replaced by `VERIFY_REQUIRE_CONFIRMED`).

## Target dates (re-agreed 2026-10-19)
- **Usable: met 2026-10-17** (GOI→DXB, the first correct confirmed deal email; rated good).
- **Done (personal tool): ≈ Nov 9–16,** once ~15 deals are rated, with a known hit rate. Basis: 1 Google deal rated so far; 1 confirmed deal per ~3.5 days at 40 lookups (faster at 80 is an estimate); review page refreshed every 2–3 days.
- Levers: `GF_REVIEW_SHARE` (25% of Google lookups explore the 16 other origins, review page only, never emailed).

## Roadmap
- **Stage 1, prove the deals are good (now).** Exit: a steady flow of deals the user would genuinely consider.
- **Stage 2, the data's blind spot:** done by moving deals to Google Flights (2026-10-12); Travelpayouts is near-empty for LON, SIN, TYO and the US.
- **Stage 3 (later), traveller mode:** tag or rank deals over Indian long weekends, Diwali, Christmas, school holidays (a free holiday calendar). Learn preferences from verdicts. Only once deals are trustworthy.

### AI-quality role focus (revised 2026-10-13)
The **lead story** for an AI-quality / evals role, for "turn a vague complaint into something measurable, then move the number". "The deals feel wrong" became: the Travelpayouts-vs-Google reliability study, the Russian-market seller bias, Google's incomplete-page failure, the cross-source consistency check, and human verdicts tracking precision. It runs every day and has human labels on its output. No new build tasks: Stage 1's tracking is the evidence.
- [ ] At the end of Stage 1, a write-up: each failure, how it was found, the measurement, the fix, and alert precision from the verdicts before and after (sample sizes stated, intervals where n allows).

### Decision point (~2026-10-30): personal tool or product?
| | Personal tool | Product (Zomunk competitor) |
|---|---|---|
| Interface | Email + simple private page; no app | Signup, subscriptions, web dashboard, then maybe mobile |
| Data source | Scraping tolerable | Needs a licensed source |
| Quality bar | User's judgement | Bag and transit-visa checks, human review queue, reliable delivery |
| Effort | Weeks | Months, and a business |

Even for a product: a public web page + email list before any mobile app, to test demand cheaply. If the user leans one way before then, shape Stage 1 for it (e.g. a multi-reviewer review page for a product).

## Definition of done
Collecting daily · calibrated on real history · backed up · (optional) hosted digest and write-up.
