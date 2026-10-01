"""Walk the active routes and write down what each one costs today.

This is the only thing in the project that must run every day. Baselines,
detection and the digest are all recomputable from what this file records;
what it fails to record is gone for good, because Travelpayouts retains
only 7 days of history.

That constraint shapes three decisions here:

* The raw payload is saved and committed BEFORE anything is parsed. If the
  field mapping below is wrong, we lose a parse, not a day of data -- rerun
  the parser over `raw_response` instead of refetching what no longer exists.
* We commit per route-month, not once at the end. A 40-destination x 6-month
  walk is ~240 calls; a Ctrl-C at call 200 must not roll back the first 199.
* One bad route is logged and stepped over, never allowed to abort the walk.

    python3 collect.py                 # the daily run
    python3 collect.py --limit 5       # first 5 route-months, for a smoke test
    python3 collect.py --dry-run       # walk the plan, make no calls
    python3 collect.py --show-keys     # what did the API actually send back?
    python3 collect.py --reparse       # re-run a corrected parser over stored raw
"""

import argparse
import json
import sys
import time
from datetime import date, datetime, timezone

import api
import config
import db

# The endpoint and its parameters, in one place. /v1/prices/cheap takes a
# YYYY-MM for depart_date/return_date and answers with the cheapest fares
# found for that month, which is exactly one cell of the distribution we are
# building. It answers with round-trips by default. return_date is left out
# on purpose: setting it to the departure month only admits trips that come
# back within that month, which on 2026-10-01 emptied BLR->DXB/SIN/DPS for
# November while the same calls without it each returned a round-trip.
ENDPOINT = "/v1/prices/cheap"
PAUSE_SEC = 1.0          # api.py retries with backoff; don't make it need to


def months_ahead(n):
    """The next n calendar months as YYYY-MM, starting with the current one."""
    t = date.today()
    out = []
    y, m = t.year, t.month
    for _ in range(n):
        out.append(f"{y}-{m:02d}")
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return out


def _day(value):
    """YYYY-MM-DD out of whatever date shape the API used.

    Timestamps arrive as full ISO strings often enough that slicing here is
    what keeps depart_month groupable and the UNIQUE key able to dedup.
    """
    if not value:
        return None
    return str(value)[:10]


# --- parsing -----------------------------------------------------------
# Checked against a live response on 2026-10-01 (BLR->DXB). An offer carries
# airline, departure_at, return_at, expires_at, price, flight_number and
# durations -- no stop count: that is the key the offer is filed under ("0"
# non-stop, "1" one stop). Deliberately the ONLY place in the collector that
# names an API field.

def _parse(payload, origin, destination, fetched_at):
    """Payload -> rows ready for fare_observation. Never raises on shape."""
    data = (payload or {}).get("data")
    if not isinstance(data, dict):
        return []

    # {DEST: {"0": {...}, "1": {...}}} from a multi-destination call, or
    # {"0": {...}} when we asked for one destination. Normalise to the
    # inner per-offer dicts.
    offers = data.get(destination, data)
    if not isinstance(offers, dict):
        return []

    rows = []
    for key, offer in offers.items():
        if not isinstance(offer, dict):
            continue
        price = offer.get("price") or offer.get("value")
        if price is None:
            continue

        depart = _day(offer.get("departure_at") or offer.get("depart_date"))
        if not depart:
            continue

        rows.append({
            "origin": origin,
            "destination": destination,
            "depart_date": depart,
            "return_date": _day(offer.get("return_at")
                                or offer.get("return_date")),
            "depart_month": depart[:7],
            "trip_class": int(offer.get("trip_class") or 0),
            "stops": offer.get("number_of_changes",
                               offer.get("transfers",
                                         int(key) if str(key).isdigit()
                                         else None)),
            "price": float(price),
            "currency": config.CURRENCY,
            "airline": offer.get("airline"),
            "flight_number": str(offer.get("flight_number"))
                             if offer.get("flight_number") is not None else None,
            "duration": offer.get("duration"),
            "distance": offer.get("distance"),
            "found_at": offer.get("found_at"),
            "expires_at": offer.get("expires_at"),
            "actual": 1 if offer.get("actual") else 0,
            # OUR clock, not the API's found_at -- see the note in db.py.
            "fetched_at": fetched_at,
            "source": ENDPOINT,
        })
    return rows


COLUMNS = ("origin", "destination", "depart_date", "return_date",
           "depart_month", "trip_class", "stops", "price", "currency",
           "airline", "flight_number", "duration", "distance", "found_at",
           "expires_at", "actual", "fetched_at", "source")


def _insert(conn, rows):
    """Returns how many rows were new.

    fetched_at is part of the UNIQUE key, so the same fare seen on two
    different days is two observations -- that repetition IS the history.
    Within a single run it dedups, which is what OR IGNORE is for.
    """
    before = conn.total_changes
    conn.executemany(
        f"INSERT OR IGNORE INTO fare_observation ({','.join(COLUMNS)})"
        f" VALUES ({','.join('?' * len(COLUMNS))})",
        [tuple(r[c] for c in COLUMNS) for r in rows],
    )
    return conn.total_changes - before


def active_routes(conn):
    return conn.execute(
        "SELECT origin, destination FROM route WHERE active=1"
        " ORDER BY origin, destination"
    ).fetchall()


def run(conn, limit=None, dry_run=False, pause=PAUSE_SEC, plan=None):
    """Walk `plan`, a list of (origin, destination, month).

    The plan is passed in rather than built here so scheduling stays a
    separate decision -- see schedule.py. The walk itself is unchanged:
    per-cell commits, raw before parse, one bad cell never ends the run.
    """
    routes = active_routes(conn)
    if not routes:
        sys.exit(
            "No active routes.\n"
            "  Seed them from real demand first:\n"
            "    python3 refdata.py sync\n"
            "    python3 refdata.py destinations"
        )

    if plan is None:
        plan = [(r["origin"], r["destination"], month)
                for r in routes
                for month in months_ahead(config.MONTHS_AHEAD)]
    if limit:
        plan = plan[:limit]

    stats = {"cells_planned": len(plan), "cells_fetched": 0,
             "observations_new": 0, "failures": 0}

    for origin, destination, month in plan:
        if dry_run:
            print(f"  would fetch {origin}->{destination} {month}")
            continue
        try:
            payload, fetched_at = api.get(
                ENDPOINT,
                {"origin": origin, "destination": destination,
                 "depart_date": month},
                conn=conn,
            )
            # The raw body is now in the transaction. Commit it before the
            # parser gets a chance to throw.
            conn.commit()

            rows = _parse(payload, origin, destination, fetched_at)
            new = _insert(conn, rows)
            conn.commit()

            stats["cells_fetched"] += 1
            stats["observations_new"] += new
            print(f"  {origin}->{destination} {month}  "
                  f"{len(rows):>3} parsed, {new:>3} new")
        except Exception as exc:            # noqa: BLE001 - one route must not end the walk
            conn.commit()                   # keep whatever raw we did get
            stats["failures"] += 1
            print(f"  {origin}->{destination} {month}  FAILED  {exc}")
        time.sleep(pause)

    return stats


def reparse(conn):
    """Re-run the current _parse over every stored raw payload.

    The reason the raw body is committed before parsing: when the field
    mapping turns out to be wrong, the fix is to correct _parse and run this,
    not to refetch days the API no longer holds.

    Idempotent, and that rests on one detail -- each row is reparsed with the
    fetched_at stored ALONGSIDE it, never with now(). fetched_at is the
    observation timestamp and part of the UNIQUE key, so a fresh clock would
    both smear the history and duplicate every observation instead of
    refilling it.
    """
    rows = conn.execute(
        "SELECT params, fetched_at, body FROM raw_response"
        " WHERE endpoint = ? ORDER BY id", (ENDPOINT,)
    ).fetchall()

    stats = {"payloads": len(rows), "observations_new": 0, "unparseable": 0}
    for r in rows:
        try:
            params = json.loads(r["params"])
            payload = json.loads(r["body"])
        except json.JSONDecodeError:
            stats["unparseable"] += 1
            continue
        parsed = _parse(payload, params.get("origin"),
                        params.get("destination"), r["fetched_at"])
        stats["observations_new"] += _insert(conn, parsed)
    conn.commit()
    return stats


def show_keys(conn, n=1):
    """Print the shape of the most recent raw payloads.

    Exists so the mapping in _parse can be corrected against reality without
    anyone opening a JSON file by hand.
    """
    rows = conn.execute(
        "SELECT endpoint, params, fetched_at, body FROM raw_response"
        " ORDER BY id DESC LIMIT ?", (n,)
    ).fetchall()
    if not rows:
        print("No raw responses stored yet. Run collect.py or probe.py first.")
        return
    for r in rows:
        print(f"\n{r['endpoint']}  {r['params']}  @ {r['fetched_at']}")
        try:
            payload = json.loads(r["body"])
        except json.JSONDecodeError:
            print(f"  non-JSON body: {r['body'][:200]}")
            continue
        print(f"  top level: {sorted(payload)}"
              if isinstance(payload, dict) else f"  top level: {type(payload)}")
        data = payload.get("data") if isinstance(payload, dict) else None
        if isinstance(data, dict) and data:
            k = next(iter(data))
            print(f"  data keys: {list(data)[:8]}")
            print(f"  data[{k!r}]:")
            print("    " + json.dumps(data[k], indent=2)[:900].replace("\n", "\n    "))


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--limit", type=int, help="only this many route-months")
    ap.add_argument("--dry-run", action="store_true", help="print the plan only")
    ap.add_argument("--show-keys", action="store_true",
                    help="inspect the newest stored raw payload and exit")
    ap.add_argument("--reparse", action="store_true",
                    help="re-run the parser over stored raw payloads and exit")
    ap.add_argument("--scheduled", action="store_true",
                    help="spend a fixed daily budget where it counts"
                         " (see schedule.py) instead of walking every cell")
    ap.add_argument("--budget", type=int, default=None,
                    help="calls for this run; implies --scheduled")
    args = ap.parse_args()

    conn = db.connect()
    if args.show_keys:
        show_keys(conn)
        sys.exit(0)
    if args.reparse:
        for k, v in reparse(conn).items():
            print(f"  {k:24} {v}")
        sys.exit(0)

    started = datetime.now(timezone.utc).isoformat(timespec="seconds")
    print(f"collecting at {started}\n")

    todays_plan = None
    if args.scheduled or args.budget is not None:
        import schedule
        todays_plan, why = schedule.plan(conn, budget=args.budget)
        print(f"  plan: {why['planned']} calls "
              f"({why['mature_due']} maintenance, "
              f"{why['planned'] - why['mature_due']} building)"
              + (f", {why['starved']} cells starved" if why["starved"] else "")
              + "\n")

    for k, v in run(conn, limit=args.limit, dry_run=args.dry_run,
                    plan=todays_plan).items():
        print(f"  {k:24} {v}")
