# faredrop — Status

Last reviewed: 2026-10-06

| Built | Documented | Hosted | Posted |
|---|---|---|---|
| ✅ Collector → baseline → detect → verify → digest → notify → health pipeline, tests, CI | ✅ README (setup, daily flow, how a deal is decided, Actions, recovery) | ✅ GitHub Actions every 2 h since 2026-10-06 (4×/day from 2026-10-04) (encrypted history on the `data` release); laptop collects in parallel until 2026-10-10 | ❌ |

## Where it stands

- Self-hosted fare-drop watcher on the Travelpayouts API, at https://github.com/dipan010/faredrop (public). Everything is committed and pushed.
- README: "the price history is the product". Travelpayouts keeps only 7 days, so every day nothing collects is history lost for good.
- **Collection days so far (UTC):** Oct 1 ✅ · Oct 2 ✅ 138/138 · **Oct 3 ❌ lost** (laptop asleep with no network) · Oct 4 ✅ 138/138 (completed by hand) · Oct 5 ✅ 138/138 on both GitHub and the laptop · Oct 6 ✅ 440/440 on GitHub (wide list, day one). Each day is 138 route-months.
- **Two independent collectors**, each with its own database and never merged:
  - **GitHub Actions** (`collect.yml`): the official history. Runs every 2 hours (:47 past even UTC hours), restoring from and storing to AES-encrypted snapshots on the `data` prerelease (`dbstore.py`). Collected Oct 5 completely (138/138). Every run has been green, but GitHub's schedule is unpunctual: in the first day, 3 of 5 slots ran, 2.5–6 h late, and one never ran. So the schedule went from 4×/day to every 2 h on 2026-10-06.
  - **Laptop** (launchd, `daily.sh`): 07:15/13:15/19:15/23:15 IST, a safety net until Oct 10. Each run also runs `watchdog.py`, which alerts if GitHub's newest snapshot is >30h old.
- **Secrets:** repository secrets `TRAVEL_PAYOUTS_API_KEY`, `FAREDROP_DB_KEY`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`, plus the same values in `~/.faredrop.env` (chmod 600). `FAREDROP_DB_KEY` is also in the user's password manager (confirmed 2026-10-05). It is the only way to decrypt the history.
- **Wider collection (2026-10-06):** GitHub collects 302 routes from 21 Indian origins (`routes.json`; the laptop stays on its 23 BLR routes). Every route gets one `/v1/prices/calendar` call; the original 23 BLR routes also keep the per-month `/cheap` walk. That's ~440 calls and ~10 min per complete day. Survey: Delhi 666 cached fares, Goa 496, Mumbai 305, BLR 112. Calendar cells are expected from `CALENDAR_SINCE` = 2026-10-06.
- Routes (laptop) are international only: 23 from BLR. 17 are seeded from `/v1/city-directions` (Aviasales' user base, so it includes MOW and AER); `config.EXTRA_DESTINATIONS` adds SIN, KUL, LON, PAR, FRA and AMS. The 13 domestic routes are inactive. Europe is thin in this feed. To change routes, edit `EXTRA_DESTINATIONS` and run `refdata.py destinations`; the collector walks the `route` table.
- Parser verified against live payloads: stops come from the offer's key, and the request doesn't pin the return month.
- **Never upload the laptop's DB to the `data` release again.** It would become the newest snapshot and drop whatever GitHub collected that the laptop didn't.

## Phases to completion

### Phase 1 — Start the clock (urgent: history accumulates only from here)
- [x] Token in `~/.faredrop.env` (chmod 600), sent as a header so it never appears in URLs or logs. `ORIGINS = ["BLR"]`.
- [x] `refdata.py sync`, `probe.py`, `refdata.py destinations`, `collect.py --limit 3`, `--show-keys`; `_parse` fixed.
- [x] `python3 test_pipeline.py` green, on both Homebrew 3.13 and launchd's `/usr/bin/python3` 3.9.
- [x] Install and load the launchd job.
- [x] A run launchd started on its own: 2026-10-02 01:51Z (07:21 IST), 138/138 cells, 56 new fares, health clean.
- [x] Catch-up slots (2026-10-04): 4 runs a day, each fetching only what today is missing; stops after 3 consecutive connection failures; `caffeinate` during runs; health reports each finished day once, with coverage.
- **2026-10-03 was lost.** The Mac woke without network at 07:21 IST, the run failed every cell, then hung suspended and blocked the Oct 4 morning run. Oct 4 was completed by hand (138/138). So the clean week restarts: the exit is met if Oct 4–10 are all complete (check on Oct 11).
- [-] ~~`sudo pmset repeat wakeorpoweron …` to wake the laptop daily~~: no longer needed now that GitHub Actions collects.
- **Exit:** a complete day (≥90% of route-months) every day for a week, on the GitHub collector, with the laptop as backup. Clean week counted from Oct 4; check on Oct 11.

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
- [ ] Compare re-check prices against real deals, then decide whether to turn on `VERIFY_SUPPRESS_GONE`.
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
- [ ] Retiring laptop collection is decided on 2026-10-10 from a week of GitHub punctuality, not by default.
- [ ] **Open decision (asked 2026-10-05):** while both collect, each side sends its own emails, so a gap or a deal would be emailed twice. Proposed: make the laptop quiet (collect, back up and watch only; no `notify.py` or `health.py` emails) until it stops collecting.
- [x] ~~Move the collector to an always-on host~~: done with GitHub Actions instead (free for public repos).
- [ ] Optional read-only digest page (static, regenerated daily).
- [ ] Write-up comparing it with the Zomunk model it reproduces; link here.

## Roadmap after Oct 11 (agreed 2026-10-06)

No app yet. The value is in deal quality, which is unproven until real deals
arrive (from ~2026-10-12). Three stages, with a decision point after the first two.

### Stage 1: prove the deals are good (2026-10-12 → early Nov, ~3–4 weeks)
- [ ] A verdict on every deal: a small private review page with "good / not for me / wrong" per deal. The verdicts are the evidence for tuning.
- [ ] Tune on real data only: `DEAL_RATIO` / `MIN_ABS_SAVING` / `MISTAKE_Z`; per-day (calendar) vs per-month (/cheap) minima modelled apart if pooling skews; `VERIFY_SUPPRESS_GONE` on or off.
- [ ] Track deals/week for `ALERT_ORIGINS`, the share worth booking, and the Google Flights confirmation rate.
- **Exit:** a steady flow of deals the user would genuinely consider. If too thin, Stage 2 matters more than any app.

### Stage 2: fix the data's blind spot (can overlap Stage 1)
- Travelpayouts mirrors Aviasales' mostly Russian/CIS users: rich for MOW/CMB, near-empty for LON, SIN, TYO and the US, which are the deals Indian travellers want.
- [ ] Option: Google Flights (fast-flights) as a second collection source, limited to `ALERT_ORIGINS` × ~30 curated destinations. Reachable from GitHub (gf-probe 3/3). Trade-off: scraping against Google's terms. Tolerable for personal use, a liability if it is ever sold. **User's call.**

### Decision point (~early Nov): personal tool or product?
| | Personal tool | Product (Zomunk competitor) |
|---|---|---|
| Interface | Email + simple private page; no app | Signup, subscriptions, web dashboard, then maybe mobile |
| Data source | Scraping tolerable | Needs a licensed source |
| Quality bar | User's judgement | Bag and transit-visa checks, human review queue, reliable delivery |
| Effort | Weeks | Months, and a business |

Even for a product: a public web page + email list before any mobile app, to test demand cheaply. If the user leans one way before then, shape Stage 1 for it (e.g. a multi-reviewer review page for a product).

## Definition of done
Collecting daily · calibrated on real history · backed up · (optional) hosted digest and write-up.
