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

# Hold off idle sleep until this script exits. On 2026-10-02 the Mac dozed
# repeatedly mid-run and one collection took four hours. Started from in here,
# not by wrapping the job in the plist: iCloud Drive ties each file to the
# program that made it, and the job's program must stay daily.sh to keep
# replacing and pruning its own snapshots. A closed lid still sleeps.
/usr/bin/caffeinate -i -w $$ &

# Scheduled several times a day (see the plist); collect.py fetches only the
# route-months today doesn't have yet, so a run after a complete one is cheap.

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

# A run missed during sleep fires the moment the Mac wakes, usually before
# Wi-Fi is back. api.py's retries span seconds, so without this wait the
# whole day's collection fails on a laptop that is about to be online. Any
# HTTP answer counts as up; only a DNS or connection failure means wait.
NET_URL=${FAREDROP_NET_URL:-https://api.travelpayouts.com}
NET_WAIT=${FAREDROP_NET_WAIT:-300}     # seconds; then try anyway
waited=0
until /usr/bin/curl -s -o /dev/null --max-time 5 "$NET_URL"; do
  if [ "$waited" -ge "$NET_WAIT" ]; then
    echo "network still down after ${waited}s -- collecting anyway" >&2
    break
  fi
  sleep 10
  waited=$((waited + 10))
done
if [ "$waited" -gt 0 ]; then echo "waited ${waited}s for the network"; fi

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

# The GitHub Actions collector can stop without telling anyone (GitHub
# disables idle schedules silently); this notices from outside it.
"$PY" watchdog.py || echo "watchdog failed (rc=$?)" >&2
