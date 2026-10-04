# faredrop — Status

Last reviewed: 2026-10-05

| Built | Documented | Hosted | Posted |
|---|---|---|---|
| ✅ Collector → baseline → detect → verify → digest → notify → health pipeline, tests, CI | ✅ README (setup, daily flow, how a deal is decided, Actions, recovery) | ✅ GitHub Actions 4×/day since 2026-10-04 (encrypted history on the `data` release); laptop collects in parallel until 2026-10-10 | ❌ |

## Where it stands

- Self-hosted fare-drop watcher on the Travelpayouts API, at https://github.com/dipan010/faredrop (public). Everything is committed and pushed.
- README: "the price history is the product". Travelpayouts keeps only 7 days, so every day nothing collects is history lost for good.
- **Collection days so far (UTC):** Oct 1 ✅ · Oct 2 ✅ 138/138 · **Oct 3 ❌ lost** (laptop asleep with no network) · Oct 4 ✅ 138/138 (completed by hand). Each day is 138 route-months.
- **Two independent collectors**, each with its own database and never merged:
  - **GitHub Actions** (`collect.yml`): the official history. Runs 07:17/13:17/19:17/23:17 IST, restoring from and storing to AES-encrypted snapshots on the `data` prerelease (`dbstore.py`). One manual run so far, green; **no scheduled run has fired yet** (the first was due at 23:17 on Oct 4, ~30 min after the push).
  - **Laptop** (launchd, `daily.sh`): 07:15/13:15/19:15/23:15 IST, a safety net until Oct 10. Each run also runs `watchdog.py`, which alerts if GitHub's newest snapshot is >30h old.
- **Secrets:** repository secrets `TRAVEL_PAYOUTS_API_KEY`, `FAREDROP_DB_KEY`, `SMTP_HOST`, `SMTP_USER`, `SMTP_PASSWORD`, `ALERT_TO`, plus the same values in `~/.faredrop.env` (chmod 600). `FAREDROP_DB_KEY` is also in the user's password manager (confirmed 2026-10-05). It is the only way to decrypt the history.
- Routes are international only: 23 from BLR. 17 are seeded from `/v1/city-directions` (Aviasales' user base, so it includes MOW and AER); `config.EXTRA_DESTINATIONS` adds SIN, KUL, LON, PAR, FRA and AMS. The 13 domestic routes are inactive. Europe is thin in this feed. To change routes, edit `EXTRA_DESTINATIONS` and run `refdata.py destinations`; the collector walks the `route` table.
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
- [ ] Confirm the scheduled runs actually fire, and how late. The 23:17 slot on 2026-10-04 didn't run; the workflow had been pushed only ~30 min earlier.
- [ ] After 2026-10-10 (clean week), stop laptop collection and keep only `watchdog.py` on the laptop.
- [ ] **Open decision (asked 2026-10-05):** while both collect, each side sends its own emails, so a gap or a deal would be emailed twice. Proposed: make the laptop quiet (collect, back up and watch only; no `notify.py` or `health.py` emails) until it stops collecting.
- [x] ~~Move the collector to an always-on host~~: done with GitHub Actions instead (free for public repos).
- [ ] Optional read-only digest page (static, regenerated daily).
- [ ] Write-up comparing it with the Zomunk model it reproduces; link here.

## Definition of done
Collecting daily · calibrated on real history · backed up · (optional) hosted digest and write-up.
