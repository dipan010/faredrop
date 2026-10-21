# faredrop — History

The dated log of phases, findings and decisions, moved out of STATUS.md on 2026-10-20 verbatim (as it stood after the 2026-10-19 sessions). Checkboxes here are as they were then; the live list of open items is in STATUS.md. New findings go in STATUS's Handoff first, and move here when they stop being current.

## Phases to completion

### Phase 1 — Start the clock ✅ (exit met 2026-10-12)
- [x] Token in `~/.faredrop.env` (chmod 600), sent as a header so it never appears in URLs or logs. `ORIGINS = ["BLR"]`.
- [x] `refdata.py sync`, `probe.py`, `refdata.py destinations`, `collect.py --limit 3`, `--show-keys`; `_parse` fixed.
- [x] `python3 test_pipeline.py` green, on both Homebrew 3.13 and launchd's `/usr/bin/python3` 3.9.
- [x] Install and load the launchd job.
- [x] A run launchd started on its own: 2026-10-02 01:51Z (07:21 IST), 138/138 cells, 56 new fares, health clean.
- [x] Catch-up slots (2026-10-04): 4 runs a day, each fetching only what today is missing; stops after 3 consecutive connection failures; `caffeinate` during runs; health reports each finished day once, with coverage.
- **2026-10-03 was lost.** The Mac woke without network at 07:21 IST, the run failed every cell, then hung suspended and blocked the Oct 4 morning run. Oct 4 was completed by hand (138/138). So the clean week restarts: the exit is met if Oct 4–10 are all complete (check on Oct 11).
- [-] ~~`sudo pmset repeat wakeorpoweron …` to wake the laptop daily~~: no longer needed now that GitHub Actions collects.
- [x] **Exit met (reviewed 2026-10-12):** Oct 4–11 all complete on GitHub (138, 138, then 440/440 daily) and on the laptop, with no alerts. GitHub ran every day: 24 scheduled runs over Oct 6–11, 3–5 per day of 12 slots, 0 failures, first run of each UTC day by 06:48 UTC at the latest.

### Phase 2 — Let it accumulate, then calibrate
- [x] Data volume (2026-10-06): measured yield was 0.18 new fares per call against a 0.5 placeholder, which put first baselines about 2 months out. An endpoint survey found `/v1/prices/calendar` (all cached round-trips per route in one call), and an origin survey found ~20× more data across Indian cities. Both are now collected.
- [x] First wider run (2026-10-06 07:01 IST): 302 routes, 440/440 cells, 2,257 new fares, 0 failures, 8.5 min. It immediately built 35 baselines (DEL 19, GOI 10, BOM 6) and emailed one "deal": GOI→SVX, 2-stop, ₹46,575 vs ~₹83k, marked not re-checked.
- [x] Fixes for what that deal exposed (2026-10-06): (1) baselines need data from ≥`MIN_HISTORY_DAYS` = 7 collection days, and each recompute starts clean, because all 35 were one day's spread across departure dates; (2) fares over `MAX_STOPS` are skipped, not flagged; (3) a Google Flights page listing no flights is "gone (nothing within the stop limit)", not an error that stops every re-check. Alerts go only for `ALERT_ORIGINS` = BLR, MAA, COK, HYD, GOI. On GitHub's data: 0 baselines and 0 deals now. Wide route-months reach 7 days from about **2026-10-12**, so expect first real deal emails from then.
- [x] `gf-probe` (2026-10-06): 3/3 Google Flights lookups answered from GitHub's network. Re-checks work there, and Google Flights is viable as a second source if wanted.
- [ ] Phase 2 modelling: calendar fares are per-day minima and `/cheap` fares per-month minima. Check whether pooling them skews the baseline; split by `fare_observation.source` if it does.
- [ ] Google Flights as a second source: reachable from GitHub (gf-probe 3/3). Scaling it to a collector is the user's call (it's scraping, against Google's terms).
- [ ] Snapshots grow with every run (~440 calls/day of raw payloads). Consider skipping the upload when a run changed nothing.
- [ ] After about 4 days, compare `schedule.measured_yield()` with the `QUOTES_PER_CALL = 0.5` placeholder. The endpoint returns at most one cheapest fare per stop count per call, so if yield is far lower, reaching 12 distinct fares per route-month could take months.
- [ ] After ~4–6 weeks, check `digest.py` data-readiness per route. Note that each route-month mixes stay lengths (1–38 days seen on day one).
- [ ] Tune thresholds in `config.py` against real distributions, not `simulate.py` output.
- [x] Email delivery configured (Gmail SMTP with an app password in `~/.faredrop.env`); test email sent 2026-10-02. Missed-day alarms email now. Deal emails start once baselines exist.
- [ ] Watch the first deal emails for false positives; thresholds are still placeholders until tuned.
- [x] Google Flights re-check (`verify.py`, venv in `.venv`), built 2026-10-02. Each alert shows the live price.
- [x] Zomunk quality bar in the re-check (2026-10-02): self-transfers excluded; airline and connecting airports shown on each alert. Checked bags can't be verified with the free scraper; transit-visa rules aren't encoded (the connections are shown instead).
- [x] ~~Decide on `VERIFY_SUPPRESS_GONE`~~: replaced by `VERIFY_REQUIRE_CONFIRMED = True` (2026-10-12), after the first real deals disagreed with Google Flights.
- **Exit:** a real deal alert you'd act on.

### Phase 3 — Backup and robustness
- [x] Daily DB snapshot: `backup.py` runs in `daily.sh` after collect and keeps 14 copies in each of `BACKUP_DIRS`. It uses the SQLite backup API, so it is WAL-safe.
- [x] Off-machine copy: `BACKUP_DIRS` also writes to iCloud Drive (`faredrop-backups`), 2026-10-02. Verified from a launchd job: snapshot intact, 56 rows, integrity ok. Pruning goes by file name because launchd can write to that folder but not list it. macOS also ties each iCloud file to the program that made it, so a snapshot made by a manual run can't be replaced or pruned by the daily job: that failed the iCloud copy on 2026-10-02 (a test file was in the way). It now falls back to another name, or warns, instead of failing.
- [x] GitHub remote for code: https://github.com/dipan010/faredrop. It is **public**, so the DB, backups and any secrets must stay git-ignored (they are).
- [x] CI (`.github/workflows/check.yml`): tests on Python 3.9 plus a live `smoke.py` call using the `TRAVEL_PAYOUTS_API_KEY` repository secret; first run green on 2026-10-02.
- [x] Alert if the collector misses a day: `health.py` (macOS notification; email once SMTP is set), 2026-10-02.
- [x] History off the laptop: encrypted snapshots on GitHub (2026-10-04), key in a password manager.
- **Exit: met (2026-10-05).** Losing the laptop no longer loses the history: GitHub holds it, and the key exists outside the laptop.

### Phase 4 (optional) — Host and publish
- [x] **Collector on GitHub Actions**, live 2026-10-04: secrets set, history seeded, first manual run green (restored 439 responses, fetched 0 since the day was complete, stored 439, no secrets in the public log). `collect.yml` runs at 07:17/13:17/19:17/23:17 IST; history is AES-encrypted snapshots on the `data` prerelease (`dbstore.py`). The key is in `~/.faredrop.env` and the `FAREDROP_DB_KEY` secret, and should be in the user's password manager.
- [x] Scheduled runs fire, but late (2.5–6 h) and some are skipped (first day: 3 of 5 slots). Moved to every 2 h, 2026-10-06.
- [x] Laptop collection retired 2026-10-12 after a clean GitHub week; the laptop is now watchdog only. This also settles the duplicate-email question.
- [x] ~~Duplicate emails while both collect~~: resolved by making the laptop watchdog-only (2026-10-12).
- [x] ~~Move the collector to an always-on host~~: done with GitHub Actions instead (free for public repos).
- [ ] Optional read-only digest page (static, regenerated daily).
- [ ] Write-up comparing it with the Zomunk model it reproduces; link here.

## Target dates (agreed 2026-10-12, re-agreed 2026-10-19)
- **Re-agreed 2026-10-19: usable = Oct 17** (GOI→DXB, the first correct confirmed deal email). **Done ≈ Nov 9–16**, once ~15 deals are rated. Basis: 0 Google deals rated so far; 1 confirmed deal per ~3.5 days at 40 lookups (faster at 80 is an estimate); review page refreshed every 2–3 days in a session.
- **~2026-10-18: usable.** Deal emails for `ALERT_ORIGINS` that have passed confirmation in a later run plus the Travelpayouts cross-check. Thresholds are still placeholders.
- **~2026-10-30: done (personal tool).** Rules tuned on ~15 rated deals; a known hit rate.
- Levers in place for that: `GF_REVIEW_SHARE` (25% of Google lookups explore the 16 other origins × the 25 destinations, review page only, never emailed); Stage 1 shortened to 2 weeks.
- [x] **2026-10-15 decision (made 2026-10-16):** budget stays at 40. It was never the limit: 8–15 Google requests a day were used. Real limits: (1) **a bug.** Google's page for GOI→SHJ 2027-02-18 prices nothing, every time. That stopped each run *before* the lookup was recorded, so discovery chose the same trip again: 42 runs, Oct 13–16, ~4 days of Google effort on one trip and no new candidates. Fixed: every lookup counts as seen (read from `gf_raw`); a page that prices nothing is recorded and the run moves on; the same in the confirmation step. (2) **GitHub ran gf.yml only 2–6 times a day of 24.** Hard refusals were about a third of requests. Travelpayouts was complete every day (Oct 12–15, 440/440).
- [x] **Dates at risk** (resolved 2026-10-19 by the re-agreed dates above): no new Google candidate since Oct 12 (bug). Re-assess ~2026-10-19 with 2–3 days of working runs; expect "usable" to slip a few days past Oct 18.
- [ ] Review page footer still says "typical" is the Travelpayouts median; for Google deals it is Google's usual. Fix on the next republish.
- [ ] Review page refresh is manual, in a session ("refresh the review page"): every 2–3 days until Oct 30, so verdicts keep pace.

## Roadmap after Oct 11 (agreed 2026-10-06)

No app yet. The value is in deal quality, which is unproven until real deals
arrive (from ~2026-10-12). Three stages, with a decision point after the first two.

### Finding 2026-10-12: Travelpayouts' cheapest fares are often Russian-market prices
- All 3 first deals were fares sold by Russian sellers (Aviakassa ×2, Ural Airlines). The same trips on Google Flights cost 30–115% more, and a mainstream seller on the same feed (Trip.com, ₹32,134 for the AI flight) matched Google. In a 12-route sample, about half the fares with a named seller came from Russian-market sites (Kupi.com, Авиасейлс, Aviakassa, City.Travel, Biletix, T-Bank), and 43% named no seller. `/cheap` and the calendar don't name the seller, so these could not be filtered, and they also pull "typical" down.
- Should have been checked before Oct 6: the Russian skew was visible then but was treated as a coverage issue, not a question of whether a price is bookable.
- [x] Safe fixes (2026-10-12): every deal, from any city, is re-checked on Google Flights (alert cities first, 10 per run), and only confirmed deals (`gf_status = 'still'`) are emailed (`VERIFY_REQUIRE_CONFIRMED`). The review page marks the 3 deals "Not confirmed by Google Flights".
- [x] Reliability study (2026-10-12, 12 fares, small): Travelpayouts price ÷ Google for the same trip. Russian-market sellers: median 0.95 (0.50–1.01). International sellers: median 0.92 (0.88–1.07). Ordinary prices run 0–12% under Google from either kind of seller, but the extreme-cheap outliers (Biletix 0.50, Aviakassa 0.60, Ural 0.46) are the ones detection picks. So Travelpayouts is usable for discovery and price levels, not as a judge of a specific deal.
- [x] Option A built 2026-10-12: `gfcollect.py`. Google's free results page carries its own price insights (usual price, typical range, ~62-day history; decoded and cross-checked on 16 pages, unfiltered searches only). Deal = fare ≤ bottom of Google's typical range and ≥ `MIN_ABS_SAVING` under usual, confirmed by a filtered search (≤1 stop, no self-transfers). Watches `ALERT_ORIGINS` × 25 destinations (`gf_routes.json`), any 2–21-night trip departing 7–180 days out; discovery from Travelpayouts plus 30% random exploration. Budget 40 Google requests a day shared with the re-check (15 per run). Own tables `gf_raw` and `gf_quote`. Live rehearsal: 4/4 pages had insights; GOI→CMB came back code 2 at the bottom of its range (so 2 is probably "low"); Travelpayouts-flagged dates were often expensive on Google.
- **Google refuses some GitHub runner addresses (2026-10-12).** The first runs on GitHub got `travel.frontend.flights.ErrorResponse` pages instead of results (0/2, then 1/3 in gf-probe); the laptop's home connection gets 100%. GitHub gave 3/3 on Oct 6, so it is per-address and intermittent. Runs stop at the first refusal, and later runs get other addresses. A missed Google day costs nothing lasting, because every lookup carries Google's own 62-day history.
- 2026-10-12 evening: Google answered 3 of 9 requests from GitHub (about the first request of each run, then refused). First Google-judged candidate, in the 21:40 IST run: GOI→CMB Oct 24–30, ₹46,552 vs usual ₹67,487, below the typical range ₹48,000–97,000, level code 1 (so 1 is probably "low"; 2 was the bottom of the range). Its confirming search was refused on GitHub, so it was neither recorded nor emailed. Confirmed from the laptop: same ₹46,552, AI via BOM, passes every rule. Added to the review page by hand. Review verdicts: the 3 DEL deals all marked "wrong".
- [x] User chose GitHub only (2026-10-12; the laptop's battery takes a hit). To get more Google answers there: `gf.yml` runs hourly (new runner address each run); lookups 40 s apart with jitter; one retry 90 s after a refusal; candidates whose confirmation was refused are owed and confirmed first next run (`gf_quote.confirm`); the re-check covers only `ALERT_ORIGINS` deals (other cities' Travelpayouts deals are never confirmed or sent); snapshots pruned to the newest 12 plus one a day. Risk noted: a gf run can cancel a waiting collect run (one slot, not a day).
- **First Google deal email was wrong (2026-10-12).** GOI→CMB ₹46,552 was confirmed and emailed by the 22:39 IST gf run. The user's browser showed ₹22,410. Google had served an incomplete page (cheap Air India fares missing) with insights computed on it ("usual ₹67,487, typical ₹48k–97k"). The judging and confirming searches saw the same view and agreed. Travelpayouts' typical for the route-month was ₹30,977, which would have caught it. **Fix:** confirmation now happens only in a later run, the fare must reproduce within 5%, and Google's usual must fit Travelpayouts' typical (0.6–1.6×) with the deal below it, where Travelpayouts has ≥5 fares. The review page marks it "Not a deal".
- [ ] By ~2026-10-15: measure the share of GitHub runs Google answers (`gf_raw.ok` by day). If too low, run `gfcollect.py` from the laptop's launchd job when it is awake. That needs its own discovery input (the laptop no longer collects Travelpayouts), or exploration only.
- [ ] After ~2 weeks: candidate and deal rate by `gf_quote.reason` (discovery vs exploration), then shift the budget toward whichever finds deals; tune `GF_BELOW_RANGE_LOW` on verdicts; raise `GF_DAILY_LOOKUPS` only after days with no block.

### Stage 3 (later): traveller mode
- [ ] Holiday and festival awareness: tag or rank deals covering Indian long weekends, Diwali, Christmas and school holidays (a free holiday calendar). Occupancy has no free source; Google's 62-day price history is a partial demand proxy. Learn "mindset" from review-page verdicts rather than guessing it. Only once deals are trustworthy.

### Stage 1: prove the deals are good (2026-10-12 → ~2026-10-30, shortened to 2 weeks)
- Status 2026-10-12: 92 route-months ready (DEL 41, GOI 26, BOM 15, BLR 4, TRV 4, CCU 1, COK 1); yield 3.0 new fares per call, against 0.18 before the calendar. First real deals were detected 2026-10-12 00:09Z, all from DEL so not emailed: DEL→KTM ₹18,255 vs ~₹33k (AI non-stop, ×2 dates) and DEL→MOW ₹29,933 vs ~₹53.6k (1 stop). Only GOI, BLR and COK of `ALERT_ORIGINS` have baselines yet; MAA and HYD have none.
- [x] Review page live 2026-10-12: https://claude.ai/artifact/FKn5RLNgx8sxmbBpLoYZc4 (private to the user). Deals sit in its `deals` collection and the user's verdicts in `verdicts/<deal id>` (`verdict`: good / not_for_me / wrong, optional `note`). It shows every city, with `ALERT_ORIGINS` highlighted. Seeded with the 3 DEL deals; the old 2-stop GOI→SVX is left out because it fails current rules.
- [ ] Refreshing it is manual for now: in a session, decrypt GitHub's newest snapshot into a scratch path, build rows for deals not yet on the page, and batch-write them to `deals` (never overwrite `verdicts`). Automate it only if Stage 1 shows the page earns its keep.
- [ ] Tune on real data only: `DEAL_RATIO` / `MIN_ABS_SAVING` / `MISTAKE_Z`; per-day (calendar) vs per-month (/cheap) minima modelled apart if pooling skews; `VERIFY_SUPPRESS_GONE` on or off.
- [ ] Track deals/week for `ALERT_ORIGINS`, the share worth booking, and the Google Flights confirmation rate.
- **Exit:** a steady flow of deals the user would genuinely consider. If too thin, Stage 2 matters more than any app.

### Stage 2: fix the data's blind spot (can overlap Stage 1)
- Travelpayouts mirrors Aviasales' mostly Russian/CIS users: rich for MOW/CMB, near-empty for LON, SIN, TYO and the US, which are the deals Indian travellers want.
- [ ] Option: Google Flights (fast-flights) as a second collection source, limited to `ALERT_ORIGINS` × ~30 curated destinations. Reachable from GitHub (gf-probe 3/3). Trade-off: scraping against Google's terms. Tolerable for personal use, a liability if it is ever sold. **User's call.**

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

## Handoff notes superseded 2026-10-21

As they stood in STATUS.md on 2026-10-20.

**Results so far**
- Google since the Oct 16 fix: uses the full 40/day, ~80% answered (Oct 16–19: 30/40, 32/40, 32/40, 32/38), against ~70% at 13–15/day on Oct 14–15. The cap was spent by ~06Z each day. 119 lookups: 64 with insights, 55 priced nothing (46%).
- **The "priced nothing" pages cluster on routes:** GOI→SHJ 11/11, GOI→HKT 9/9, GOI→KTM 9/9, GOI→MLE 8/8 = 37 of the 55. GOI took 60 of 75 discovery lookups (its Travelpayouts fares look cheapest against their medians); BLR, COK and MAA discovery priced every page. Judging searches are also limited to ≤1 stop (`MAX_STOPS`), so these routes have no ≤1-stop itinerary from GOI on Google: perhaps the flights use Mopa (GOX), perhaps no 1-stop connection exists. Either way nothing emailable is lost by skipping them.
- Status check 2026-10-19: all `collect.yml` and `gf.yml` runs since Oct 12 succeeded (none cancelled); Travelpayouts 440/440 every day Oct 12–19. No new Google candidate since Oct 17 (4 in all: 2 confirmed, 2 rejected by the cross-check). One unconfirmed Travelpayouts deal, DEL→MOW Nov 10–Dec 7 ₹29,719 (Oct 17): not an alert city, so never checked on Google or emailed, and left off the review page.
- Deal emails: **GOI→DXB 1–15 Nov, ₹33,883 vs Google's usual ₹38,609** (emailed Oct 17; not yet on the review page). The **GOI→CMB ₹46,552** email on Oct 12 was **wrong**: Google served an incomplete page. That led to the later-run confirmation and the Travelpayouts cross-check. Since then, two GOI→CMB candidates were correctly rejected (Google's usual ~₹69k vs Travelpayouts' ~₹31k).
- Review verdicts (2026-10-19): the 3 DEL Travelpayouts "deals" wrong; GOI→CMB (Oct 12, before the later-run confirmation) **wrong**; GOI→DXB (confirmed, TP typical ~₹37,900 over 51 fares) **good**. Google deal emails: 2 good (GOI→DXB, GOX→SHJ), 1 wrong (GOI→CMB, before the Oct 12 fix); since the fix, 2 of 2 good (n too small to mean much). 2 of ~15 rated deals toward tuning.

**First Mopa deal (2026-10-19):** GOX→SHJ Feb 18–25, ₹30,335 Air Arabia non-stop, vs Google's usual ₹36,782 (range ₹31,500–50,000) and Travelpayouts' Goa typical ~₹45,100. Judged in the first run with GOX (20:15Z), confirmed by the manual collect run that verified the new layout (21:23Z), emailed, added to the review page; **rated good** by the user. The same trip priced nothing from GOI on 42 runs, Oct 13–16. GOX→CMB (Oct 28–30) and GOX→IST priced nothing, so the Oct 12 CMB question is still open.

2. [x] Budget 40 → 80 a day (user's decision, 2026-10-19), `GF_PER_RUN` stays 15. "Days without a block" read as no wholesale refusal; ~20% single refusals still happen daily. **Watch Oct 20–22:** answer rate (stop raising, or step back, if it falls well under ~75%; Oct 19, first day: 62 of 69 answered, the 80 cap not reached because GitHub started few runs), and Travelpayouts still 440/440 (gf runs now work later into the day and share the `collect` concurrency group).
3. [x] Priced nothing: four GOI routes (see Results). Discovery now skips dead routes (user's decision, 2026-10-19); on Oct 19's data that is GOI→HKT/KTM/MLE/SGN/SHJ. Check on Oct 22 that the empty-page share fell. Back-off added the same day (a plain 14-day window would have cost 3 lookups per dead route per 14 days): GOI→SGN gets its probe ~Nov 2, the other four wait 60 days.
4. [x] **Goa's Mopa airport (GOX) added 2026-10-19 (user's decision; its deals are emailed).** A laptop probe (3 lookups, Nov 20–27): GOI→SHJ priced nothing, GOX→SHJ ₹60,903 Air Arabia non-stop with insights, GOX→MLE nothing. Travelpayouts' reference data puts GOX in city GOI and we query by city, so its "GOI" fares cover both airports; they drive discovery and the cross-check for both (`TP_CITY`). One-time cost: up to ~75 lookups (3 per GOX route) to learn which of the 25 exist, during which GOX takes most new lookups. **Check by Oct 22:** which GOX routes price; whether a GOX deal passes the cross-check; and **compare GOX→CMB's Google usual with GOI's ₹67–69k** (same on Oct 12 and twice Oct 17). If GOX's is far lower, the Oct 12 GOI→CMB email was an airport mismatch (a Dabolim-only market judged against Travelpayouts' all-Goa ₹31k and the user's all-Goa ₹22,410), not an incomplete page: revise that finding, change no rules over it. Note: Goa takes most discovery picks (60 of 75, Oct 16–19), and GOX, unseen so far, takes them first; revisit in item 6.
