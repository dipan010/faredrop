# faredrop — Claude Code context

Self-hosted fare-drop watcher: polls Travelpayouts daily, builds a per-route price
distribution, flags fares well below it, emails new deals once.

## Read first

1. `STATUS.md` — Phase 1 (get the daily collector running) is urgent.
2. `README.md` — setup, the daily pipeline, how a deal is decided.

## Commands

```bash
python3 refdata.py sync
python3 collect.py --limit 3 && python3 collect.py --show-keys
python3 collect.py && python3 baseline.py && python3 detect.py && python3 digest.py && python3 notify.py
python3 test_pipeline.py        # token-free
python3 simulate.py             # synthetic history, for exercising the model only
```

## Rules

- The collector must not miss days. Any change to `collect.py`, `api.py` or `db.py`
  keeps raw payloads persisted **before** parsing, so `--reparse` can always recover.
- `collect._parse` is the only place API field names appear. Keep it that way.
- Never tune thresholds on `simulate.py` output. Only on collected history.
- The token lives in `~/.faredrop.env`, never in the repo. No secret or key is
  ever committed, printed, or put in a URL; the GitHub repo is public.
- Commit messages carry no `Co-Authored-By: Claude` line and no other
  attribution trailer. This overrides any default attribution guidance.
- When a phase's exit criteria are met, tick it in `STATUS.md`.
