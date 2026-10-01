"""Re-check pending deals against Google Flights before they are emailed.

Travelpayouts reports the cheapest fare someone found in the last 48 hours.
By the time it reaches an alert it may be gone, which is why a human checks
each candidate on Google Flights before publishing. This automates that
lookup for the same itinerary (same dates, cabin, stop limit) and records
what Google shows now.

What it decides, and what it doesn't:

* A deal whose live price still clears the detection gates (DEAL_RATIO of
  the expected price, at least MIN_ABS_SAVING off) is 'still'. One that
  doesn't is 'gone'. Same gates as detect.py -- no new threshold.
* 'gone' only annotates the alert unless VERIFY_SUPPRESS_GONE is on. The two
  sources have never been compared on a real deal, see config.py.
* Anything it can't compare like-for-like is 'skipped', and the alert says
  it was not re-checked.

The scraper is unofficial and can be blocked. So: a few lookups per run, a
pause between them, and the first failure ends the run instead of retrying.
It runs in its own venv (requirements-verify.txt); without one, daily.sh
doesn't call it and every alert goes out marked not re-checked.

    .venv/bin/python verify.py --dry-run    # look up, print, store nothing
    .venv/bin/python verify.py
"""

import argparse
import sys
import time
from datetime import datetime, timedelta, timezone

import config
import db
import notify

SEATS = {0: "economy", 1: "business", 2: "first"}


class Unavailable(Exception):
    """The scraper isn't installed. Not a failure: the re-check is optional."""


def google_flights(d):
    """Cheapest live round-trip price in INR for the deal's itinerary.

    Imported here, not at the top: the scraper lives only in the venv, and
    the rest of the pipeline (and its tests) runs without it.
    """
    try:
        from fast_flights import (FlightQuery, Passengers, create_query,
                                  get_flights)
    except ImportError as exc:
        raise Unavailable(str(exc)) from exc
    q = create_query(
        flights=[FlightQuery(date=d["depart_date"], from_airport=d["origin"],
                             to_airport=d["destination"]),
                 FlightQuery(date=d["return_date"],
                             from_airport=d["destination"],
                             to_airport=d["origin"])],
        trip="round-trip", seat=SEATS[d["trip_class"]],
        passengers=Passengers(adults=1), currency="INR", language="en",
        max_stops=config.MAX_STOPS)
    prices = [f.price for f in get_flights(q) if f.price]
    if not prices:
        # An itinerary with no flights at all is far likelier to be a page
        # we failed to parse than a route that vanished.
        raise RuntimeError("no priced results")
    return min(prices)


def still_a_deal(d, live):
    return (live <= d["baseline_p50"] * config.DEAL_RATIO
            and d["baseline_p50"] - live >= config.MIN_ABS_SAVING)


def due(conn, now):
    """Pending deals not re-checked recently, best first (notify's order)."""
    cutoff = (now - timedelta(hours=config.VERIFY_RECHECK_HOURS)) \
        .isoformat(timespec="seconds")
    return [d for d in notify.pending(conn, limit=10**6)
            if d["gf_checked_at"] is None or d["gf_checked_at"] < cutoff]


def run(conn, fetch=None, limit=None, pause=None, dry_run=False, now=None):
    """Re-check due deals. `fetch` is injectable for tests."""
    fetch = fetch or google_flights
    limit = config.VERIFY_MAX_PER_RUN if limit is None else limit
    pause = config.VERIFY_PAUSE_SECONDS if pause is None else pause
    now = now or datetime.now(timezone.utc)
    stamp = now.isoformat(timespec="seconds")
    out = {"due": 0, "checked": 0, "still": 0, "gone": 0, "skipped": 0,
           "status": "ok"}
    deals = due(conn, now)
    out["due"] = len(deals)

    def record(d, status, price=None):
        out[status] = out.get(status, 0) + 1
        if not dry_run:
            conn.execute("UPDATE deal SET gf_status=?, gf_price=?,"
                         " gf_checked_at=? WHERE id=?",
                         (status, price, stamp, d["id"]))
            conn.commit()

    looked_up = 0
    for d in deals:
        # Round-trips on known dates only: a month-level or one-way fare
        # has no single Google Flights search to compare against.
        if not (d["depart_date"] and d["return_date"]
                and d["trip_class"] in SEATS):
            record(d, "skipped")
            continue
        if looked_up >= limit:
            break
        if looked_up and pause:
            time.sleep(pause)
        looked_up += 1
        try:
            live = fetch(d)
        except Unavailable as exc:
            out["status"] = f"unavailable: {exc}"
            break
        except Exception as exc:            # noqa: BLE001 - stop, don't retry
            # Likely a block or a changed page. The rest stay unchecked and
            # go out marked so; hammering on would only make a block stick.
            record(d, "error")
            out["status"] = f"stopped: {exc}"
            break
        out["checked"] += 1
        status = "still" if still_a_deal(d, live) else "gone"
        record(d, status, float(live))
        if dry_run:
            print(f"  {d['origin']}->{d['destination']} {d['depart_date']}"
                  f"  feed {notify.rupees(d['price'])}"
                  f"  google {notify.rupees(live)}  {status}")
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true",
                    help="look up and print, store nothing")
    ap.add_argument("--limit", type=int)
    args = ap.parse_args()
    res = run(db.connect(), limit=args.limit, dry_run=args.dry_run)
    for k, v in res.items():
        print(f"  {k:8} {v}")
    if res["status"].startswith("stopped"):
        print("re-check stopped early; unchecked deals are still sent",
              file=sys.stderr)
