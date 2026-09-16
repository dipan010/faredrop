"""Flag fares that sit far enough below what their route-month should cost
at the horizon they were found at.

Three gates, and it is worth being clear about which one you can trust:

* **Ratio** -- below DEAL_RATIO of the predicted price. Scale-free, so it
  works the same on a ₹15k route and a ₹150k one.
* **Absolute saving** -- at least MIN_ABS_SAVING rupees below prediction.
  The only gate that doesn't depend on a calibrated scale, and the one that
  keeps a cheap route from filling the digest with noise.
* **Outlier score** -- how far into the left tail, in robust log units. This
  ranks; it does not classify. Every price in the feed is a minimum over a
  ~48h search window, and the left tail of a distribution of minima is not
  the tail the score's arithmetic assumes. Working in logs fixes the skew,
  not that. So `kind='mistake'` means "look at this one first", never "this
  is a mistake fare" -- the digest presents it that way and so should you.

The judgment lives in the quality filters and, ultimately, in you reading
the digest. You are the review queue at this scale.
"""

import json
from datetime import datetime, timezone

import baseline
import config
import db


def quality_flags(obs, airlines=None):
    """Reasons a cheap fare might still be a bad deal. Empty list == clean."""
    flags = []
    stops = obs["stops"]
    if stops is not None and stops > config.MAX_STOPS:
        flags.append(f"{stops} stops")
    if obs["airline"] and obs["airline"] in config.AIRLINE_BLOCKLIST:
        flags.append(f"blocklisted carrier {obs['airline']}")
    if obs["expires_at"]:
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        if obs["expires_at"] <= now:
            flags.append("price already expired")
    if obs["return_date"] is None:
        flags.append("one-way (baseline is round-trip)")
    # Baggage inclusion and transit-visa status are not in this feed at all.
    # Rather than guess, say so -- an unverified claim is worse than a gap.
    flags.append("verify bag allowance + transit visa before booking")
    return flags


def _days_to_departure(depart_date, fetched_at):
    if not depart_date or not fetched_at:
        return None
    try:
        d0 = datetime.fromisoformat(fetched_at[:10]).date()
        d1 = datetime.fromisoformat(depart_date[:10]).date()
    except ValueError:
        return None
    return (d1 - d0).days


def load_offsets(conn):
    """Route-level horizon offsets, plus a pooled fallback per bucket."""
    per_route, pooled = {}, {}
    for r in conn.execute("SELECT * FROM bucket_offset"):
        key = (r["origin"], r["destination"], r["trip_class"])
        per_route[(key, r["bucket"])] = r["offset_log"]
        pooled.setdefault(r["bucket"], []).append(
            (r["offset_log"], r["pooled_from"]))
    # Fall back to the widest-backed value seen for that bucket.
    pooled = {b: max(vals, key=lambda t: t[1])[0] for b, vals in pooled.items()}
    return per_route, pooled


def score(price, p50_log, log_scale, offset_log):
    """(predicted price, ratio, outlier score in robust log units)."""
    import math
    predicted = baseline.predict(p50_log, offset_log)
    ratio = price / predicted
    # 1.4826 puts the MAD on the same footing as a standard deviation would
    # be under a normal -- a convention that makes the number readable, not
    # a claim that these residuals are normal. They aren't; see the docstring.
    z = (p50_log + offset_log - math.log(price)) / (1.4826 * log_scale)
    return predicted, ratio, z


def run(conn):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    per_route, pooled = load_offsets(conn)

    rows = conn.execute(
        """
        SELECT o.*, b.p50, b.p50_log, b.log_scale, b.n AS baseline_n
        FROM fare_observation o
        JOIN baseline b
          ON  b.origin       = o.origin
          AND b.destination  = o.destination
          AND b.depart_month = o.depart_month
          AND b.trip_class   = o.trip_class
        LEFT JOIN deal d ON d.observation_id = o.id
        WHERE d.id IS NULL
          AND b.n >= ?
          AND b.p50_log IS NOT NULL
          AND (o.expires_at IS NULL OR o.expires_at > ?)
        """,
        (config.MIN_OBSERVATIONS, now),
    ).fetchall()

    found = 0
    for o in rows:
        dtd = _days_to_departure(o["depart_date"], o["fetched_at"])
        bucket = baseline.bucket_for(dtd)
        route_key = (o["origin"], o["destination"], o["trip_class"])
        offset = per_route.get((route_key, bucket), pooled.get(bucket, 0.0))

        predicted, ratio, z = score(o["price"], o["p50_log"],
                                    o["log_scale"] or config.MIN_LOG_SCALE,
                                    offset)

        # Both gates, not either. The ratio alone fires on cheap routes over
        # pocket change; the absolute saving alone fires on expensive ones
        # over a rounding error.
        if ratio > config.DEAL_RATIO:
            continue
        saving = predicted - o["price"]
        if saving < config.MIN_ABS_SAVING:
            continue

        kind = "mistake" if z >= config.MISTAKE_Z else "drop"

        conn.execute(
            """
            INSERT OR IGNORE INTO deal
                (observation_id, origin, destination, depart_date, return_date,
                 trip_class, price, baseline_p50, discount_pct, abs_saving,
                 dtd, dtd_bucket, outlier_z, kind, flags, detected_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (o["id"], o["origin"], o["destination"], o["depart_date"],
             o["return_date"], o["trip_class"], o["price"], predicted,
             round((1 - ratio) * 100, 1), round(saving, 0), dtd, bucket,
             round(z, 2), kind, json.dumps(quality_flags(o)), now),
        )
        found += 1

    conn.commit()
    return {"candidates_examined": len(rows), "deals_found": found}


if __name__ == "__main__":
    conn = db.connect()
    for k, v in run(conn).items():
        print(f"  {k:24} {v}")
