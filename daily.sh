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

if [ -z "${TRAVELPAYOUTS_TOKEN:-}" ]; then
  echo "$(date -u +%FT%TZ)  FATAL: TRAVELPAYOUTS_TOKEN not set" >&2
  echo "  put it in ~/.faredrop.env as: export TRAVELPAYOUTS_TOKEN=..." >&2
  exit 78          # EX_CONFIG -- launchd won't thrash-retry on this
fi

PY=$(command -v python3)
echo "=== $(date -u +%FT%TZ) faredrop daily"

# Collection first and separately: if it fails we still want to know, but a
# modelling error must never stop tomorrow's collection from being attempted.
"$PY" collect.py || echo "collect failed (rc=$?) -- history may have a gap" >&2
"$PY" baseline.py
"$PY" detect.py
"$PY" digest.py

# Delivery last, and never fatal: a mail misconfiguration must not make the
# run look like collection failed. notify.py exits 0 when SMTP is unset and
# stamps deals only on a successful send, so a bad day retries tomorrow.
"$PY" notify.py
