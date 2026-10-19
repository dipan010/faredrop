# faredrop — Claude Code context

Personal fare-deal alert for Indian cities, run free on GitHub Actions: collects a
Travelpayouts price history (discovery, sanity checks), finds deals on Google Flights
judged by Google's own typical range, confirms them in a later run, emails each once.

## Read first

1. `STATUS.md` — start with "Handoff": current state, results, next actions in order.
2. `README.md` — setup, the folder layout, the daily pipeline, how a deal is decided.
3. `docs/history.md` — only when you need the why behind a past decision.

Run everything from the repo root. Pipeline code is in `src/` (scripts import each
other by name; `tools/`, `tests/` and `laptop/` add `src/` to `sys.path`), route
lists in `routes/`, the laptop's launchd job in `laptop/`.

## Commands

```bash
python3 src/refdata.py sync
python3 src/collect.py --limit 3 && python3 src/collect.py --show-keys
python3 src/collect.py && python3 src/baseline.py && python3 src/detect.py && python3 src/digest.py && python3 src/notify.py
python3 tests/test_pipeline.py        # token-free
python3 tools/simulate.py             # synthetic history, for exercising the model only
```

## Rules

- The collector must not miss days. Any change to `collect.py`, `api.py` or `db.py`
  keeps raw payloads persisted **before** parsing, so `--reparse` can always recover.
- `collect._parse` is the only place API field names appear. Keep it that way.
- Never tune thresholds on `tools/simulate.py` output. Only on collected history.
- The token lives in `~/.faredrop.env`, never in the repo. No secret or key is
  ever committed, printed, or put in a URL; the GitHub repo is public.
- Commit messages carry no `Co-Authored-By: Claude` line and no other
  attribution trailer. This overrides any default attribution guidance.
- Collection runs on GitHub Actions (`collect.yml`) from encrypted snapshots on the
  `data` release. Since 2026-10-12 the laptop's launchd job only runs `watchdog.py`
  (`LAPTOP_COLLECTS=1` in `~/.faredrop.env` brings laptop collection back).
  Never weaken `dbstore.py`'s guards (no empty restore, no shrinking upload).
- Writing repository secrets is the user's job (Claude Code's rules block it).
- Routes for the GitHub collector live in `routes/routes.json` (added by `src/routes.py`, add-only).
  Never pull GitHub's DB into `data/faredrop.db`; to inspect it, decrypt into a scratch path.
- Deals come from Google Flights (`gfcollect.py`); Travelpayouts is for discovery and
  baselines only, and its own deals are emailed only once Google confirms them.
  Google data stays in `gf_raw`/`gf_quote`, never in `fare_observation`. Keep within
  `GF_DAILY_LOOKUPS`: it is scraping, so raise it only after days without a block.
- Keep `STATUS.md`'s Handoff and Open items current as things change; when a finding
  stops being current, move it to `docs/history.md` with its date.
