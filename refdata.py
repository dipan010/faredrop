"""Reference tables and route-list seeding.

`python refdata.py sync`         -> download airports/airlines/cities (no token)
`python refdata.py destinations` -> ask the API what's popular from each origin
                                    and write data/destinations.json (needs token)
"""

import json
import sys
from pathlib import Path

import api
import config
import db

DATA = Path("data")


def sync():
    DATA.mkdir(exist_ok=True)
    summary = {}
    for name in ("airports", "airlines", "cities", "countries"):
        payload = api.reference(name)
        (DATA / f"{name}.json").write_text(json.dumps(payload))
        summary[name] = len(payload)
    return summary


def load(name):
    return json.loads((DATA / f"{name}.json").read_text())


def airport_index():
    """IATA -> {name, city_code, country, tz} for airports with a code."""
    idx = {}
    for a in load("airports"):
        code = a.get("code")
        if code:
            idx[code] = {
                "name": a.get("name"),
                "city": a.get("city_code"),
                "country": a.get("country_code"),
                "tz": a.get("time_zone"),
            }
    return idx


def airline_index():
    return {a["code"]: a.get("name") for a in load("airlines") if a.get("code")}


def seed_destinations():
    """Use /v1/city-directions to pick the destinations worth watching.

    Popularity comes from the API rather than a list I invented, which keeps
    the route universe honest about where people from this origin actually fly.
    """
    conn = db.connect()
    airports = airport_index()
    out = {}
    for origin in config.ORIGINS:
        payload, _ = api.get("/v1/city-directions",
                             {"origin": origin}, conn=conn)
        data = payload.get("data", {})
        # data: {DEST: {price, airline, flight_number, departure_at, ...}}
        # International only, as Zomunk does. Domestic fares are the cheapest
        # in this feed, so left in they take most of the list and the call
        # budget, for alerts about a cheap flight to Pune.
        home = airports.get(origin, {}).get("country")
        domestic = [d for d in data
                    if airports.get(d, {}).get("country") == home]
        data = {d: v for d, v in data.items() if d not in domestic}
        if domestic:
            conn.executemany(
                "UPDATE route SET active = 0"
                " WHERE origin = ? AND destination = ?",
                [(origin, d) for d in domestic])
        ranked = sorted(data.items(),
                        key=lambda kv: kv[1].get("price", 10**9))
        picks = []
        for rank, (dest, info) in enumerate(ranked[: config.MAX_DESTINATIONS]):
            picks.append({
                "code": dest,
                "name": airports.get(dest, {}).get("name", dest),
                "country": airports.get(dest, {}).get("country"),
                "seen_price": info.get("price"),
            })
            # Rank, so a cheaper/more-popular destination sorts first. Without
            # it schedule.py has nothing better than alphabetical order to pick
            # which unexplored cell to open next.
            conn.execute(
                "INSERT INTO route (origin, destination, popularity)"
                " VALUES (?,?,?)"
                " ON CONFLICT (origin, destination)"
                " DO UPDATE SET popularity = excluded.popularity",
                (origin, dest, rank),
            )
        # Hand-picked routes, after the ranked ones so they sort behind them
        # for the scheduler but are never left out.
        seen = {p["code"] for p in picks}
        for dest in config.EXTRA_DESTINATIONS.get(origin, []):
            if dest in seen:
                continue
            rank = len(picks)
            picks.append({
                "code": dest,
                "name": airports.get(dest, {}).get("name", dest),
                "country": airports.get(dest, {}).get("country"),
                "seen_price": None,
            })
            conn.execute(
                "INSERT INTO route (origin, destination, popularity)"
                " VALUES (?,?,?)"
                " ON CONFLICT (origin, destination)"
                " DO UPDATE SET popularity = excluded.popularity, active = 1",
                (origin, dest, rank),
            )
        out[origin] = picks
    conn.commit()
    Path(config.DESTINATIONS_FILE).write_text(json.dumps(out, indent=2))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "sync"
    if cmd == "sync":
        for name, n in sync().items():
            print(f"  {name:10} {n:>6} records")
    elif cmd == "destinations":
        for origin, picks in seed_destinations().items():
            print(f"{origin}: {len(picks)} destinations")
            for p in picks[:10]:
                print(f"   {p['code']}  {p['name']}")
            if len(picks) > 10:
                print(f"   ... and {len(picks)-10} more")
    else:
        sys.exit(f"unknown command: {cmd}")
