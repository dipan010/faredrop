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


def generate(conn, days=45, quotes_per_day=3, seed=11, inject_deals=True):
    """Walk `days` of collection, writing observations as the collector would.

    Includes the property that matters most: a quote persists in the feed for
    a few days, so the raw row count runs well ahead of the distinct one.
    """
    rng = random.Random(seed)
    today = date.today()
    months = [f"{(today.replace(day=1) + timedelta(days=31 * i)).year}-"
              f"{(today.replace(day=1) + timedelta(days=31 * i)).month:02d}"
              for i in range(config.MONTHS_AHEAD)]

    injected = []
    rows = []
    for origin, destination, level in ROUTES:
        conn.execute("INSERT OR IGNORE INTO route (origin,destination)"
                     " VALUES (?,?)", (origin, destination))
        for day in range(days):
            fetched = today - timedelta(days=days - day)
            for _ in range(quotes_per_day):
                month_idx = rng.randrange(len(months))
                month = months[month_idx]
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
    return {"rows_written": len(rows), "injected_deals": injected}


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


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--days", type=int, default=45)
    ap.add_argument("--seed", type=int, default=11)
    report(days=ap.parse_args().days, seed=ap.parse_args().seed)
