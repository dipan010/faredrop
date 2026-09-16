"""Flag observations that sit far enough below their route-month baseline.

Deliberately simple: once a baseline exists this is arithmetic. The judgment
lives in the quality filters and, ultimately, in you reading the digest --
you are the review queue at this scale.
"""

import json
from datetime import datetime, timezone

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


def run(conn):
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    rows = conn.execute(
        """
        SELECT o.*, b.p50, b.mad, b.n AS baseline_n
        FROM fare_observation o
        JOIN baseline b
          ON  b.origin       = o.origin
          AND b.destination  = o.destination
          AND b.depart_month = o.depart_month
          AND b.trip_class   = o.trip_class
        LEFT JOIN deal d ON d.observation_id = o.id
        WHERE d.id IS NULL
          AND b.n >= ?
          AND (o.expires_at IS NULL OR o.expires_at > ?)
        """,
        (config.MIN_OBSERVATIONS, now),
    ).fetchall()

    found = 0
    for o in rows:
        p50, mad = o["p50"], o["mad"]
        if not p50:
            continue
        ratio = o["price"] / p50
        if ratio > config.DEAL_RATIO:
            continue

        # MAD-based outlier score, scaled to be comparable to a z-score.
        kind = "drop"
        if mad and (p50 - o["price"]) / (1.4826 * mad) >= config.MISTAKE_Z:
            kind = "mistake"

        conn.execute(
            """
            INSERT OR IGNORE INTO deal
                (observation_id, origin, destination, depart_date, return_date,
                 trip_class, price, baseline_p50, discount_pct, kind, flags,
                 detected_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (o["id"], o["origin"], o["destination"], o["depart_date"],
             o["return_date"], o["trip_class"], o["price"], p50,
             round((1 - ratio) * 100, 1), kind,
             json.dumps(quality_flags(o)), now),
        )
        found += 1

    conn.commit()
    return {"candidates_examined": len(rows), "deals_found": found}


if __name__ == "__main__":
    conn = db.connect()
    for k, v in run(conn).items():
        print(f"  {k:24} {v}")
