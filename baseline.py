"""What a route-month normally costs, given how far ahead you are booking.

This is the asset. Everything else in the project is replaceable; this table
only exists because we were already writing prices down.

Three things the model does, in the order they matter:

1. **Counts distinct quotes, not rows.** The feed repeats the same fare day
   after day, so thirty rows can be four fares. Counting the repeats would
   both overstate how much history we have and collapse the spread estimate
   toward zero -- which is precisely the number the outlier score divides by.
   Rows are kept verbatim (that's the audit trail); the collapse happens
   here, on read.

2. **Conditions on days-to-departure.** A fare 200 days out and one 10 days
   out are different distributions. Pooled, the median is a blend of the two
   and a fixed ratio threshold is wrong against both. Coarse buckets, not a
   fitted curve: at ~1 quote per cell per day a smooth booking curve is
   unfittable for months, while a bucket that never fills just falls back to
   the route's own level and costs nothing.

3. **Works in log space.** Fares are right-skewed and move multiplicatively.
   In logs, "20% below normal" is the same distance on a ₹15k route and a
   ₹150k one, so one threshold can serve both.

Caveat carried from the source data and never to be dropped: each observation
is the cheapest fare Aviasales users found in a ~48h window. p50 here is a
median-of-minima -- a consistent yardstick for "cheaper than usual on this
route", which is what we need. It is not the market average and we never
label it as one.

Deliberately NOT implemented yet: pooling a thin route-month toward its
route's other months (seasonality with shrinkage). The decomposition below
has the slot for it -- `_cell_level` is where it would go -- but three levels
of shrinkage cannot be checked against zero observations, so a thin cell
simply produces no baseline instead of a guessed one.
"""

import math
import statistics
from datetime import datetime, timezone

import config
import db


def bucket_for(dtd):
    """Which booking-horizon bucket a days-to-departure value falls in."""
    if dtd is None:
        return None
    for label, upper in config.DTD_BUCKETS:
        if dtd < upper:
            return label
    return config.DTD_BUCKETS[-1][0]


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


def _mad(values, centre):
    return statistics.median([abs(v - centre) for v in values]) if values else 0.0


# --- reading the history -----------------------------------------------

DISTINCT_QUOTES = """
    SELECT origin, destination, depart_month, trip_class,
           depart_date, return_date, airline, flight_number, price,
           min(fetched_at) AS first_seen,
           count(*)        AS sightings
    FROM fare_observation
    GROUP BY origin, destination, trip_class, depart_date, return_date,
             airline, flight_number, price
"""


def distinct_quotes(conn):
    """One row per distinct fare, however many days it sat in the feed.

    Days-to-departure is measured from the FIRST sighting: that is when the
    quote entered the world, and re-counting it at a shorter horizon each
    day would drag every quote toward the last-minute bucket.
    """
    out = []
    for r in conn.execute(DISTINCT_QUOTES):
        if r["price"] is None or r["price"] <= 0:
            continue
        dtd = None
        if r["depart_date"] and r["first_seen"]:
            try:
                d0 = datetime.fromisoformat(r["first_seen"][:10]).date()
                d1 = datetime.fromisoformat(r["depart_date"][:10]).date()
                dtd = (d1 - d0).days
            except ValueError:
                dtd = None
        if dtd is not None and dtd < 0:
            continue                      # departed already; not a forward price
        out.append({
            "origin": r["origin"], "destination": r["destination"],
            "depart_month": r["depart_month"], "trip_class": r["trip_class"],
            "price": float(r["price"]), "log_price": math.log(float(r["price"])),
            "dtd": dtd, "bucket": bucket_for(dtd),
            "sightings": r["sightings"],
        })
    return out


# --- the decomposition -------------------------------------------------
# log price  =  route level  +  horizon offset  +  cell offset  +  residual
#
# Estimated in one pass, not iterated to convergence. With this little data
# the extra passes would chase noise, and the levels are near-orthogonal
# anyway: horizon is within-route, the cell offset is within-route-month.

def _route_key(q):
    return (q["origin"], q["destination"], q["trip_class"])


def horizon_offsets(quotes):
    """How much each booking horizon moves the price, per route.

    A route's own offset is trusted in proportion to how much data backs it
    -- n/(n+k) of the say -- with the rest coming from the same bucket pooled
    across every route. A route with three quotes in a bucket gets mostly the
    pooled value; a well-observed one gets mostly its own. A bucket nobody
    has enough data for is zero, which makes the whole term a no-op rather
    than a guess.
    """
    by_route = {}
    for q in quotes:
        by_route.setdefault(_route_key(q), []).append(q)

    # Residual of each quote against its own route's median, so that routes
    # of wildly different price levels can be pooled at all.
    pooled = {}
    per_route = {}
    for key, qs in by_route.items():
        level = statistics.median([q["log_price"] for q in qs])
        for q in qs:
            if q["bucket"] is None:
                continue
            resid = q["log_price"] - level
            pooled.setdefault(q["bucket"], []).append(resid)
            per_route.setdefault((key, q["bucket"]), []).append(resid)

    # Shrink the pooled value toward zero by the same n/(n+k) rule, rather
    # than gating it on a minimum count. A hard gate makes the estimate jump
    # discontinuously as a bucket crosses the threshold -- in simulation the
    # last-minute offset read +0.04 at 22 quotes and +0.38 at 31, for no
    # reason but which side of the line it landed on. Continuous shrinkage
    # keeps a thin bucket conservative without the cliff.
    pooled_offset = {}
    for bucket, resids in pooled.items():
        m = len(resids)
        pooled_offset[bucket] = (m / (m + config.MIN_BUCKET_QUOTES)) * \
            statistics.median(resids)

    offsets = {}
    for (key, bucket), resids in per_route.items():
        pooled_val = pooled_offset.get(bucket, 0.0)
        n = len(resids)
        w = n / (n + config.SHRINK_K)
        own = statistics.median(resids)
        offsets[(key, bucket)] = {
            "offset": w * own + (1 - w) * pooled_val,
            "n": n,
            "pooled_from": len(pooled.get(bucket, [])),
        }
    return offsets, pooled_offset


def offset_lookup(offsets, pooled_offset, route_key, bucket):
    """The horizon adjustment to apply, with the fallbacks spelled out."""
    if bucket is None:
        return 0.0
    hit = offsets.get((route_key, bucket))
    if hit is not None:
        return hit["offset"]
    return pooled_offset.get(bucket, 0.0)


def _cell_level(adjusted_logs):
    """The route-month's own level, once horizon is taken out.

    The slot where seasonal shrinkage toward the route's other months would
    go. Today it is a plain median: with no observations there is nothing to
    check a shrinkage weight against, and a wrong one is worse than none.
    """
    return statistics.median(adjusted_logs)


# --- writing it down ---------------------------------------------------

def compute(conn, min_observations=None):
    """Recompute every route-month cell that has enough distinct quotes."""
    min_n = min_observations or config.MIN_OBSERVATIONS
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")

    # Every quote counts as history, expired or not. `expires_at` means "this
    # particular quote is no longer bookable" -- which disqualifies it as a
    # deal (detect.py filters on it) but not as evidence of what the route
    # costs. Filtering it here would discard each observation days after we
    # recorded it, so n would never reach MIN_OBSERVATIONS and no baseline
    # would ever exist.
    quotes = distinct_quotes(conn)
    offsets, pooled_offset = horizon_offsets(quotes)

    conn.execute("DELETE FROM bucket_offset")
    for (route_key, bucket), info in offsets.items():
        conn.execute(
            "INSERT INTO bucket_offset (origin, destination, trip_class,"
            " bucket, offset_log, n, pooled_from, computed_at)"
            " VALUES (?,?,?,?,?,?,?,?)",
            (*route_key, bucket, info["offset"], info["n"],
             info["pooled_from"], now),
        )

    cells = {}
    for q in quotes:
        key = (q["origin"], q["destination"], q["depart_month"], q["trip_class"])
        cells.setdefault(key, []).append(q)

    written = skipped = 0
    for key, qs in cells.items():
        if len(qs) < min_n:
            skipped += 1
            continue
        route_key = _route_key(qs[0])

        # Take the booking horizon out, so what remains is comparable.
        adjusted = [q["log_price"]
                    - offset_lookup(offsets, pooled_offset, route_key, q["bucket"])
                    for q in qs]
        p50_log = _cell_level(adjusted)
        log_scale = max(_mad(adjusted, p50_log), config.MIN_LOG_SCALE)

        prices = sorted(q["price"] for q in qs)
        p50 = _pct(prices, 0.50)
        conn.execute(
            """
            INSERT INTO baseline (origin, destination, depart_month, trip_class,
                                  n, n_raw, p10, p50, mad, p50_log, log_scale,
                                  lowest_seen, computed_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            ON CONFLICT (origin, destination, depart_month, trip_class)
            DO UPDATE SET n=excluded.n, n_raw=excluded.n_raw, p10=excluded.p10,
                          p50=excluded.p50, mad=excluded.mad,
                          p50_log=excluded.p50_log, log_scale=excluded.log_scale,
                          lowest_seen=excluded.lowest_seen,
                          computed_at=excluded.computed_at
            """,
            (*key, len(qs), sum(q["sightings"] for q in qs),
             _pct(prices, 0.10), p50, _mad(prices, p50),
             p50_log, log_scale, prices[0], now),
        )
        written += 1

    conn.commit()
    return {"distinct_quotes": len(quotes),
            "horizon_offsets": len(offsets),
            "cells_written": written,
            "cells_below_threshold": skipped,
            "min_observations": min_n}


def predict(p50_log, offset_log):
    """What this cell should cost at a given booking horizon, in rupees."""
    return math.exp(p50_log + offset_log)


def coverage(conn):
    """How close each route-month is to being trustworthy.

    Reports raw rows and distinct quotes side by side, because the gap
    between them is the whole point: a cell with 40 rows and 5 distinct
    fares is not ready, and the old count said it was.
    """
    quotes = distinct_quotes(conn)
    cells = {}
    for q in quotes:
        key = (q["origin"], q["destination"], q["depart_month"], q["trip_class"])
        c = cells.setdefault(key, {"n": 0, "n_raw": 0, "buckets": set()})
        c["n"] += 1
        c["n_raw"] += q["sightings"]
        if q["bucket"]:
            c["buckets"].add(q["bucket"])
    rows = [{"origin": k[0], "destination": k[1], "depart_month": k[2],
             "trip_class": k[3], "n": v["n"], "n_raw": v["n_raw"],
             "buckets": sorted(v["buckets"])}
            for k, v in cells.items()]
    rows.sort(key=lambda r: r["n"])
    return rows


if __name__ == "__main__":
    conn = db.connect()
    result = compute(conn)
    for k, v in result.items():
        print(f"  {k:24} {v}")
    rows = coverage(conn)
    if rows:
        ready = sum(1 for r in rows if r["n"] >= config.MIN_OBSERVATIONS)
        raw = sum(r["n_raw"] for r in rows)
        distinct = sum(r["n"] for r in rows)
        print(f"\n  {ready}/{len(rows)} route-months have enough distinct quotes")
        print(f"  {raw:,} rows collapse to {distinct:,} distinct fares")
    else:
        print("\n  no observations yet -- run the collector first")
