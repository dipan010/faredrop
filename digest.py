"""Today's deals, plus an honest read on whether the data is ready yet.

This is the review queue. At one origin you are the reviewer -- the digest
shows candidates and their caveats; you decide what's real.
"""

import json
import sys

import baseline
import config
import db

BOLD, DIM, RESET = "\033[1m", "\033[2m", "\033[0m"
AMBER, GREEN = "\033[33m", "\033[32m"


def rupees(x):
    return f"₹{x:,.0f}"


def status(conn):
    c = db.counts(conn)
    print(f"{BOLD}faredrop{RESET} {DIM}— collector status{RESET}")
    print(f"  routes tracked      {c['routes']}")
    print(f"  observations        {c['observations']:,}")
    print(f"  route-months        {c['route_months']}")
    print(f"  baselines ready     {c['baselines']}")
    if c["first_observation"]:
        print(f"  collecting since    {c['first_observation']}")
    else:
        print(f"\n  {AMBER}No observations yet.{RESET}")
        print("  Set TRAVELPAYOUTS_TOKEN, then run: python3 collect.py")
        return False

    rows = baseline.coverage(conn)
    if rows:
        raw = sum(r["n_raw"] for r in rows)
        distinct = sum(r["n"] for r in rows)
        # The gap between these two is the honest readiness number. The feed
        # repeats the same fare daily, so raw rows flatter the history badly.
        print(f"  distinct fares      {distinct:,} {DIM}(from {raw:,} rows){RESET}")
        not_ready = [r for r in rows if r["n"] < config.MIN_OBSERVATIONS]
        if not_ready:
            print(f"\n  {DIM}{len(not_ready)} of {len(rows)} route-months still "
                  f"below {config.MIN_OBSERVATIONS} distinct quotes{RESET}")
    return True


def deals(conn, limit=25):
    rows = conn.execute(
        """
        SELECT * FROM deal
        ORDER BY (kind='mistake') DESC, outlier_z DESC, discount_pct DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()

    if not rows:
        print(f"\n  {DIM}No deals flagged. Either nothing has dropped, or the "
              f"baselines aren't seasoned yet.{RESET}")
        return

    print(f"\n{BOLD}Flagged fares{RESET}")
    for d in rows:
        # "look first", not a verdict -- the score ranks, it doesn't classify.
        marker = (f"{AMBER}look first{RESET}" if d["kind"] == "mistake"
                  else f"{GREEN}drop{RESET}")
        cabin = config.TRIP_CLASSES.get(d["trip_class"], "?")
        dates = d["depart_date"] or "?"
        if d["return_date"]:
            dates += f" → {d['return_date']}"
        horizon = (f"{d['dtd']}d out" if d["dtd"] is not None else "horizon ?")
        print(f"\n  {BOLD}{d['origin']} → {d['destination']}{RESET}  "
              f"{rupees(d['price'])}  "
              f"{DIM}(expected {rupees(d['baseline_p50'])} at {horizon}){RESET}")
        saving = f", saves {rupees(d['abs_saving'])}" if d["abs_saving"] else ""
        print(f"    {d['discount_pct']}% below expected{saving}   {marker}   "
              f"{cabin}   {dates}")
        for flag in json.loads(d["flags"] or "[]"):
            print(f"    {DIM}⚠ {flag}{RESET}")
        print(f"    {DIM}https://www.google.com/travel/flights?q=Flights%20"
              f"from%20{d['origin']}%20to%20{d['destination']}{RESET}")


if __name__ == "__main__":
    conn = db.connect()
    if status(conn):
        deals(conn, int(sys.argv[1]) if len(sys.argv) > 1 else 25)
