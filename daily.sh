#!/bin/zsh
# The daily run. Collect, re-model, detect -- in that order, because each
# step reads what the previous one wrote.
#
# Collection is the only step that cannot be caught up later: Travelpayouts
# keeps 7 days, so a day this doesn't run is a day of history that never
# existed. baseline and detect are pure recomputation over the database and
# can be re-run at any time.
set -u
cd "$(dirname "$0")"

# launchd starts with a near-empty environment, so a shell export is not
# inherited. Keep the token in this file (chmod 600) or in ~/.faredrop.env.
[ -f ~/.faredrop.env ] && source ~/.faredrop.env

PY=$(command -v python3)

if [ -z "${TRAVEL_PAYOUTS_API_KEY:-}" ]; then
  echo "$(date -u +%FT%TZ)  FATAL: TRAVEL_PAYOUTS_API_KEY not set" >&2
  echo "  put it in ~/.faredrop.env as: export TRAVEL_PAYOUTS_API_KEY=..." >&2
  "$PY" health.py  # a run that can't collect must still raise the alarm
  exit 78          # EX_CONFIG -- launchd won't thrash-retry on this
fi
echo "=== $(date -u +%FT%TZ) faredrop daily"

# Collection first and separately: if it fails we still want to know, but a
# modelling error must never stop tomorrow's collection from being attempted.
"$PY" collect.py || echo "collect failed (rc=$?) -- history may have a gap" >&2
# Snapshot straight after collecting: today's fares are the irreplaceable part.
"$PY" backup.py || echo "backup failed (rc=$?)" >&2
"$PY" baseline.py
"$PY" detect.py
# The live re-check needs a newer Python and a scraper the rest doesn't, so
# it gets its own venv. Missing or failing, alerts still go out, unchecked.
if [ -x .venv/bin/python ]; then
  .venv/bin/python verify.py || echo "verify failed (rc=$?) -- alerts go out unchecked" >&2
fi
"$PY" digest.py

# Delivery last, and never fatal: a mail misconfiguration must not make the
# run look like collection failed. notify.py exits 0 when SMTP is unset and
# stamps deals only on a successful send, so a bad day retries tomorrow.
"$PY" notify.py

# Last, so it judges what actually reached the database today.
"$PY" health.py
