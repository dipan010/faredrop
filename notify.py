"""Email the deals nobody has been told about yet.

A fare you hear about on Thursday, that went on Monday, is not a deal. The
collector already runs without needing to be remembered; the alert has to as
well, or the whole thing is a database you have to go and interrogate.

Two rules hold this together:

* **Only unnotified deals are sent, and the stamp goes on after a successful
  send.** Run it twice and the second run sends nothing. If the mail server
  is down, nothing is stamped and tomorrow tries again -- the failure mode is
  a late alert, never a silently dropped one.
* **A missing mailbox is not an error.** No SMTP configured means print the
  setup hint and exit 0. Collection is the irreplaceable step; a mail
  misconfiguration must never make the daily run look like it failed.

Repeat suppression lives in detect.py, not here. By the time a deal reaches
this module it is already known to be new.

    python3 notify.py --dry-run     # print the email instead of sending it
    python3 notify.py
"""

import argparse
import json
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage

import config
import db
from digest import booking_url

SUBJECT_MAX = 120


def _names():
    """Airline and airport lookups, or empty dicts if the tables aren't synced.

    data/*.json is gitignored and refdata.py sync may never have run, so this
    is decoration that must never be load-bearing.
    """
    try:
        import refdata
        return refdata.airline_index(), refdata.airport_index()
    except Exception:                       # noqa: BLE001 - cosmetic only
        return {}, {}


def rupees(x):
    return f"₹{x:,.0f}"


def pending(conn, limit=25, window_days=None):
    """Deals never emailed AND still recent enough to act on.

    The recency bound is not optional. Without it the first successful send
    after any quiet stretch -- SMTP not configured yet, a long mail outage,
    weeks of collecting before the mailbox is set up -- arrives as one email
    containing every deal ever detected, nearly all of them long gone. A
    stale unnotified deal ages out silently instead, which is correct: it was
    never bookable by the time anyone would have read it.
    """
    window_days = (config.DIGEST_WINDOW_DAYS if window_days is None
                   else window_days)
    since = (datetime.now(timezone.utc) - timedelta(days=window_days)) \
        .isoformat(timespec="seconds")
    # Off by default -- see VERIFY_SUPPRESS_GONE in config.py.
    gone = (" AND gf_status IS NOT 'gone'" if config.VERIFY_SUPPRESS_GONE
            else "")
    # Only the departure cities you fly from (config.ALERT_ORIGINS). Deals
    # elsewhere are still detected and listed by digest.py, just not sent.
    origins = sorted(config.ALERT_ORIGINS)
    marks = ",".join("?" * len(origins))
    return conn.execute(
        f"""
        SELECT * FROM deal
        WHERE notified_at IS NULL AND detected_at >= ?{gone}
          AND origin IN ({marks})
        ORDER BY (kind='mistake') DESC, outlier_z DESC, discount_pct DESC
        LIMIT ?
        """, (since, *origins, limit)).fetchall()


def _place(code, airports):
    info = airports.get(code) or {}
    name = info.get("name")
    return f"{code} ({name})" if name and name != code else code


def _line(d, airlines, airports):
    cabin = config.TRIP_CLASSES.get(d["trip_class"], "?")
    dates = d["depart_date"] or "?"
    if d["return_date"]:
        dates += f" → {d['return_date']}"
    carrier = airlines.get(d["airline"]) if "airline" in d.keys() else None
    head = (f"{_place(d['origin'], airports)} → "
            f"{_place(d['destination'], airports)}  {rupees(d['price'])}")
    body = [
        f"  expected {rupees(d['baseline_p50'])}"
        + (f" at {d['dtd']}d out" if d["dtd"] is not None else ""),
        f"  {d['discount_pct']}% below expected"
        + (f", saves {rupees(d['abs_saving'])}" if d["abs_saving"] else ""),
        f"  {cabin}   {dates}" + (f"   {carrier}" if carrier else ""),
    ]
    if d["kind"] == "mistake":
        # Ranking, not a verdict -- see detect.py on why this can't classify.
        body.append("  unusually far below normal; worth looking at first")
    for flag in json.loads(d["flags"] or "[]"):
        body.append(f"  ! {flag}")
    body.append(_recheck(d))
    body.append(f"  {booking_url(d)}")
    return head, body


def _recheck(d):
    """What verify.py found on Google Flights, in one line."""
    get = lambda k: d[k] if k in d.keys() else None
    status = get("gf_status")
    if status not in ("still", "gone"):
        return "  not re-checked on Google Flights"
    if get("gf_price") is None:             # verify.py found nothing to fit
        return (f"  ! Google Flights has no itinerary within "
                f"{config.MAX_STOPS} stop(s) -- may already be gone")
    via = get("gf_via")
    route = ("" if via is None else
             " non-stop" if via == "" else f" via {via.replace(',', ', ')}")
    found = (f"{rupees(get('gf_price'))}"
             + (f" on {get('gf_airline')}" if get("gf_airline") else "")
             + route)
    if status == "still":
        return f"  Google Flights now {found} -- still a deal"
    return f"  ! Google Flights now {found} -- may already be gone"


def compose(deals, airlines=None, airports=None):
    """Build the message. Pure -- no network, no database, no side effects."""
    airlines = airlines if airlines is not None else {}
    airports = airports if airports is not None else {}
    top = deals[0]
    subject = (f"faredrop: {top['origin']}→{top['destination']} "
               f"{rupees(top['price'])} ({top['discount_pct']:.0f}% below expected)")
    if len(deals) > 1:
        subject += f" +{len(deals) - 1} more"
    subject = subject[:SUBJECT_MAX]

    text, html = [], ["<div style=\"font-family:system-ui,sans-serif\">"]
    for d in deals:
        head, body = _line(d, airlines, airports)
        text.append(head)
        text.extend(body)
        text.append("")
        html.append(f"<p><strong>{head}</strong><br>"
                    + "<br>".join(x.strip() for x in body) + "</p>")
    text.append("Verify bag allowance, routing and transit visas before "
                "booking -- none of that is in this feed.")
    html.append("<p><em>Verify bag allowance, routing and transit visas "
                "before booking &mdash; none of that is in this feed.</em></p>"
                "</div>")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.ALERT_FROM
    msg["To"] = config.ALERT_TO
    msg.set_content("\n".join(text))
    msg.add_alternative("\n".join(html), subtype="html")
    return msg


def configured():
    return bool(config.SMTP_HOST and config.ALERT_TO and config.ALERT_FROM)


def send(msg):
    """Hand the message to the mail server. Raises on failure, by design."""
    with smtplib.SMTP(config.SMTP_HOST, config.SMTP_PORT, timeout=30) as smtp:
        smtp.starttls()
        if config.SMTP_USER:
            smtp.login(config.SMTP_USER, config.SMTP_PASSWORD)
        smtp.send_message(msg)


def run(conn, dry_run=False, sender=None, limit=25, window_days=None):
    """Send pending deals and stamp them. `sender` is injectable for tests."""
    deals = pending(conn, limit=limit, window_days=window_days)
    if not deals:
        return {"pending": 0, "sent": 0, "status": "nothing to send"}

    # An injected sender IS the transport, so the SMTP settings are moot.
    if not dry_run and sender is None and not configured():
        print("SMTP is not configured, so nothing was emailed.\n"
              "  Put these in ~/.faredrop.env (chmod 600):\n"
              "    export SMTP_HOST=smtp.gmail.com\n"
              "    export SMTP_USER=you@gmail.com\n"
              "    export SMTP_PASSWORD=your_app_specific_password\n"
              "    export ALERT_TO=you@gmail.com\n"
              "  Gmail will not accept your normal password; create an "
              "app password.", file=sys.stderr)
        return {"pending": len(deals), "sent": 0, "status": "not configured"}

    airlines, airports = _names()
    msg = compose(deals, airlines, airports)

    if dry_run:
        print(f"--- would send to {config.ALERT_TO or '(ALERT_TO unset)'} ---")
        print(f"Subject: {msg['Subject']}\n")
        print(msg.get_body(preferencelist=("plain",)).get_content())
        return {"pending": len(deals), "sent": 0, "status": "dry run"}

    try:
        (sender or send)(msg)
    except Exception as exc:                # noqa: BLE001 - any failure retries
        # Nothing is stamped, so tomorrow tries again. A late alert beats a
        # dropped one, and it beats a crash that masks the collection result.
        print(f"send failed, will retry next run: {exc}", file=sys.stderr)
        return {"pending": len(deals), "sent": 0, "status": f"failed: {exc}"}

    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    conn.executemany("UPDATE deal SET notified_at = ? WHERE id = ?",
                     [(now, d["id"]) for d in deals])
    conn.commit()
    return {"pending": len(deals), "sent": len(deals), "status": "sent"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the email instead of sending it")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    conn = db.connect()
    for k, v in run(conn, dry_run=args.dry_run, limit=args.limit).items():
        print(f"  {k:12} {v}")
