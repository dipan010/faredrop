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

Repeat suppression of the same trip lives in detect.py. This module skips
near-duplicates: another trip on a route already emailed, departing within a
week of it, and not meaningfully cheaper (see `near_duplicates`).

    python3 src/notify.py --dry-run     # print the email instead of sending it
    python3 src/notify.py
"""

import argparse
import json
import smtplib
import sys
from datetime import datetime, timedelta, timezone
from email.message import EmailMessage
from html import escape as html_escape
from pathlib import Path

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
    # Only deals Google Flights confirmed -- see VERIFY_REQUIRE_CONFIRMED.
    gone = (" AND gf_status = 'still'" if config.VERIFY_REQUIRE_CONFIRMED
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


PLACES_FILE = Path(__file__).resolve().parents[1] / "routes" / "places.json"

# The email's look. Inline styles and tables only: that is what Gmail and
# phone mail apps render reliably (no <style> blocks, scripts or images).
INK = "#0b2545"          # deep navy: headings, button
ACCENT = "#ff6b4a"       # coral: the plane, the fare marker
PAPER = "#f6f2ea"        # warm page background
CARD = "#ffffff"
RULE = "#e8e2d6"
MUTED = "#7d7465"
GOOD_BG, GOOD = "#e5f5ea", "#137a43"
RANGE = "#cfe0f5"        # Google's typical range on the price bar
FONT = ("-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,Helvetica,"
        "Arial,sans-serif")


def _places():
    """Display names by code, from routes/places.json; {} if unreadable."""
    try:
        return json.loads(PLACES_FILE.read_text())["places"]
    except Exception:                       # noqa: BLE001 - cosmetic only
        return {}


def _get(d, k):
    return d[k] if k in d.keys() else None


def _name(code, places, airports):
    return (places.get(code) or (airports.get(code) or {}).get("name")
            or code)


def _dates(d):
    """'Wed 10 Feb → Fri 26 Feb · 16 nights', or the raw dates."""
    dep, ret = _day(d["depart_date"]), _day(d["return_date"])
    if not dep:
        return d["depart_date"] or "?"
    out = f"{dep:%a} {dep.day} {dep:%b}"
    if ret:
        n = (ret - dep).days
        out += f" → {ret:%a} {ret.day} {ret:%b} · {n} night{'s' if n != 1 else ''}"
    return out


def _flight(d, airlines):
    """'Vietjet · non-stop' / 'IndiGo · via HYD', from the Google check."""
    airline = _get(d, "gf_airline") or airlines.get(_get(d, "airline"))
    via = _get(d, "gf_via")
    stops = (None if via is None else "non-stop" if via == ""
             else "via " + via.replace(",", ", "))
    return " · ".join(x for x in (airline, stops) if x)


def _usual_label(d):
    return ("Google's usual price" if _get(d, "source") == "google_flights"
            else "typical price")


def _line(d, airlines, airports, places=None):
    """The plain-text version of one deal: (heading, body lines)."""
    places = places if places is not None else {}
    head = (f"{d['origin']} → {d['destination']}  {rupees(d['price'])}   "
            f"{_name(d['origin'], places, airports)} → "
            f"{_name(d['destination'], places, airports)}")
    body = [
        f"  {d['discount_pct']:.0f}% below usual"
        + (f", saves {rupees(d['abs_saving'])}" if d["abs_saving"] else "")
        + f" ({_usual_label(d)} {rupees(d['baseline_p50'])})",
        f"  {_dates(d)} · {config.TRIP_CLASSES.get(d['trip_class'], '?')}"
        + (f" · {_flight(d, airlines)}" if _flight(d, airlines) else ""),
    ]
    if _get(d, "range_low") and _get(d, "range_high"):
        body.append(f"  Google's typical range {rupees(d['range_low'])}"
                    f"–{rupees(d['range_high'])}")
    if d["kind"] == "mistake":
        # Ranking, not a verdict -- see detect.py on why this can't classify.
        body.append("  unusually far below normal; worth looking at first")
    body.append(_recheck(d))
    for flag in json.loads(d["flags"] or "[]"):
        body.append(f"  ! {flag}")
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


def _bar(d):
    """Where the fare sits against Google's typical range: a row of table
    cells (positioned elements don't survive mail clients)."""
    low, high, price = _get(d, "range_low"), _get(d, "range_high"), d["price"]
    if not (low and high and high > low):
        return ""
    start = min(price, low) * 0.92
    span = high - start

    def pct(a, b):
        return max(0.0, (b - a) / span * 100)

    cells = [(pct(start, price), "#ece7dc"), (2.2, ACCENT),
             (pct(price, low), "#ece7dc"), (pct(max(price, low), high), RANGE)]
    tds = "".join(
        f'<td width="{w:.1f}%" style="background:{c};height:8px;'
        f'font-size:0;line-height:0">&nbsp;</td>'
        for w, c in cells if w > 0.4)
    return (
        '<table role="presentation" width="100%" cellpadding="0" '
        'cellspacing="0" style="border-collapse:separate;border-radius:4px;'
        f'overflow:hidden;margin:14px 0 6px"><tr>{tds}</tr></table>'
        '<table role="presentation" width="100%" cellpadding="0" '
        f'cellspacing="0"><tr><td style="font:600 12px {FONT};color:{ACCENT}">'
        f'this fare {rupees(price)}</td><td align="right" style="font:12px '
        f'{FONT};color:{MUTED}">Google\'s typical {rupees(low)}–'
        f'{rupees(high)}</td></tr></table>')


def _card(d, airlines, airports, places):
    esc = html_escape
    origin = esc(_name(d["origin"], places, airports))
    dest = esc(_name(d["destination"], places, airports))
    saving = (f" · save {rupees(d['abs_saving'])}" if d["abs_saving"] else "")
    chips = [f"📅 {esc(_dates(d))}"]
    if _flight(d, airlines):
        chips.append(f"✈️ {esc(_flight(d, airlines))}")
    dtd = _get(d, "dtd")
    soon = (f'<span style="display:inline-block;background:#fff1ec;'
            f'color:{ACCENT};border-radius:999px;padding:3px 10px;'
            f'font:700 12px {FONT};margin-top:8px">⏳ departs in {dtd} days'
            f'</span>' if dtd is not None and 0 < dtd <= 21 else "")
    flags = "".join(f'<div style="margin-top:4px">⚠️ {esc(f)}</div>'
                    for f in json.loads(d["flags"] or "[]"))
    mistake = (f'<div style="margin-top:4px;color:{ACCENT}">🔥 unusually far '
               f'below normal — worth looking at first</div>'
               if d["kind"] == "mistake" else "")
    return f"""
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{CARD};border:1px solid {RULE};border-radius:16px;margin:0 0 18px">
<tr><td style="padding:22px 24px 4px">
  <div style="font:700 11px {FONT};letter-spacing:.14em;text-transform:uppercase;color:{MUTED}">{origin} &rarr; {dest}</div>
  <div style="font:800 36px/1.15 {FONT};color:{INK};margin-top:6px;letter-spacing:.02em">{esc(d['origin'])} <span style="color:{ACCENT}">&#9992;</span> {esc(d['destination'])}</div>
</td></tr>
<tr><td style="padding:10px 24px 0">
  <span style="font:800 30px {FONT};color:{INK}">{rupees(d['price'])}</span>
  <span style="font:15px {FONT};color:{MUTED};text-decoration:line-through;margin-left:8px">{rupees(d['baseline_p50'])}</span>
  <div style="margin-top:8px"><span style="display:inline-block;background:{GOOD_BG};color:{GOOD};border-radius:999px;padding:4px 12px;font:700 13px {FONT}">{d['discount_pct']:.0f}% below {esc(_usual_label(d).replace("Google's ", ""))}{saving}</span></div>
  <div style="font:12px/1.5 {FONT};color:{MUTED};margin-top:8px">Price when we checked. Fares move: the button shows today's price, which can be lower or higher.</div>
</td></tr>
<tr><td style="padding:14px 24px 0;font:14px/1.6 {FONT};color:{INK}">
  {"<br>".join(chips)}
  {f"<br>{soon}" if soon else ""}
  {_bar(d)}
</td></tr>
<tr><td style="padding:16px 24px 6px">
  <a href="{esc(booking_url(d))}" style="display:inline-block;background:{INK};color:#ffffff;text-decoration:none;border-radius:10px;padding:12px 20px;font:700 14px {FONT}">See these dates on Google Flights &rarr;</a>
</td></tr>
<tr><td style="padding:10px 24px 20px;font:12px/1.5 {FONT};color:{MUTED}">
  <div>&#10003; {esc(_recheck(d).strip())}</div>{mistake}{flags}
</td></tr>
</table>"""


def compose(deals, airlines=None, airports=None, places=None):
    """Build the message. Pure -- no network, no database, no side effects."""
    airlines = airlines if airlines is not None else {}
    airports = airports if airports is not None else {}
    places = places if places is not None else _places()
    top = deals[0]
    subject = (f"✈️ {top['origin']}→{top['destination']} "
               f"{rupees(top['price'])} · {top['discount_pct']:.0f}% below usual")
    if len(deals) > 1:
        subject += f" +{len(deals) - 1} more"
    subject = subject[:SUBJECT_MAX]

    text = []
    for d in deals:
        head, body = _line(d, airlines, airports, places)
        text.append(head)
        text.extend(body)
        text.append("")
    text.append("Prices are what Google Flights showed when we checked; fares "
                "move, so the link shows today's price (lower or higher).")
    text.append("Verify bag allowance, routing and transit visas before "
                "booking -- none of that is in this feed.")
    if config.REVIEW_URL:
        text.append(f"Rate these deals: {config.REVIEW_URL}")

    count = f"{len(deals)} deal{'s' if len(deals) != 1 else ''}"
    cities = ", ".join(sorted({_name(d["origin"], places, airports)
                               for d in deals}))
    preheader = (f"{top['origin']}→{top['destination']} {rupees(top['price'])}, "
                 f"{top['discount_pct']:.0f}% below usual")
    twice = (" Each confirmed on Google Flights in two checks, hours apart."
             if all(_get(d, "source") == "google_flights" for d in deals)
             else "")
    review = (f'<a href="{html_escape(config.REVIEW_URL)}" style="color:{INK};'
              f'font-weight:700">Rate them on your review page</a> · '
              if config.REVIEW_URL else "")
    page = f"""<!doctype html><html><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="color-scheme" content="light only"></head>
<body style="margin:0;padding:0;background:{PAPER}">
<div style="display:none;max-height:0;overflow:hidden;opacity:0">{html_escape(preheader)}</div>
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="background:{PAPER}"><tr><td align="center" style="padding:24px 12px">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:560px">
<tr><td style="padding:4px 4px 18px">
  <div style="font:800 22px {FONT};color:{INK};letter-spacing:-.01em">fare<span style="color:{ACCENT}">drop</span> <span style="font-size:20px">&#9992;</span></div>
  <div style="font:15px/1.5 {FONT};color:{MUTED};margin-top:4px">{count} below the usual price, from {html_escape(cities)}.{twice}</div>
</td></tr>
<tr><td>{"".join(_card(d, airlines, airports, places) for d in deals)}</td></tr>
<tr><td style="padding:6px 6px 24px;font:12px/1.6 {FONT};color:{MUTED}">
  {review}Round trips for 1 adult in INR, economy, at most 1 stop. Fares move fast; check bags, routing and transit visas before booking &mdash; none of that is in this feed.
</td></tr>
</table></td></tr></table></body></html>"""

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = config.ALERT_FROM
    msg["To"] = config.ALERT_TO
    msg.set_content("\n".join(text))
    msg.add_alternative(page, subtype="html")
    return msg


def _day(text):
    try:
        return datetime.strptime(text[:10], "%Y-%m-%d").date()
    except (TypeError, ValueError):
        return None


def near_duplicates(conn, deals, now=None):
    """Split pending deals into (to send, skipped). Skipped: the same route
    already emailed in the last NOTIFY_DUP_DAYS (or earlier in this batch),
    departing within NOTIFY_DUP_DEPART_DAYS, and not NOTIFY_DUP_CHEAPER
    cheaper. Skipped deals stay unstamped, so they age out with the window."""
    now = now or datetime.now(timezone.utc)
    since = (now - timedelta(days=config.NOTIFY_DUP_DAYS)) \
        .isoformat(timespec="seconds")
    sent = {}
    for r in conn.execute(
            "SELECT origin, destination, depart_date, price FROM deal"
            " WHERE notified_at IS NOT NULL AND notified_at != ''"
            " AND notified_at >= ?", (since,)):
        sent.setdefault((r[0], r[1]), []).append((_day(r[2]), r[3]))
    keep, skip = [], []
    for d in deals:
        dep = _day(d["depart_date"])
        dup = dep is not None and any(
            when is not None
            and abs((dep - when).days) <= config.NOTIFY_DUP_DEPART_DAYS
            and d["price"] > price * (1 - config.NOTIFY_DUP_CHEAPER)
            for when, price in sent.get((d["origin"], d["destination"]), []))
        (skip if dup else keep).append(d)
        if not dup:
            sent.setdefault((d["origin"], d["destination"]), []).append(
                (dep, d["price"]))
    return keep, skip


def _with_range(conn, d):
    """The deal as a dict, plus Google's typical range for a Google deal (its
    observation_id is -gf_quote.id), for the email's price bar."""
    d = dict(d)
    if d.get("source") == "google_flights" and d.get("observation_id"):
        q = conn.execute("SELECT range_low, range_high FROM gf_quote"
                         " WHERE id = ?", (-d["observation_id"],)).fetchone()
        if q:
            d["range_low"], d["range_high"] = q[0], q[1]
    return d


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
    deals, dupes = near_duplicates(
        conn, pending(conn, limit=limit, window_days=window_days))
    deals = [_with_range(conn, d) for d in deals]
    if not deals:
        return {"pending": 0, "sent": 0, "near_duplicates": len(dupes),
                "status": "nothing to send"}

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
    return {"pending": len(deals), "sent": len(deals),
            "near_duplicates": len(dupes), "status": "sent"}


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="print the email instead of sending it")
    ap.add_argument("--limit", type=int, default=25)
    args = ap.parse_args()
    conn = db.connect()
    for k, v in run(conn, dry_run=args.dry_run, limit=args.limit).items():
        print(f"  {k:12} {v}")
