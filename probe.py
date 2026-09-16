"""Dump raw payloads from every candidate endpoint, so the parser is written
against what the API actually returns rather than what the docs claim.

Open question this answers: whether /v2/prices/month-matrix is one-way or
round-trip, and which endpoint gives the densest per-day history in one call.

    python probe.py            # uses config.ORIGINS[0] -> DXB
    python probe.py BLR SIN
"""

import json
import sys
from datetime import date

import api
import config
import db

RAW = "raw"


def next_month():
    t = date.today()
    return f"{t.year + (t.month // 12)}-{(t.month % 12) + 1:02d}"


def probe(origin, dest):
    conn = db.connect()
    month = next_month()
    calls = [
        ("cheap", "/v1/prices/cheap",
         {"origin": origin, "destination": dest, "depart_date": month}),
        ("cheap_roundtrip", "/v1/prices/cheap",
         {"origin": origin, "destination": dest,
          "depart_date": month, "return_date": month}),
        ("month_matrix", "/v2/prices/month-matrix",
         {"origin": origin, "destination": dest, "month": f"{month}-01"}),
        ("calendar", "/v1/prices/calendar",
         {"origin": origin, "destination": dest,
          "depart_date": month, "calendar_type": "departure_date"}),
        ("direct", "/v1/prices/direct",
         {"origin": origin, "destination": dest, "depart_date": month}),
        ("latest", "/v2/prices/latest",
         {"origin": origin, "destination": dest,
          "beginning_of_period": f"{month}-01", "period_type": "month",
          "limit": 100}),
    ]

    print(f"probing {origin} -> {dest} for {month}\n")
    for name, path, params in calls:
        try:
            payload, _ = api.get(path, params, conn=conn)
        except api.ApiError as exc:
            print(f"  {name:16} FAILED  {exc}")
            continue

        out = f"{RAW}/probe_{name}_{origin}{dest}.json"
        with open(out, "w") as fh:
            json.dump(payload, fh, indent=2)

        data = payload.get("data") if isinstance(payload, dict) else payload
        n = len(data) if hasattr(data, "__len__") else "?"
        sample = None
        if isinstance(data, dict) and data:
            k = next(iter(data))
            sample = {k: data[k]}
        elif isinstance(data, list) and data:
            sample = data[0]

        print(f"  {name:16} {n:>4} items -> {out}")
        if sample is not None:
            text = json.dumps(sample, indent=2)
            for line in text.splitlines()[:14]:
                print(f"      {line}")
            print()
    conn.commit()
    print("Raw payloads are in ./raw/ -- inspect before the parser is written.")


if __name__ == "__main__":
    args = sys.argv[1:]
    origin = args[0] if args else config.ORIGINS[0]
    dest = args[1] if len(args) > 1 else "DXB"
    probe(origin, dest)
