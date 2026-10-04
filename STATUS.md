# faredrop — Status

Last reviewed: 2026-10-02

| Built | Documented | Hosted | Posted |
|---|---|---|---|
| ✅ Collector → baseline → detect → digest → notify pipeline, tests, launchd plist | ✅ README (setup, daily flow, how a deal is decided) | ⏳ Collecting daily since 2026-10-01 (launchd); first run 102 cells, 51 fares | ❌ |

## Where it stands

- Self-hosted fare-drop watcher on the Travelpayouts API. Last commit 2026-09-22; 2026-10-01/02 work committed. Pushed to https://github.com/dipan010/faredrop (public).
- README: "the price history is the product". Travelpayouts keeps only 7 days, so every day the collector doesn't run is history lost for good.
- Routes are international only: 23 from BLR, 138 route-months a day. 17 are seeded from `/v1/city-directions` (Aviasales' user base, so it includes MOW and AER); `config.EXTRA_DESTINATIONS` adds SIN, KUL, LON, PAR, FRA and AMS (2026-10-02, collected the same day). The 13 domestic routes are inactive. Europe is thin in this feed: FRA and AMS had no fares on day one. To change routes, edit `EXTRA_DESTINATIONS` and run `refdata.py destinations`; the collector walks the `route` table.
- launchd job installed in `~/Library/LaunchAgents` and loaded (2026-10-01). A test kickstart ran `daily.sh` under launchd's real environment (`/usr/bin/python3` 3.9, which reaches the API over TLS) and exited 78 because no token is set. First real run 2026-10-01 18:48Z via launchd: 102/102 cells, 51 observations, 0 failures.
- Parser verified against live payloads. Two fixes: stops come from the offer's key, and the request no longer pins the return month (pinning it emptied most cells).

## Phases to completion

### Phase 1 — Start the clock (urgent: history accumulates only from here)
- [x] Token in `~/.faredrop.env` (chmod 600), sent as a header so it never appears in URLs or logs. `ORIGINS = ["BLR"]`.
- [x] `refdata.py sync`, `probe.py`, `refdata.py destinations`, `collect.py --limit 3`, `--show-keys`; `_parse` fixed.
- [x] `python3 test_pipeline.py` green, on both Homebrew 3.13 and launchd's `/usr/bin/python3` 3.9.
- [x] Install and load the launchd job.
- [x] A run launchd started on its own: 2026-10-02 01:51Z (07:21 IST), 138/138 cells, 56 new fares, health clean.
- [x] Catch-up slots (2026-10-04): 4 runs a day, each fetching only what today is missing; stops after 3 consecutive connection failures; `caffeinate` during runs; health reports each finished day once, with coverage.
- **2026-10-03 was lost.** The Mac woke without network at 07:21 IST, the run failed every cell, then hung suspended and blocked the Oct 4 morning run. Oct 4 was completed by hand (138/138). So the clean week restarts: the exit is met if Oct 4–10 are all complete (check on Oct 11).
- [ ] Optional but the real fix for a sleeping laptop: `sudo pmset repeat wakeorpoweron MTWRFSS 07:16:00` (user's call; needs the admin password). Not set as of 2026-10-04.
- **Exit:** collector running daily with a log entry every day for a week.

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
- **Exit:** losing the laptop doesn't lose the history.

### Phase 4 (optional) — Host and publish
- [ ] **Collector on GitHub Actions** (built 2026-10-04, pushed, not yet live). `collect.yml` runs 4×/day; the history lives as AES-encrypted snapshots on the `data` prerelease (`dbstore.py`), with guards against ever uploading an empty or shrunken DB. Skips until the `FAREDROP_DB_KEY` secret is set. To go live: `gh auth login`, add secrets (`FAREDROP_DB_KEY`, `SMTP_*`, `ALERT_TO`), `dbstore.py push --seed`, then set the key secret last. The key must also be saved in a password manager. Keep the laptop collecting until 2026-10-10, then reduce it to `watchdog.py`.
- [ ] Move the collector to an always-on host (small VM / Raspberry Pi) if the laptop sleeps through runs.
- [ ] Optional read-only digest page (static, regenerated daily).
- [ ] Write-up comparing it with the Zomunk model it reproduces; link here.

## Definition of done
Collecting daily · calibrated on real history · backed up · (optional) hosted digest and write-up.
