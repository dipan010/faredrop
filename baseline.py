"""Turn accumulated observations into a per-route-month price distribution.

This is the asset. Everything else in the project is replaceable; this table
only exists because we were already writing prices down.

Caveat carried from the source data: each observation is the cheapest fare
Aviasales users found in a ~48h window, so p50 here is a median-of-minima.
It is a consistent yardstick for "cheaper than usual on this route", which is
what we need. It is not the market average, and we never label it as one.
"""

import statistics
from datetime import datetime, timezone

import config
import db


def _pct(sorted_vals, q):
    """Linear-interpolated percentile. Small n, so no numpy."""
    if not sorted_vals:
        return None
    if len(sorted_vals) == 1:
        return sorted_vals[0]
    pos = q * (len(sorted_vals) - 1)
    lo = int(pos)
    hi = min(lo + 1, len(sorted_vals) - 1)
    frac = pos - lo
    return sorted_vals[lo] * (1 - frac) + sorted_vals[hi] * frac


def compute(conn, min_observations=None):
    """Recompute every route-month cell that has enough data."""
    min_n = min_observations or config.MIN_OBSERVATIONS
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Every observation counts, expired or not. `expires_at` means "this
    # particular quote is no longer bookable" -- which disqualifies it as a
    # deal (detect.py filters on it) but not as history. Filtering it here
    # would discard each observation days after we record it, so n would
    # never reach MIN_OBSERVATIONS and no baseline would ever exist.
    rows = conn.execute(
        """
        SELECT origin, destination, depart_month, trip_class, price
        FROM fare_observation
        ORDER BY origin, destination, depart_month, trip_class
        """
    ).fetchall()

    cells = {}
    for r in rows:
        key = (r["origin"], r["destination"], r["depart_month"], r["trip_class"])
        cells.setdefault(key, []).append(r["price"])

    written = skipped = 0
    for key, prices in cells.items():
        if len(prices) < min_n:
            skipped += 1
            continue
        prices.sort()
        p50 = _pct(prices, 0.50)
        # Median absolute deviation: robust to the outliers we are hunting,
        # unlike stdev which the outliers themselves inflate.
        mad = statistics.median([abs(p - p50) for p in prices]) or 0.0
        conn.execute(
            """
            INSERT INTO baseline (origin, destination, depart_month, trip_class,
                                  n, p10, p50, mad, lowest_seen, computed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (origin, destination, depart_month, trip_class)
            DO UPDATE SET n=excluded.n, p10=excluded.p10, p50=excluded.p50,
                          mad=excluded.mad, lowest_seen=excluded.lowest_seen,
                          computed_at=excluded.computed_at
            """,
            (*key, len(prices), _pct(prices, 0.10), p50, mad,
             prices[0], now),
        )
        written += 1

    conn.commit()
    return {"cells_written": written,
            "cells_below_threshold": skipped,
            "min_observations": min_n}


def coverage(conn):
    """How close each route-month is to being trustworthy. Answers the only
    question that matters in week one: is there enough history yet?"""
    return conn.execute(
        """
        SELECT origin, destination, depart_month, trip_class,
               count(*) AS n,
               min(fetched_at) AS since
        FROM fare_observation
        GROUP BY origin, destination, depart_month, trip_class
        ORDER BY n ASC
        """
    ).fetchall()


if __name__ == "__main__":
    conn = db.connect()
    result = compute(conn)
    for k, v in result.items():
        print(f"  {k:24} {v}")
    rows = coverage(conn)
    if rows:
        ready = sum(1 for r in rows if r["n"] >= config.MIN_OBSERVATIONS)
        print(f"\n  {ready}/{len(rows)} route-months have enough observations")
    else:
        print("\n  no observations yet -- run the collector first")
