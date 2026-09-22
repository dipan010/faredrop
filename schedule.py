"""Which cells get today's API calls.

The whole argument is a threshold effect. Below MIN_OBSERVATIONS a cell
produces nothing at all -- no baseline, so no deal can be detected in it at
any price. So 240 cells at n=6 are worth exactly zero and 40 cells at n=12
are worth everything. When the budget cannot walk every cell daily, spreading
it evenly is the one allocation guaranteed to produce nothing for longest.

Hence cohorts: drive a subset across the line, then hold them there and start
the next subset. Two rules fall out, and they are the entire policy.

    1. Mature cells are served first. They are the only cells that can
       produce a deal today, and a deal missed is not recoverable later.
    2. Whatever is left goes to the cells CLOSEST to maturity, not the
       neediest. Finishing a cell at n=11 buys a working baseline; starting
       a fifth cell at n=0 buys nothing.

Rule 2 is the counter-intuitive one and it is the point. Deliberately absent:
staleness weights, volatility weights, urgency weights. They are refinements
that cannot be calibrated against zero observations, and each one dilutes an
argument that currently needs no tuning at all.

**When this is worth using, measured rather than assumed.** In simulation,
against a plain round-robin over 24 cells for 30 days:

    budget/day    round-robin matures    cohort matures
             1                      0                 3
             2                      0                 9
             3                     16                16
             4                     24                18
             6                     24                24
            12          24 (360 calls)    24 (271 calls)

Read that for its shape, not its numbers. Every figure falls out of
simulate.py's invented yield -- three quotes per call, lingering one to four
days -- so the crossover moves when the yield does. What it establishes is
that two regimes exist and which one you are in turns on whether the budget
can mature every cell; it does not establish that 3 calls/day is anybody's
crossover. diagnose() computes that from real history instead.

Two regimes, and only one of them wants a scheduler. When the budget cannot
mature every cell, round-robin matures *nothing* -- every cell stalls just
short of the line -- and cohorting is the difference between a working system
and no system. When the budget is comfortable, round-robin is as good and
simpler, and at 12/day the only thing cohorting buys is a quarter of the
calls back by not re-polling what needs nothing.

So this is not automatically the better policy, and collect.py still walks
uniformly by default. `--scheduled` is for when the budget is genuinely
short, and even then, watching fewer destinations is the more legible fix.

    python3 schedule.py            # today's plan and why
    python3 schedule.py --budget 60
"""

import argparse
from datetime import date, datetime, timezone

import baseline
import collect
import config
import db


def _cells(conn):
    """Every (origin, destination, month) worth polling right now."""
    routes = collect.active_routes(conn)
    months = collect.months_ahead(config.MONTHS_AHEAD)
    return [(r["origin"], r["destination"], m) for r in routes for m in months]


def _popularity(conn):
    """Route -> rank from refdata (0 = most popular). Missing sorts last.

    Only used to break ties between cells we have never touched: with nothing
    else to go on, open the destination people actually fly to first.
    """
    return {(r["origin"], r["destination"]):
            (r["popularity"] if r["popularity"] is not None else 10**6)
            for r in conn.execute(
                "SELECT origin, destination, popularity FROM route")}


def _maturity(conn):
    """Distinct quotes per cell. The only state the policy reads."""
    out = {}
    for q in baseline.distinct_quotes(conn):
        key = (q["origin"], q["destination"], q["depart_month"])
        out[key] = out.get(key, 0) + 1
    return out


def _last_polled(conn):
    """When each cell was last CALLED, from the raw log.

    Deliberately not taken from fare_observation: a call that returned
    nothing is still a call, and treating it as never-polled would make the
    scheduler hammer dead cells forever.
    """
    import json
    out = {}
    for r in conn.execute(
            "SELECT params, fetched_at FROM raw_response"
            " WHERE endpoint = ? ORDER BY id", (collect.ENDPOINT,)):
        try:
            p = json.loads(r["params"])
        except (json.JSONDecodeError, TypeError):
            continue
        key = (p.get("origin"), p.get("destination"), p.get("depart_date"))
        if all(key):
            out[key] = max(out.get(key, ""), r["fetched_at"])
    return out


def _days_since(stamp, today):
    if not stamp:
        return None
    try:
        return (today - datetime.fromisoformat(stamp[:10]).date()).days
    except ValueError:
        return None


def plan(conn, budget=None, today=None, min_observations=None):
    """Today's poll list, plus the reasoning, as (plan, explanation)."""
    budget = config.DAILY_CALL_BUDGET if budget is None else budget
    min_n = min_observations or config.MIN_OBSERVATIONS
    today = today or date.today()

    cells = _cells(conn)
    matured = _maturity(conn)
    polled = _last_polled(conn)

    mature, maturing, untouched = [], [], []
    for cell in cells:
        n = matured.get(cell, 0)
        if n >= min_n:
            mature.append((cell, n))
        elif n > 0:
            maturing.append((cell, n))
        else:
            untouched.append((cell, 0))

    # 1. Mature cells that are due. The only cells that can yield a deal
    #    today, so they come first -- but not without limit. Maintenance is
    #    capped so that exploration always keeps a slice: left uncapped the
    #    policy is absorbing, and a cohort that fills the budget locks the
    #    remaining cells out for good.
    due = []
    for cell, n in mature:
        age = _days_since(polled.get(cell), today)
        if age is None or age >= config.MAINTENANCE_DAYS:
            due.append(cell)

    unmatured = len(maturing) + len(untouched)
    cap = budget
    if unmatured:
        cap = max(1, int(budget * (1 - config.EXPLORE_RESERVE)))
    # Oldest first, so the cells skipped by the cap rotate rather than
    # starving the same ones every day.
    due.sort(key=lambda c: polled.get(c) or "")
    deferred = max(0, len(due) - cap)
    chosen = due[:cap]
    remaining = budget - len(chosen)

    # 2. Closest to maturity first. Finishing beats starting.
    maturing.sort(key=lambda t: -t[1])
    for cell, _ in maturing:
        if remaining <= 0:
            break
        chosen.append(cell)
        remaining -= 1

    # 3. Only then open new ground: nearest departure month first, since those
    #    baselines become useful soonest, then the more popular destination.
    pop = _popularity(conn)
    untouched.sort(key=lambda t: (t[0][2], pop.get((t[0][0], t[0][1]), 10**6),
                                  t[0][0], t[0][1]))
    for cell, _ in untouched:
        if remaining <= 0:
            break
        chosen.append(cell)
        remaining -= 1

    return chosen, {
        "budget": budget,
        "cells_total": len(cells),
        "mature": len(mature),
        "mature_due": len(due),
        "maturing": len(maturing),
        "untouched": len(untouched),
        "maintenance_deferred": deferred,
        "planned": len(chosen),
        "unspent": remaining,
        "starved": max(0, (len(due) + len(maturing) + len(untouched)) - len(chosen)),
    }


def measured_yield(conn):
    """Distinct quotes actually gained per call, from our own history.

    Returns None until there is enough to measure. config.QUOTES_PER_CALL is
    a placeholder standing in until then -- and it is only ever used to
    estimate how long maturity will take, never to allocate calls.
    """
    calls = conn.execute(
        "SELECT count(*) FROM raw_response WHERE endpoint = ?",
        (collect.ENDPOINT,)).fetchone()[0]
    if calls < 20:
        return None
    return len(baseline.distinct_quotes(conn)) / calls


def eta_days(conn, budget=None, min_observations=None):
    """Rough days until the next cohort matures, stated as the guess it is."""
    budget = config.DAILY_CALL_BUDGET if budget is None else budget
    min_n = min_observations or config.MIN_OBSERVATIONS
    per_call = measured_yield(conn)
    source = "measured" if per_call else "placeholder"
    per_call = per_call or config.QUOTES_PER_CALL
    if per_call <= 0:
        return None, source
    _, why = plan(conn, budget=budget, min_observations=min_n)
    working = budget - why["mature_due"]
    if working <= 0:
        return None, source
    return round(min_n / per_call), source


def diagnose(conn, budget=None):
    """Which regime this budget is in, and therefore which policy to use."""
    budget = config.DAILY_CALL_BUDGET if budget is None else budget
    cells = len(_cells(conn))
    if not cells:
        return "No routes seeded yet, so nothing to schedule."
    per_call = measured_yield(conn) or config.QUOTES_PER_CALL
    source = "measured" if measured_yield(conn) else "placeholder yield"
    calls_per_cell = config.MIN_OBSERVATIONS / max(per_call, 1e-9)
    days_uniform = (cells * calls_per_cell) / max(budget, 1)
    if days_uniform <= 30:
        return (f"A uniform walk matures all {cells} cells in ~"
                f"{days_uniform:.0f} days ({source}). That is comfortable --"
                f" use plain `collect.py`; this scheduler buys you little.")
    return (f"A uniform walk would need ~{days_uniform:.0f} days to mature"
            f" {cells} cells ({source}), during which it produces nothing."
            f" Cohorting, or fewer destinations, is the fix.")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--budget", type=int, default=None)
    args = ap.parse_args()

    conn = db.connect()
    chosen, why = plan(conn, budget=args.budget)
    for k, v in why.items():
        print(f"  {k:16} {v}")
    if why["starved"]:
        print(f"\n  {why['starved']} cells get nothing today. Either raise "
              f"DAILY_CALL_BUDGET or watch fewer destinations.")
    days, source = eta_days(conn, budget=args.budget)
    if days:
        print(f"\n  ~{days} days to a matured cohort ({source} yield)")
    print("  " + diagnose(conn, budget=args.budget))
    for cell in chosen[:15]:
        print(f"    {cell[0]}->{cell[1]} {cell[2]}")
    if len(chosen) > 15:
        print(f"    ... and {len(chosen)-15} more")
