"""Say so, loudly, when a day of collection was missed or only partly done.

A missed day can't be refetched (the API keeps 7 days), so the only useful
alarm is a prompt one. This runs at the end of every scheduled run and checks
each *finished* UTC day of the last week against what reached the database:
how many of the route-months were collected that day. A day with nothing is
lost; a day well short of the full set is a hole in it.

Each day is reported once. There are several runs a day now (catch-up slots
for a laptop that slept through the morning), so without that the same gap
would be announced at every slot. Today is never judged: a later slot may
still finish it.

It can't fire on a day nothing runs at all; nothing local can. It fires on
the next run instead, which launchd starts on wake.

Alerts go to a macOS notification, and by email too when SMTP is set up.
Neither is required; the log line is always written.

    python3 health.py              # check, alert if needed
    python3 health.py --quiet      # check and log only, no alerts
"""

import subprocess
import sys
from datetime import date, datetime, timedelta, timezone
from email.message import EmailMessage

import collect
import config
import db

LOOKBACK_DAYS = 7
# A day with fewer than this share of its route-months is reported. Not 100%:
# one cell answering with an API error is not a lost day.
PARTIAL_BELOW = 0.9


def collected_days(conn):
    """UTC dates on which the collector stored at least one response."""
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT substr(fetched_at, 1, 10) FROM raw_response"
        " WHERE endpoint = ?", (collect.ENDPOINT,))}


def expected_cells(conn):
    n = conn.execute("SELECT count(*) FROM route WHERE active=1").fetchone()[0]
    return n * config.MONTHS_AHEAD


def check(conn, today=None):
    """-> [(day, kind, message)] not yet reported. Reads only."""
    today = today or datetime.now(timezone.utc).date()
    days = collected_days(conn)
    if not days:
        found = [(today.isoformat(), "never",
                  "collection has never succeeded -- no history is being kept")]
    else:
        found = []
        expected = expected_cells(conn)
        # Only routes still watched count; a dropped route's old cells would
        # pad a short day.
        active = {(r[0], r[1]) for r in conn.execute(
            "SELECT origin, destination FROM route WHERE active=1")}
        start = max(date.fromisoformat(min(days)),
                    today - timedelta(days=LOOKBACK_DAYS))
        day = start
        while day < today:
            got = sum(1 for o, d, _ in collect.done_today(conn, day.isoformat())
                      if (o, d) in active)
            if got < PARTIAL_BELOW * expected:
                what = ("nothing collected -- that day's history is gone"
                        if got == 0 else
                        f"only {got}/{expected} route-months collected")
                found.append((day.isoformat(), "coverage", f"{day}: {what}"))
            day += timedelta(days=1)
    reported = {(r[0], r[1]) for r in
                conn.execute("SELECT day, kind FROM alert")}
    return [f for f in found if (f[0], f[1]) not in reported]


def mark(conn, problems):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany("INSERT OR IGNORE INTO alert (day, kind, sent_at)"
                     " VALUES (?,?,?)", [(d, k, now) for d, k, _ in problems])
    conn.commit()


def notify_mac(text):
    try:
        subprocess.run(["osascript", "-e",
                        f'display notification "{text}" with title "faredrop"'],
                       check=False, timeout=10, capture_output=True)
    except Exception:                       # noqa: BLE001 - best effort
        pass


def notify_mail(problems):
    import notify                           # SMTP settings and transport
    if not notify.configured():
        return
    msg = EmailMessage()
    msg["Subject"] = f"faredrop: {problems[0]}"[:120]
    msg["From"] = config.ALERT_FROM
    msg["To"] = config.ALERT_TO
    msg.set_content("\n".join(problems))
    try:
        notify.send(msg)
    except Exception as exc:                # noqa: BLE001 - never fatal
        print(f"health email failed: {exc}", file=sys.stderr)


def main():
    conn = db.connect()
    problems = check(conn)
    if not problems:
        print("health: nothing new to report")
        return
    lines = [m for _, _, m in problems]
    for m in lines:
        print(f"health: {m}", file=sys.stderr)
    if "--quiet" not in sys.argv:
        notify_mac("; ".join(lines).replace('"', "'"))
        notify_mail(lines)
        mark(conn, problems)


if __name__ == "__main__":
    main()
