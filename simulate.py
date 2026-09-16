"""Synthetic observations, for exercising the model when there is no history.

**What this can show:** that the code runs on sparse and lopsided input, that
a thin cell produces no baseline rather than a confident wrong one, that the
horizon term is a no-op when nothing backs it, that repeated sightings of one
fare don't inflate readiness or collapse the scale estimate.

**What this cannot show:** whether DEAL_RATIO, MIN_ABS_SAVING or MISTAKE_Z
are the right numbers. This generator has a booking curve and log-normal
noise; the model estimates a booking curve and a robust log spread. Measuring
precision and recall here would only prove the estimator inverts the
generator. Real fares are minima over a 48h window, gappy, and correlated
across days in ways nothing below reproduces. Any threshold "validated" here
is a placeholder wearing a lab coat.

    python3 simulate.py              # build a scratch DB and report
    python3 simulate.py --days 60    # longer synthetic run
"""

import argparse
import json
import math
import random
import tempfile
from datetime import date, timedelta
from pathlib import Path

import baseline
import config
import db
import detect

# Route level in rupees, then how much of a discount each horizon carries.
ROUTES = [("BLR", "DXB", 26000), ("BLR", "SIN", 34000),
          ("BLR", "BKK", 22000), ("BLR", "LHR", 68000)]

# Booking-curve shape as a multiplier on the route level. Cheapest in the
# middle distance, dearest at the last minute -- the usual shape, invented
# here, which is exactly why it cannot validate an estimate of itself.
HORIZON_MULT = {"last-minute": 1.45, "near": 1.05, "mid": 0.92, "far": 1.00}
MONTH_MULT = {0: 1.00, 1: 1.08, 2: 1.22, 3: 0.95, 4: 0.90, 5: 1.02}


def _price(level, bucket, month_idx, rng, sigma=0.12):
    mu = math.log(level * HORIZON_MULT[bucket] * MONTH_MULT[month_idx])
    return round(math.exp(rng.gauss(mu, sigma)), 0)


def generate(conn, days=45, quotes_per_day=3, seed=11, inject_deals=True,
             scheduler=None, budget=None):
    """Walk `days` of collection, writing observations as the collector would.

    Includes the property that matters most: a quote persists in the feed for
    a few days, so the raw row count runs well ahead of the distinct one.

    With `scheduler`, only the cells it plans each day are polled, and each
    poll is logged to raw_response as a real call would be. Without it, every
    cell is polled every day -- which is what makes a scheduler invisible, so
    any comparison between allocation policies has to pass one in.
    """
    rng = random.Random(seed)
    today = date.today()
    months = [f"{(today.replace(day=1) + timedelta(days=31 * i)).year}-"
              f"{(today.replace(day=1) + timedelta(days=31 * i)).month:02d}"
              for i in range(config.MONTHS_AHEAD)]

    levels = {(o, d): lv for o, d, lv in ROUTES}
    for origin, destination, _ in ROUTES:
        conn.execute("INSERT OR IGNORE INTO route (origin,destination)"
                     " VALUES (?,?)", (origin, destination))
    conn.commit()

    injected = []
    rows = []
    calls = 0
    for day in range(days):
        fetched = today - timedelta(days=days - day)
        stamp = fetched.isoformat() + "T06:00:00+00:00"

        if scheduler is None:
            todays = [(o, d, m) for o, d, _ in ROUTES for m in months]
        else:
            todays, _why = scheduler(conn, budget=budget, today=fetched)

        for origin, destination, month in todays:
            if (origin, destination) not in levels or month not in months:
                continue
            calls += 1
            # A call is logged whether or not it yields anything -- the
            # scheduler reads this to know a cell was tried.
            conn.execute(
                "INSERT INTO raw_response (endpoint, params, status,"
                " fetched_at, body) VALUES (?,?,?,?,?)",
                ("/v1/prices/cheap",
                 json.dumps({"origin": origin, "destination": destination,
                             "depart_date": month}, sort_keys=True),
                 200, stamp, "{}"))

            month_idx = months.index(month)
            level = levels[(origin, destination)]
            for _ in range(quotes_per_day):
                depart = date(int(month[:4]), int(month[5:]),
                              rng.randint(1, 28))
                dtd = (depart - fetched).days
                if dtd < 1:
                    continue
                bucket = baseline.bucket_for(dtd)
                price = _price(level, bucket, month_idx, rng)
                # A real quote lingers: the same fare comes back for a few
                # days running. This is what inflates raw counts.
                for repeat in range(rng.randint(1, 4)):
                    seen = fetched + timedelta(days=repeat)
                    if seen >= today:
                        break
                    rows.append((origin, destination, depart.isoformat(),
                                 (depart + timedelta(days=8)).isoformat(),
                                 month, 0, rng.randint(0, 1), float(price),
                                 config.CURRENCY, "XX", None, None, None,
                                 None, None, 1, seen.isoformat() + "T06:00:00+00:00",
                                 "simulate"))
        # Committed per day so the scheduler sees yesterday's results when it
        # plans today, exactly as it would in production.
        cols_ = ("origin,destination,depart_date,return_date,depart_month,"
                 "trip_class,stops,price,currency,airline,flight_number,"
                 "duration,distance,found_at,expires_at,actual,fetched_at,"
                 "source")
        conn.executemany(
            f"INSERT OR IGNORE INTO fare_observation ({cols_})"
            f" VALUES ({','.join('?' * 18)})", rows)
        rows = []
        conn.commit()

    if inject_deals:
        # A handful of genuine drops, at a known depth, to confirm they come
        # out the far end. Not a recall measurement -- see the module note.
        for origin, destination, level in ROUTES[:2]:
            month = months[1]
            depart = date(int(month[:4]), int(month[5:]), 15)
            seen = today - timedelta(days=1)
            dtd = (depart - seen).days
            bucket = baseline.bucket_for(dtd)
            price = round(level * HORIZON_MULT[bucket] * MONTH_MULT[1] * 0.45)
            injected.append((origin, destination, price))
            rows.append((origin, destination, depart.isoformat(),
                         (depart + timedelta(days=8)).isoformat(), month, 0, 0,
                         float(price), config.CURRENCY, "ZZ", None, None, None,
                         None, None, 1, seen.isoformat() + "T06:00:00+00:00",
                         "simulate-injected"))

    cols = ("origin,destination,depart_date,return_date,depart_month,"
            "trip_class,stops,price,currency,airline,flight_number,duration,"
            "distance,found_at,expires_at,actual,fetched_at,source")
    conn.executemany(
        f"INSERT OR IGNORE INTO fare_observation ({cols})"
        f" VALUES ({','.join('?' * 18)})", rows)
    conn.commit()
    total = conn.execute("SELECT count(*) FROM fare_observation").fetchone()[0]
    return {"rows_written": total, "calls": calls,
            "injected_deals": injected}


def report(days=45, seed=11):
    with tempfile.TemporaryDirectory() as tmp:
        conn = db.connect(str(Path(tmp) / "sim.db"))
        gen = generate(conn, days=days, seed=seed)
        print(f"generated {gen['rows_written']:,} rows over {days} days")

        b = baseline.compute(conn)
        print("\nbaseline")
        for k, v in b.items():
            print(f"  {k:24} {v}")
        raw = conn.execute("SELECT count(*) FROM fare_observation").fetchone()[0]
        print(f"  {'repetition factor':24} "
              f"{raw / max(b['distinct_quotes'], 1):.2f}x rows per distinct fare")

        print("\nhorizon offsets (log units; negative = cheaper than the "
              "route's own level)")
        for r in conn.execute(
                "SELECT bucket, avg(offset_log) o, sum(n) n FROM bucket_offset"
                " GROUP BY bucket ORDER BY o"):
            print(f"  {r['bucket']:12} {r['o']:+.3f}   n={r['n']}")

        d = detect.run(conn)
        print("\ndetect")
        for k, v in d.items():
            print(f"  {k:24} {v}")
        for row in conn.execute(
                "SELECT origin,destination,price,baseline_p50,discount_pct,"
                "dtd,dtd_bucket,outlier_z,kind FROM deal"
                " ORDER BY outlier_z DESC LIMIT 8"):
            print(f"  {row['origin']}->{row['destination']} "
                  f"₹{row['price']:>8,.0f} vs ₹{row['baseline_p50']:>8,.0f}  "
                  f"{row['discount_pct']:>5.1f}%  z={row['outlier_z']:>5.2f}  "
                  f"{row['dtd']:>3}d {row['dtd_bucket']:<12} {row['kind']}")
        print("\n  injected: " + ", ".join(
            f"{o}->{d_} ₹{p:,.0f}" for o, d_, p in gen["injected_deals"]))
        print("\n  Thresholds are NOT validated by this run. See the module "
              "docstring for why.")


def round_robin(budget):
    """The obvious policy: walk every cell in turn, spreading calls evenly.

    The one thing to beat. It is not a straw man -- it is what collect.py
    does by default and what anyone would write first.
    """
    state = {"i": 0}

    def _plan(conn, budget=None, today=None):
        import schedule as _s
        cells = _s._cells(conn)
        if not cells:
            return [], {}
        out = []
        for _ in range(min(budget or 0, len(cells))):
            out.append(cells[state["i"] % len(cells)])
            state["i"] += 1
        return out, {}
    return _plan


def compare(days=60, budget=6, seed=11):
    """Under a budget too small for uniform coverage, which policy gets more
    cells ACROSS MIN_OBSERVATIONS -- not which collects more quotes.

    Total quotes collected is the wrong scoreboard: both policies spend the
    same number of calls. What differs is whether those quotes are
    concentrated enough that any cell crosses the line and starts producing
    baselines. This comparison is about allocation under a threshold, so it
    does not depend on recovering the generator's parameters.
    """
    import schedule

    results = {}
    for label, sched in (("round-robin", round_robin(budget)),
                         ("cohort", schedule.plan)):
        with tempfile.TemporaryDirectory() as tmp:
            conn = db.connect(str(Path(tmp) / "c.db"))
            gen = generate(conn, days=days, seed=seed, inject_deals=False,
                           scheduler=sched, budget=budget)
            b = baseline.compute(conn)
            cov = baseline.coverage(conn)
            ready = [c for c in cov if c["n"] >= config.MIN_OBSERVATIONS]
            results[label] = {
                "calls": gen["calls"],
                "distinct_quotes": b["distinct_quotes"],
                "cells_touched": len(cov),
                "cells_matured": len(ready),
                "baselines": b["cells_written"],
            }

    print(f"{days} days, {budget} calls/day, "
          f"{len(ROUTES) * config.MONTHS_AHEAD} cells "
          f"(a uniform daily walk would need "
          f"{len(ROUTES) * config.MONTHS_AHEAD})\n")
    keys = ["calls", "distinct_quotes", "cells_touched", "cells_matured",
            "baselines"]
    print(f"  {'':22}" + "".join(f"{k:>18}" for k in keys))
    for label, r in results.items():
        print(f"  {label:22}" + "".join(f"{r[k]:>18,}" for k in keys))
    rr, co = results["round-robin"], results["cohort"]
    print(f"\n  Same budget, same quotes. What differs is how many cells "
          f"cross the line:\n"
          f"  round-robin {rr['cells_matured']}, cohort {co['cells_matured']}.")
    return results


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--seed", type=int, default=11)
    ap.add_argument("--compare", action="store_true",
                    help="cohort vs round-robin under a tight budget")
    ap.add_argument("--budget", type=int, default=6)
    args = ap.parse_args()
    if args.compare:
        compare(days=args.days, budget=args.budget, seed=args.seed)
    else:
        report(days=args.days, seed=args.seed)
