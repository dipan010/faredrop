# faredrop — Status

Last reviewed: 2026-10-21 (review page refreshed; budget, dead routes and Mopa checked)

| Built | Documented | Hosted | Posted |
|---|---|---|---|
| ✅ Travelpayouts collector (history) + Google Flights deal finder (`src/gfcollect.py`) + confirm/notify/health, 193 token-free checks, CI | ✅ README, this file, `docs/history.md`, CLAUDE.md rules | ✅ GitHub Actions (`collect.yml` every 2 h, `gf.yml` hourly); encrypted history on the `data` release; laptop is watchdog only | ❌ |

## Handoff — where the project is (2026-10-19)

**What it is.** A personal fare-deal alert in the style of Zomunk, for Indian departure cities, run free on GitHub Actions. Repo: https://github.com/dipan010/faredrop (public). Email alerts go to the owner. Deals can be rated on a private review page: https://claude.ai/artifact/FKn5RLNgx8sxmbBpLoYZc4

**How it works now**
1. **History (Travelpayouts, `collect.yml`, every 2 h, idempotent per UTC day):** 302 international routes from 21 Indian origins (`routes/routes.json`, added add-only by `src/routes.py`). One `/v1/prices/calendar` call per route, plus the per-month `/v1/prices/cheap` walk for the original 23 BLR routes: 440 cells a day. Complete every day since Oct 4 (Oct 3 was lost on the laptop era). 6,737 raw responses and 145 route-month baselines as of Oct 19. Used for discovery and as a sanity check, **never as a judge of a deal**: its cheapest fares are often Russian-market seller prices (see "Finding 2026-10-12" in `docs/history.md`).
2. **Deals (Google Flights, `gfcollect.py`, `gf.yml` hourly plus a step in `collect.yml`):** watches `ALERT_ORIGINS` (BLR, MAA, COK, HYD, GOI, GOX, BOM, CCU) × 25 destinations (`routes/gf_routes.json`), any 2–21-night trip 7–180 days out. 25% of lookups explore the 14 other origins for review only (never emailed). An unfiltered search reads Google's own price insights (usual price, typical range, ~62-day history). Candidate = fare ≤ bottom of the typical range and ≥ ₹4,000 under usual. Confirmed **in a later run** with a filtered search (≤1 stop, no self-transfers): the fare must reproduce within 5%, and Google's usual must fit Travelpayouts' typical (0.6–1.6×) with the deal below it. Only then is it a deal; email goes out only for `ALERT_ORIGINS`.
3. **Google budget:** 80 requests a day (40 until 2026-10-19), 15 per run, shared with the re-check (`verify.py`, which confirms Travelpayouts deals from alert cities only). Spaced ~40 s; one retry 90 s after a refusal; a refused confirmation is owed to the next run; a page that prices nothing is recorded and skipped; discovery skips a route whose last 3 pages all priced nothing (`GF_DEAD_LOOKUPS`), then probes it with one lookup after 14 days, doubling the wait with each further empty page, up to 60.
4. **Storage and safety:** history = AES-256 snapshots on the `data` prerelease (`dbstore.py`: never restores empty, never uploads a smaller DB, newest 12 plus one a day kept). Key `FAREDROP_DB_KEY` is in `~/.faredrop.env`, the repo secret, and the user's password manager. Secrets in the repo: `TRAVEL_PAYOUTS_API_KEY`, `FAREDROP_DB_KEY`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`. Alerts: `health.py` (per-day coverage, once), `watchdog.py` on the laptop (alerts if snapshots go >30 h stale).

**Results so far (2026-10-21)**
- **Refresh 2026-10-30:** two GOI→CMB deals emailed and added to the review page: Dec 9–13 ₹30,065 (IndiGo via MAA, usual ₹37,113, TP Dec ~₹40,100; Oct 28) and Feb 9–13 ₹31,329 (via HYD, usual ₹37,565, TP Feb ~₹37,400; Oct 30). Held back as near-duplicates: Dec 10–14 ₹31,235 and GOX→SHJ Feb 20–25 ₹32,202 (re-confirmed, already emailed Oct 21). Goa→Colombo is now 5 of the 9 Google deals emailed, so ratings lean on one route. **Google answers dipped:** 73/80 (Oct 27), 55/69 (80%, Oct 28), 70/76 (92%, Oct 29), 44/57 (77%, Oct 30 by 14Z). Still above the ~75% line, so budget stays 80; step back to 60 if a full day falls under 75%. Travelpayouts 440/440; all runs succeeded, CI green.
- **Refresh 2026-10-29:** no new deals since Oct 27 (the system re-judged known deals: GOX→SHJ Feb 20–25 now ₹32,188, BOM→SGN Apr 5–11 still ₹25,218; no new emails). Google answered 72/77 (Oct 26), 73/80 (Oct 27), but only 23/33 (70%) on Oct 28: watch. Travelpayouts 440/440. **CI's live smoke check failed twice (Oct 26)**: `/cheap` returned no BLR→DXB fares for 3 months (that route's cache is down to 1–3 fares a day) while collection parsed ~1,900 fares a day as usual. Fixed: smoke now tests the calendar endpoint and only warns on an empty `/cheap`.
- **Refresh 2026-10-27:** Google answered 76/80, 79/80, 74/80 (Oct 23–25), 68/73 on Oct 26; Travelpayouts 440/440; all runs succeeded. **City turns work:** since the change (Oct 23 17Z), lookups by city (excluding review): BOM 39, CCU 32, BLR 22, MAA 22, HYD 17, Goa 27 (GOX 16, GOI 11), COK 10; empty pages under 3%, so Navi Mumbai isn't needed for now. **First Mumbai deal:** BOM→SGN Apr 5–11 ₹25,218, Vietjet non-stop, vs Google's usual ₹35,948 (range ₹30,500–44,000), TP April typical ~₹31,400; emailed Oct 24, on the review page. Two near-duplicates held back (Mar 31–Apr 6, Apr 1–8). No new Goa/Colombo deals. Two Travelpayouts DEL→KTM deals (Dec, ~₹17k) detected; not an alert city, never checked on Google or emailed, left off the page as before.
- **Refresh 2026-10-23:** Google answered 75/80, 74/80, 79/80 (Oct 20–22) and 64/67 on Oct 23 by 14Z; Travelpayouts 440/440 every day; all runs succeeded; empty pages ~20%. Six GOI→CMB January deals confirmed (IndiGo via HYD, ₹31,395–32,885 vs Google's usual ~₹39k, TP ~₹37.7k). **The near-duplicate rule worked:** only Jan 16–19 ₹31,395 was emailed (11 days from the emailed Jan 5 trip); Jan 4–11, 7–12, 9–12, 16–23, 20–24 were held back. One review-page card for it, listing the held-back dates. Open question for tuning: most of January is ₹31–33k on this route, so is that a deal or January's going rate, with Google's usual lagging?
- **Google, at 80 a day since Oct 19:** answered 73/80 (Oct 19), 75/80 (Oct 20), 37/42 (Oct 21 by 08Z), so 91–94%, better than ~80% at 40. Travelpayouts 440/440 every day Oct 12–21; all `collect`/`gf` runs succeeded. The higher budget holds.
- **Dead routes (back-off):** GOI→HKT/IST/KTM/KUL/MLE/SGN/SHJ and GOX→CMB/KTM/MLE/SGN. Empty pages fell from 46% of lookups (Oct 16–19) to ~25% (Oct 20–21), mostly GOX routes being tried for the first time.
- **Mopa (GOX):** prices SHJ (15/15, Air Arabia non-stop), DXB, BKK, HKT, AUH, LON, MCT, KUL. Nothing for CMB, KTM, MLE, SGN, IST, SEL, AMS. Apart from SHJ, Mopa's fares are high (DXB from ₹87k, BKK ₹108k): long multi-airline trips.
- **Oct 12 GOI→CMB, explained:** not an airport mismatch (GOX→CMB has no flights). Google's usual for GOI→CMB is ₹51–69k only for trips in late Oct/early Nov (Diwali, Nov 8) and ₹37–39k for Nov 23 and January, while fares sit ~₹30k throughout. So Google's usual is inflated for the festival dates and Travelpayouts' ~₹31k is the real level. The cross-check keeps rejecting those (5 so far), as designed. The incomplete-page explanation for the ₹46,552 itself (user saw ₹22,410) stands.
- **Deal emails (Google):** GOI→CMB Oct 24–30 ₹46,552 (Oct 12, **wrong**, before the fix); GOI→DXB Nov 1–15 ₹33,883 (Oct 17, **good**); GOX→SHJ Feb 18–25 ₹30,335 (Oct 19, **good**); GOX→SHJ Feb 20–25 ₹30,698 (Oct 21); GOI→CMB Jan 5–12 ₹32,403, IndiGo via MAA, TP typical ~₹37,700 (Oct 21). The last two await verdicts. One more candidate is waiting for its confirmation: GOI→CMB Jan 7–12 ₹31,961.
- **Near-duplicates:** the two GOX→SHJ emails were nearly the same trip (Feb 18–25, Feb 20–25). **Fixed 2026-10-21 (user's call):** a deal is not emailed when the same route had one emailed in the last 14 days departing within 7 days, unless it is 5%+ cheaper (`NOTIFY_DUP_*`). Such deals are still recorded and go on the review page. On the production copy this holds back GOI→CMB Jan 7–12 (₹31,961 vs ₹32,403 emailed).
- Review verdicts: 3 DEL Travelpayouts deals wrong; Google deals 8 good (GOI→DXB, GOX→SHJ ×2, GOI→CMB ×4: Dec 9–13, Jan 5–12, Jan 16–19, Feb 9–13, BOM→SGN Apr), 1 wrong (pre-fix). 8 of ~15 rated toward tuning; every deal emailed since the Oct 12 fix rated good, and half are one route (GOI→CMB).
- **Prices after the email (live check 2026-10-21 ~09Z, user's report):** GOI→CMB Jan 5–12 rose ₹32,403 → ₹33,274 (+2.7%, now IndiGo via HYD; the MAA fare went) within ~8 h of the email; that is just above Google's range bottom (₹33,000), so it would no longer qualify. GOX→SHJ Feb 20–25 is ₹30,424 (a little lower). The user saw ~₹29k to SHJ on other dates: we search one date pair per lookup, so a cheaper day nearby is invisible to us. Idea, not done: link the email to Google's date grid for the route-week.

**Next actions, in order**
1. [x] GOI→DXB added to the review page and rated good; GOI→CMB rated wrong (2026-10-19).
2. [x] Budget 40 → 80 a day (user's decision, 2026-10-19), `GF_PER_RUN` 15. Watched Oct 19–21: 91–94% answered, Travelpayouts 440/440. Holds.
3. [x] Priced nothing: discovery skips dead routes (user's decision, 2026-10-19), with a back-off (one probe after 14 days, doubling to 60). Empty pages fell to ~25% (see Results).
4. [x] **Goa's Mopa airport (GOX) added 2026-10-19** (user's decision; its deals are emailed). Travelpayouts files both airports as city GOI, so its Goa fares drive discovery and the cross-check for both (`TP_CITY`). Checked Oct 21: see Results.
4b. [x] **More cities, 2026-10-23 (user's request):** BOM (Mumbai) and CCU (Kolkata) are alert cities, so their deals are emailed (200 watched routes). Discovery now has cities take turns: Oct 19–23 Goa (GOI+GOX) took 160 of 209 discovery lookups, BLR 24, MAA 15, HYD 6, COK 4. On Oct 23's data the first 8 picks cover all 7 cities. Budget stays 80/day, so each route is looked at less often. **Check at the next refresh:** lookups and candidates per city. Not done: Mumbai's second airport, Navi Mumbai (NMI), is filed under city BOM like GOX under GOI; add it the same way if BOM routes come back empty.
5. [x] **Dates agreed 2026-10-19:** usable = Oct 17 (first correct confirmed deal email); done ≈ Nov 9–16, when ~15 deals are rated. It holds only if the review page is refreshed every 2–3 days in a session and the user rates as deals arrive. Old note: Re-plan the dates: "usable" slipped from Oct 18. Deals now flow, about 1 confirmed per 2–3 days. Tuning needs ~15 rated deals, so "done" is likely early-to-mid November, not Oct 30. Agree a new date with the user.
6. After about 2 weeks of data: candidate and deal rate by `gf_quote.reason` (discovery vs exploration vs review), then move budget to what finds deals; tune `GF_BELOW_RANGE_LOW` / `MIN_ABS_SAVING` on verdicts.
7. Then the decision point (personal tool vs product) and Stage 3 (holiday-aware ranking).

**How to inspect production data:** decrypt the newest `data` asset into a scratch path, never into `data/faredrop.db`. The `gh` CLI isn't logged in; use the git keychain credential as `GH_TOKEN` (`git credential fill`), never printing it. See `src/dbstore.py` for the openssl parameters.

**Layout (2026-10-20):** code in `src/`, route lists in `routes/`, tests in `tests/`, one-offs in `tools/`, the laptop's launchd job in `laptop/` (reloaded at `laptop/daily.sh` and checked: watchdog ran, exit 0). Workflows call `python3 src/<script>.py`.

## Open items (curated 2026-10-20 from the old phase and stage lists)
- [ ] **Review page:** refresh every 2–3 days, in a session ("refresh the review page"): decrypt GitHub's newest snapshot into a scratch path, add deals not yet on the page to `deals`, never touch `verdicts`. Automate only if Stage 1 shows the page earns its keep. Fix the footer on the next republish (it says "typical" is the Travelpayouts median; for Google deals it is Google's usual).
- [ ] **Track (Stage 1):** deals/week for `ALERT_ORIGINS`, the share rated good, the Google confirmation rate.
- [ ] **Tune on verdicts only, never on `tools/simulate.py`:** `GF_BELOW_RANGE_LOW`, `MIN_ABS_SAVING` for Google deals; `DEAL_RATIO`, `MISTAKE_Z` for Travelpayouts (now discovery and cross-check only).
- [ ] **Baseline modelling:** calendar fares are per-day minima, `/cheap` per-month minima; check whether pooling them skews baselines, split by `fare_observation.source` if so. Also: ~4–5% of Travelpayouts fares have return = departure (same-day, every day since Oct 10); Google discovery ignores them (`GF_NIGHTS` ≥ 2), but check whether they skew baselines and the cross-check's typical.
- [ ] **Snapshots** grow with every run; consider skipping the upload when a run changed nothing.
- [ ] **End-of-Stage-1 write-up** (the AI-quality story below), with alert precision before and after.
- [ ] Optional: a read-only digest page; a write-up comparing it with the Zomunk model.
- [ ] **If there is ever a frontend** (user, 2026-10-21): show near-duplicate deals as one card, not several, with a note that the deal will likely go away in a few days. Emails already skip them.
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
