"""Token-free checks: parser shape, and that collect -> baseline -> detect
-> digest actually chains. Uses a throwaway DB, never data/faredrop.db.

Run: python3 test_pipeline.py
"""

import json
import random
import tempfile
from pathlib import Path

import math

import baseline
import collect
import config
import db
import detect

SAMPLE = {
    "success": True,
    "data": {
        "DXB": {
            "0": {"price": 18450, "airline": "EK", "flight_number": 565,
                  "departure_at": "2026-11-14T03:45:00Z",
                  "return_at": "2026-11-22T21:10:00Z",
                  "expires_at": "2026-09-19T00:00:00Z",
                  "number_of_changes": 0, "duration": 235, "distance": 2192,
                  "found_at": "2026-09-16T11:02:00Z", "actual": True},
            "1": {"price": 21300, "airline": "6E", "flight_number": "1471",
                  "departure_at": "2026-11-03", "return_at": "2026-11-11",
                  "number_of_changes": 1, "trip_class": 0},
            "2": {"airline": "XX"},            # no price -> dropped
        }
    },
}


def check(label, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
    assert cond, label


def main():
    rows = collect._parse(SAMPLE, "BLR", "DXB", "2026-09-17T06:00:00+00:00")
    print("parser")
    check("drops the priceless offer", len(rows) == 2)
    r = rows[0]
    check("depart_date sliced to a day", r["depart_date"] == "2026-11-14")
    check("depart_month groupable", r["depart_month"] == "2026-11")
    check("return_date sliced", r["return_date"] == "2026-11-22")
    check("fetched_at is our clock, not found_at",
          r["fetched_at"].startswith("2026-09-17"))
    check("price is a float", isinstance(r["price"], float))
    check("stops read from number_of_changes", r["stops"] == 0)
    check("flight_number stringified", r["flight_number"] == "565")
    check("source records the endpoint", r["source"] == collect.ENDPOINT)
    check("every NOT NULL column present",
          all(r[c] is not None for c in
              ("origin", "destination", "depart_month", "trip_class",
               "price", "currency", "fetched_at", "source")))
    check("bare-date offer parses too", rows[1]["depart_date"] == "2026-11-03")
    check("unparseable payload is empty, not an error",
          collect._parse({"data": []}, "BLR", "DXB", "x") == []
          and collect._parse(None, "BLR", "DXB", "x") == [])

    with tempfile.TemporaryDirectory() as tmp:
        conn = db.connect(str(Path(tmp) / "t.db"))
        conn.execute("INSERT INTO route (origin,destination) VALUES ('BLR','DXB')")

        print("\ninsert")
        check("rows insert", collect._insert(conn, rows) == 2)
        # Dedup within one payload leans on `stops` being non-NULL: SQLite
        # treats every NULL in a UNIQUE index as distinct, so if the live
        # endpoint omits number_of_changes/transfers this property lapses.
        # Harmless -- offers in one payload are genuinely different fares,
        # and fetched_at is what separates runs -- but don't over-trust it.
        check("same run dedups", collect._insert(conn, rows) == 0)
        later = collect._parse(SAMPLE, "BLR", "DXB", "2026-09-18T06:00:00+00:00")
        check("a later run is new history", collect._insert(conn, later) == 2)

        print("\nbaseline + detect")
        # 30 normal observations around 40k, then one 14k outlier.
        random.seed(7)
        obs = [{**rows[0], "price": float(random.gauss(40000, 2500)),
                "fetched_at": f"2026-08-{d:02d}T06:00:00+00:00",
                "expires_at": "2020-01-01T00:00:00Z"}   # long expired on purpose
               for d in range(1, 31)]
        collect._insert(conn, obs)
        res = baseline.compute(conn)
        check("expired observations still build history",
              res["cells_written"] >= 1)
        b = conn.execute("SELECT * FROM baseline WHERE destination='DXB'").fetchone()
        check(f"n counts them all (n={b['n']})", b["n"] >= 30)
        check(f"p50 near 40k (p50={b['p50']:.0f})", 35000 < b["p50"] < 45000)

        collect._insert(conn, [{**rows[0], "price": 14000.0,
                                "fetched_at": "2026-09-19T06:00:00+00:00",
                                "expires_at": None}])
        baseline.compute(conn)
        d = detect.run(conn)
        check(f"the outlier is flagged ({d['deals_found']} found)",
              d["deals_found"] >= 1)
        deal = conn.execute(
            "SELECT * FROM deal ORDER BY discount_pct DESC").fetchone()
        check(f"classed as a mistake fare (kind={deal['kind']})",
              deal["kind"] == "mistake")
        check("carries the bag/visa caveat",
              any("transit visa" in f for f in json.loads(deal["flags"])))
        # An expired fare that IS cheap enough to qualify -- the only way to
        # tell "history counts expired fares" apart from "deals don't".
        collect._insert(conn, [{**rows[0], "price": 15000.0,
                                "fetched_at": "2026-09-20T06:00:00+00:00",
                                "expires_at": "2020-01-01T00:00:00Z"}])
        baseline.compute(conn)
        detect.run(conn)
        check("an expired fare under the deal ratio is NOT flagged",
              conn.execute("SELECT count(*) FROM deal WHERE price = 15000.0")
                  .fetchone()[0] == 0)
        check("...while the live one at the same discount still is",
              conn.execute("SELECT count(*) FROM deal WHERE price = 14000.0")
                  .fetchone()[0] == 1)
        check("and it still counted toward the baseline",
              conn.execute("SELECT count(*) FROM fare_observation"
                           " WHERE price = 15000.0").fetchone()[0] == 1)

        print("\nreparse")
        raw = json.dumps(SAMPLE)
        for ts in ("2026-09-17T06:00:00+00:00", "2026-09-18T06:00:00+00:00"):
            conn.execute(
                "INSERT INTO raw_response (endpoint, params, status,"
                " fetched_at, body) VALUES (?,?,?,?,?)",
                (collect.ENDPOINT,
                 json.dumps({"origin": "BLR", "destination": "DXB"}),
                 200, ts, raw))
        conn.commit()
        first = collect.reparse(conn)
        check(f"reparse reads both payloads (n={first['payloads']})",
              first["payloads"] == 2)
        check("it refills the rows already inserted, adding none",
              first["observations_new"] == 0)
        check("and is idempotent on a second pass",
              collect.reparse(conn)["observations_new"] == 0)

        print("\nmodel: dedup")
        # A fare that sits in the feed for a week is one fare, not seven.
        c2 = db.connect(str(Path(tmp) / "dedup.db"))
        repeated = [{**rows[0], "price": 30000.0,
                     "fetched_at": f"2026-08-{d:02d}T06:00:00+00:00"}
                    for d in range(1, 21)]
        collect._insert(c2, repeated)
        check("20 rows of one fare collapse to 1 distinct quote",
              len(baseline.distinct_quotes(c2)) == 1)
        check("coverage reports both counts",
              baseline.coverage(c2)[0]["n"] == 1
              and baseline.coverage(c2)[0]["n_raw"] == 20)
        check("and that cell is NOT declared ready",
              baseline.compute(c2)["cells_written"] == 0)

        print("\nmodel: booking horizon")
        check("buckets partition the horizon",
              baseline.bucket_for(3) == "last-minute"
              and baseline.bucket_for(30) == "near"
              and baseline.bucket_for(90) == "mid"
              and baseline.bucket_for(300) == "far")
        check("a missing horizon is not forced into a bucket",
              baseline.bucket_for(None) is None)
        check("no horizon data makes the term a no-op",
              baseline.offset_lookup({}, {}, ("BLR", "DXB", 0), "near") == 0.0)

        print("\nmodel: scoring")
        # 20% below a 50k prediction, with the horizon term zero.
        pred, ratio, z = detect.score(40000.0, math.log(50000.0), 0.10, 0.0)
        check(f"prediction inverts the log level (₹{pred:,.0f})",
              abs(pred - 50000) < 1)
        check(f"ratio is scale-free ({ratio:.2f})", abs(ratio - 0.8) < 0.01)
        check("a cheaper fare scores further into the tail",
              detect.score(30000.0, math.log(50000.0), 0.10, 0.0)[2] > z)
        check("the horizon term moves the prediction",
              detect.score(40000.0, math.log(50000.0), 0.10, 0.2)[0] > pred)
        check("log scale is floored, so agreement can't make z infinite",
              abs(detect.score(1.0, 0.0, config.MIN_LOG_SCALE, 0.0)[2]) < 1e9)

        print("\nmodel: the absolute-saving gate")
        c3 = db.connect(str(Path(tmp) / "floor.db"))
        # A cheap route: 45% off, but only a few hundred rupees saved.
        random.seed(3)
        cheap = [{**rows[0], "price": float(random.gauss(1200, 90)),
                  "depart_date": f"2026-11-{d:02d}", "depart_month": "2026-11",
                  "fetched_at": f"2026-08-{d:02d}T06:00:00+00:00"}
                 for d in range(1, 21)]
        collect._insert(c3, cheap)
        collect._insert(c3, [{**rows[0], "price": 650.0,
                              "depart_date": "2026-11-25",
                              "depart_month": "2026-11",
                              "fetched_at": "2026-09-01T06:00:00+00:00",
                              "expires_at": None}])
        baseline.compute(c3)
        detect.run(c3)
        check("a big percentage off pocket change is not a deal",
              c3.execute("SELECT count(*) FROM deal").fetchone()[0] == 0)

        print("\nguards")
        check("empty route list exits with instructions",
              _exits_cleanly(db.connect(str(Path(tmp) / "empty.db"))))

    print("\nall checks passed")


def _exits_cleanly(conn):
    try:
        collect.run(conn)
    except SystemExit as e:
        return "refdata.py destinations" in str(e)
    return False


if __name__ == "__main__":
    main()
