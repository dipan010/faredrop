"""Say so, loudly, when a day of collection was missed.

A missed day can't be refetched (the API keeps 7 days), so the only useful
alarm is a prompt one. This runs at the end of every daily run and checks two
things against what actually reached the database:

* **Today:** did collection store anything? If not, it failed -- no token,
  no network, an API change -- and today's history is at risk.
* **The gap behind it:** days between the last collected day before today
  and today that have nothing. If the laptop was off for three days, the run
  on wake reports all three, once: the next day the gap is closed.

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


def collected_days(conn):
    """UTC dates on which the collector stored at least one response."""
    return {r[0] for r in conn.execute(
        "SELECT DISTINCT substr(fetched_at, 1, 10) FROM raw_response"
        " WHERE endpoint = ?", (collect.ENDPOINT,))}


def check(conn, today=None):
    """-> list of problems, empty when healthy. Pure apart from the read."""
    today = today or datetime.now(timezone.utc).date()
    days = collected_days(conn)
    if not days:
        return ["collection has never succeeded -- no history is being kept"]
    problems = []
    if today.isoformat() not in days:
        problems.append(f"no collection today ({today}) -- check logs/daily.err")
    before = [d for d in days if d < today.isoformat()]
    if before:
        last = date.fromisoformat(max(before))
        missed = [last + timedelta(days=i)
                  for i in range(1, (today - last).days)]
        if missed:
            span = (f"{missed[0]}" if len(missed) == 1
                    else f"{missed[0]} to {missed[-1]}")
            problems.append(f"missed {len(missed)} day(s): {span} "
                            "-- that history is gone")
    return problems


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
    problems = check(db.connect())
    if not problems:
        print("health: collected today, no gaps")
        return
    for p in problems:
        print(f"health: {p}", file=sys.stderr)
    if "--quiet" not in sys.argv:
        notify_mac("; ".join(problems).replace('"', "'"))
        notify_mail(problems)


if __name__ == "__main__":
    main()
