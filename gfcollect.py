"""Find deals on Google Flights, judged by Google's own sense of normal.

Why this exists: Travelpayouts' cheapest fares are often Russian-market
seller prices an Indian traveller can't buy (the first three "deals",
2026-10-12, were 30-115% under Google Flights). Its ordinary prices are
roughly right, so it stays useful for *where to look*; Google decides what a
fare is.

Each run, within a small daily budget of Google requests:

1. **Choose trips.** Most come from discovery: recent Travelpayouts fares on
   the watched routes (ALERT_ORIGINS x gf_routes.json) that look cheap for
   their route, any trip length in GF_NIGHTS. The rest explore: random
   departure dates and lengths, favouring routes Google has seen least, so
   routes Travelpayouts barely covers (London, Tokyo, Sydney) aren't blind.
2. **Judge.** One unfiltered lookup per trip. Only unfiltered pages carry
   Google's price insights: its usual price for that exact trip, its typical
   range, and ~62 days of price history. The page data is stored (gf_raw)
   before it is read, then parsed into gf_quote.
3. **Confirm.** If the fare is at or below the bottom of Google's typical
   range and saves MIN_ABS_SAVING against its usual price, a second lookup
   with the quality bar on (MAX_STOPS, no self-transfers) must still find a
   fare that clears both. Only then is it a deal, recorded as confirmed.

The first failed fetch or unreadable page ends the run: it is likelier a
block than bad luck, and pressing on makes a block stick.

    python3 gfcollect.py             # one run
    python3 gfcollect.py --dry-run   # show the trips it would look up
"""

import argparse
import json
import random
import sys
import time
import zlib
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config
import db
import detect
import verify

NIGHT_CHOICES = (2, 3, 4, 5, 7, 10, 14)


# --- what to watch -------------------------------------------------------

def destinations(path=None):
    path = Path(path or Path(__file__).with_name(config.GF_ROUTES_FILE))
    return json.loads(path.read_text())["destinations"]


def watched(dests=None):
    dests = dests if dests is not None else destinations()
    return [(o, d) for o in sorted(config.ALERT_ORIGINS) for d in dests]


# --- reading the page ----------------------------------------------------

def insights(payload):
    """Google's price insights from the page data, or None.

    Positions decoded 2026-10-12 against the page text on 16 pages:
    [5][1] cheapest now, [5][2] usual price, [5][4]..[5][5] typical range,
    [5][0] level (3 and 4 seen for "typical", 5 for "high"; "low" not yet
    seen, so nothing depends on it), [5][10][0] daily price history. Like
    verify.cheapest, Google's array positions live only here.
    """
    try:
        b = payload[5]
        if not b:
            return None

        def val(i):
            x = b[i]
            return x[1] if isinstance(x, list) and len(x) > 1 else None
        hist = b[10][0] if len(b) > 10 and b[10] else []
        out = {"price": val(1), "usual": val(2), "range_low": val(4),
               "range_high": val(5), "level_code": b[0],
               "history": [[int(t), int(p)] for t, p in hist]}
    except (IndexError, TypeError, ValueError):
        return None
    if not all(out[k] for k in ("price", "usual", "range_low", "range_high")):
        return None
    return out


def is_candidate(q):
    """Google's own test: at or below the bottom of its typical range, and a
    saving worth having against its usual price."""
    return (q["price"] <= q["range_low"] * config.GF_BELOW_RANGE_LOW
            and q["usual"] - q["price"] >= config.MIN_ABS_SAVING)


# --- choosing trips -------------------------------------------------------

def _recently_seen(conn, today):
    since = (today - timedelta(days=config.GF_RECHECK_DAYS)).isoformat()
    return {tuple(r) for r in conn.execute(
        "SELECT origin, destination, depart_date, return_date FROM gf_quote"
        " WHERE substr(fetched_at, 1, 10) > ?", (since,))}


def discovery(conn, routes, today, n):
    """Travelpayouts' cheapest-looking recent fares on watched routes.

    "Cheap-looking" is the fare against its own route's median in the same
    window: crude, but only used to decide where to spend a Google lookup.
    At most one trip per route per run, so one route can't eat the budget.
    """
    if n <= 0:
        return []
    lo, hi = config.GF_HORIZON_DAYS
    first = (today + timedelta(days=lo)).isoformat()
    last = (today + timedelta(days=hi)).isoformat()
    since = (today - timedelta(days=2)).isoformat()
    seen = _recently_seen(conn, today)
    wanted = set(routes)
    by_route = {}
    for r in conn.execute(
            "SELECT origin, destination, depart_date, return_date, price"
            " FROM fare_observation WHERE substr(fetched_at, 1, 10) >= ?"
            " AND return_date IS NOT NULL AND depart_date BETWEEN ? AND ?",
            (since, first, last)):
        key = (r[0], r[1])
        if key not in wanted:
            continue
        nights = (date.fromisoformat(r[3]) - date.fromisoformat(r[2])).days
        if not config.GF_NIGHTS[0] <= nights <= config.GF_NIGHTS[1]:
            continue
        by_route.setdefault(key, []).append((r[2], r[3], r[4]))
    picks = []
    for key, fares in by_route.items():
        prices = sorted(f[2] for f in fares)
        median = prices[len(prices) // 2]
        best = min((f for f in fares if (*key, f[0], f[1]) not in seen),
                   key=lambda f: f[2], default=None)
        if best:
            picks.append((best[2] / median, (*key, best[0], best[1])))
    picks.sort()
    return [p[1] for p in picks[:n]]


def exploration(conn, routes, today, n, rng):
    """Random trips, routes Google has seen least first."""
    if n <= 0:
        return []
    counts = {tuple(r[:2]): r[2] for r in conn.execute(
        "SELECT origin, destination, count(*) FROM gf_quote GROUP BY 1, 2")}
    order = sorted(routes, key=lambda r: (counts.get(r, 0), rng.random()))
    lo, hi = config.GF_HORIZON_DAYS
    nights = [x for x in NIGHT_CHOICES
              if config.GF_NIGHTS[0] <= x <= config.GF_NIGHTS[1]]
    out = []
    for o, d in order[:n]:
        dep = today + timedelta(days=rng.randint(lo, hi))
        ret = dep + timedelta(days=rng.choice(nights))
        out.append((o, d, dep.isoformat(), ret.isoformat()))
    return out


# --- the run ---------------------------------------------------------------

def page(origin, destination, depart, ret, filtered):
    """Fetch one Google Flights results page; returns its data (a list)."""
    try:
        from fast_flights import FlightQuery, Passengers, create_query
        from fast_flights.fetcher import fetch_flights_html
    except ImportError as exc:
        raise verify.Unavailable(str(exc)) from exc
    q = create_query(
        flights=[FlightQuery(date=depart, from_airport=origin,
                             to_airport=destination),
                 FlightQuery(date=ret, from_airport=destination,
                             to_airport=origin)],
        trip="round-trip", passengers=Passengers(adults=1), currency="INR",
        language="en", max_stops=config.MAX_STOPS,
        hide_separate_and_self_transfer=filtered)
    return verify.page_data(fetch_flights_html(q))


def _store_raw(conn, trip, filtered, purpose, payload, ok, now):
    body = (zlib.compress(json.dumps(payload).encode(), 9)
            if payload is not None else None)
    cur = conn.execute(
        "INSERT INTO gf_raw (origin, destination, depart_date, return_date,"
        " filtered, purpose, fetched_at, ok, body) VALUES (?,?,?,?,?,?,?,?,?)",
        (*trip, int(filtered), purpose, now, int(ok), body))
    conn.commit()                     # stored before anything reads it
    return cur.lastrowid


def _record_deal(conn, trip, quote_id, q, best, now):
    origin, dest, dep, ret = trip
    fp = detect.fingerprint(origin, dest, dep, ret, 0)
    if detect.already_seen(conn, fp, best["price"], now) is not None:
        return False
    saving = q["usual"] - best["price"]
    conn.execute(
        "INSERT OR IGNORE INTO deal (observation_id, origin, destination,"
        " depart_date, return_date, trip_class, price, baseline_p50,"
        " discount_pct, abs_saving, dtd, kind, flags, fingerprint,"
        " detected_at, gf_status, gf_price, gf_airline, gf_via,"
        " gf_checked_at, source)"
        " VALUES (?,?,?,?,?,0,?,?,?,?,?,'drop',?,?,?,'still',?,?,?,?,"
        " 'google_flights')",
        (-quote_id, origin, dest, dep, ret, best["price"], q["usual"],
         round(saving / q["usual"] * 100, 1), round(saving),
         (date.fromisoformat(dep) - date.fromisoformat(now[:10])).days,
         json.dumps(["verify bag allowance + transit visa before booking"]),
         fp, now, best["price"], best.get("airline"),
         ",".join(best.get("via") or []), now))
    conn.commit()
    return True


def run(conn, fetch=None, today=None, rng=None, pause=None, dry_run=False,
        routes=None):
    """One collection run. `fetch` and `routes` are injectable for tests."""
    fetch = fetch or page
    today = today or datetime.now(timezone.utc).date()
    rng = rng or random.Random()
    pause = 5 if pause is None else pause
    routes = routes if routes is not None else watched()
    stats = {"budget_left": 0, "looked_up": 0, "with_insights": 0,
             "candidates": 0, "deals": 0, "status": "ok"}

    left = min(config.GF_PER_RUN,
               config.GF_DAILY_LOOKUPS - verify.lookups_today(conn, today))
    stats["budget_left"] = max(left, 0)
    if left <= 0:
        stats["status"] = "daily Google budget spent"
        return stats
    # Leave room in the run for a confirming lookup per likely candidate.
    trips_n = max(1, (left * 2) // 3)
    n_explore = int(round(trips_n * config.GF_EXPLORE_SHARE))
    trips = [(t, "discovery") for t in
             discovery(conn, routes, today, trips_n - n_explore)]
    trips += [(t, "exploration") for t in
              exploration(conn, routes, today, trips_n - len(trips), rng)]
    if dry_run:
        for t, why in trips:
            print(f"  would look up {t[0]}->{t[1]} {t[2]}..{t[3]} ({why})")
        stats["status"] = "dry run"
        return stats

    used = 0

    def lookup(trip, filtered, purpose):
        nonlocal used
        if used and pause:
            time.sleep(pause)
        used += 1
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        try:
            payload = fetch(*trip, filtered)
        except verify.Unavailable:
            raise
        except Exception as exc:          # noqa: BLE001 - stop, don't retry
            _store_raw(conn, trip, filtered, purpose, None, False, now)
            raise RuntimeError(f"{trip[0]}->{trip[1]}: {exc}") from exc
        return _store_raw(conn, trip, filtered, purpose, payload, True,
                          now), payload, now

    try:
        for trip, why in trips:
            if used >= left:
                break
            raw_id, payload, now = lookup(trip, False, "judge")
            stats["looked_up"] += 1
            q = insights(payload)
            best = verify.cheapest(payload)
            nights = (date.fromisoformat(trip[3])
                      - date.fromisoformat(trip[2])).days
            cur = conn.execute(
                "INSERT INTO gf_quote (raw_id, origin, destination,"
                " depart_date, return_date, nights, fetched_at, reason, price,"
                " usual, range_low, range_high, level_code, history, airline,"
                " via) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (raw_id, *trip, nights, now, why,
                 (q or {}).get("price") or (best or {}).get("price"),
                 (q or {}).get("usual"), (q or {}).get("range_low"),
                 (q or {}).get("range_high"), (q or {}).get("level_code"),
                 json.dumps((q or {}).get("history") or []),
                 (best or {}).get("airline"),
                 ",".join((best or {}).get("via") or [])))
            conn.commit()
            if not q:
                continue
            stats["with_insights"] += 1
            if not is_candidate(q) or used >= left:
                continue
            stats["candidates"] += 1
            # Judged unfiltered (that is where the insights are); booked
            # filtered. The bookable fare must clear the same bar.
            _, filtered_payload, now = lookup(trip, True, "confirm")
            best = verify.cheapest(filtered_payload)
            if best and is_candidate({**q, "price": best["price"]}):
                stats["deals"] += _record_deal(conn, trip, cur.lastrowid, q,
                                               best, now)
    except verify.Unavailable as exc:
        stats["status"] = f"unavailable: {exc}"
    except Exception as exc:              # noqa: BLE001 - see module doc
        stats["status"] = f"stopped: {exc}"

    keep = (today - timedelta(days=config.GF_RAW_KEEP_DAYS)).isoformat()
    conn.execute("UPDATE gf_raw SET body = NULL WHERE body IS NOT NULL"
                 " AND substr(fetched_at, 1, 10) < ?", (keep,))
    conn.commit()
    return stats


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()
    res = run(db.connect(), dry_run=args.dry_run)
    for k, v in res.items():
        print(f"  {k:14} {v}")
    print(f"google: {res['looked_up']} lookups this run, status {res['status']}")
    if res["status"].startswith("stopped"):
        sys.exit(0)   # a block is reported, never fatal to the workflow
