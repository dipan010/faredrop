"""Token-free checks: parser shape, and that collect -> baseline -> detect
-> digest actually chains. Uses a throwaway DB, never data/faredrop.db.

Run: python3 test_pipeline.py
"""

import json
import random
import tempfile
from pathlib import Path

import math
from datetime import datetime, timedelta, timezone

import backup
import baseline
import collect
import notify
import schedule
import verify
import config
import db
import detect
import digest
import health

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

# The shape actually observed on 2026-10-01: no stop field on the offer, the
# stop count is the key it sits under.
LIVE = {"success": True, "currency": "inr", "data": {"DXB": {
    "0": {"airline": "EK", "departure_at": "2026-11-27T10:25:00+05:30",
          "return_at": "2026-12-05T13:35:00+04:00", "price": 43237,
          "flight_number": 565, "duration": 455},
    "1": {"airline": "GF", "departure_at": "2026-11-27T05:00:00+05:30",
          "return_at": "2026-12-05T07:45:00+04:00", "price": 29254,
          "flight_number": 283, "duration": 1220}}}}


def check(label, cond):
    print(f"  {'ok  ' if cond else 'FAIL'}  {label}")
    assert cond, label


# Fixtures are timed relative to now, never written as literal dates. An
# earlier version hardcoded them; they sat inside DETECT_WINDOW_DAYS on the
# day they were written and silently fell out of it days later, turning a
# passing suite into a failing one with no code change. A test whose result
# depends on the calendar is not a test.
NOW = datetime.now(timezone.utc)


def at(days_ago, hour=6):
    return (NOW - timedelta(days=days_ago)).replace(
        hour=hour, minute=0, second=0, microsecond=0).isoformat(
            timespec="seconds")


def main():
    rows = collect._parse(SAMPLE, "BLR", "DXB", at(0))
    print("parser")
    check("drops the priceless offer", len(rows) == 2)
    r = rows[0]
    check("depart_date sliced to a day", r["depart_date"] == "2026-11-14")
    check("depart_month groupable", r["depart_month"] == "2026-11")
    check("return_date sliced", r["return_date"] == "2026-11-22")
    check("fetched_at is our clock, not found_at",
          r["fetched_at"].startswith(NOW.date().isoformat()))
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
    live = {x["airline"]: x for x in collect._parse(LIVE, "BLR", "DXB", at(0))}
    check("live shape: stops come from the offer's key",
          live["EK"]["stops"] == 0 and live["GF"]["stops"] == 1)
    check("live shape: a return month later than departure is kept",
          live["GF"]["return_date"] == "2026-12-05"
          and live["GF"]["depart_month"] == "2026-11")

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
        later = collect._parse(SAMPLE, "BLR", "DXB", at(-1))
        check("a later run is new history", collect._insert(conn, later) == 2)

        print("\nbaseline + detect")
        # 30 normal observations around 40k, then one 14k outlier.
        random.seed(7)
        obs = [{**rows[0], "price": float(random.gauss(40000, 2500)),
                "fetched_at": at(20 + d),
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
                                "fetched_at": at(0), "expires_at": None}])
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
                                "fetched_at": at(0, hour=7),
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
        # The same stamps the rows above were parsed with -- reparse must
        # refill those exact observations, not create a parallel set.
        for ts in (at(0), at(-1)):
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
        far = (NOW + timedelta(days=75)).date().isoformat()
        cheap = [{**rows[0], "price": float(random.gauss(1200, 90)),
                  "depart_date": far, "depart_month": far[:7],
                  "fetched_at": at(20 + d)}
                 for d in range(1, 21)]
        collect._insert(c3, cheap)
        collect._insert(c3, [{**rows[0], "price": 650.0,
                              "depart_date": far, "depart_month": far[:7],
                              "fetched_at": at(0), "expires_at": None}])
        baseline.compute(c3)
        detect.run(c3)
        check("a big percentage off pocket change is not a deal",
              c3.execute("SELECT count(*) FROM deal").fetchone()[0] == 0)

        print("\nmodel: the recency window")
        c4 = db.connect(str(Path(tmp) / "recency.db"))
        far_off = (NOW + timedelta(days=60)).date().isoformat()
        random.seed(5)
        # Enough distinct history, all of it old.
        collect._insert(c4, [
            {**rows[0], "price": float(random.gauss(40000, 2000)),
             "depart_date": far_off, "depart_month": far_off[:7],
             "fetched_at": at(40 + i)} for i in range(20)])
        # One fare that was a bargain months ago, one found today.
        collect._insert(c4, [
            {**rows[0], "price": 14000.0, "depart_date": far_off,
             "depart_month": far_off[:7], "airline": "OLD",
             "fetched_at": at(30), "expires_at": None},
            {**rows[0], "price": 14000.0, "depart_date": far_off,
             "depart_month": far_off[:7], "airline": "NEW",
             "fetched_at": at(0), "expires_at": None}])
        baseline.compute(c4)
        res = detect.run(c4)
        check(f"only recent rows are examined ({res['candidates_examined']} of 22)",
              res["candidates_examined"] < 22)
        flagged = {r[0] for r in c4.execute(
            "SELECT o.airline FROM deal d JOIN fare_observation o"
            " ON o.id = d.observation_id")}
        check("today's bargain is flagged", "NEW" in flagged)
        check("a bargain from 30 days ago is NOT re-served as bookable",
              "OLD" not in flagged)
        check("but it still counts as history",
              any(q["price"] == 14000.0 for q in baseline.distinct_quotes(c4)))
        check("no deal is older than the window",
              c4.execute(
                  "SELECT count(*) FROM deal d JOIN fare_observation o"
                  " ON o.id = d.observation_id WHERE o.fetched_at < ?",
                  (at(config.DETECT_WINDOW_DAYS),)).fetchone()[0] == 0)

        print("\nmodel: pooled fallback")
        per_route, pooled = detect.load_offsets(conn)
        check("the pooled offset is stored under the sentinel route",
              detect.POOLED_SENTINEL == "*" and isinstance(pooled, dict))
        check("no real route leaks into the pooled fallback",
              all(k[0][0] != "*" for k in per_route))

        print("\nrepeat suppression")
        c7 = db.connect(str(Path(tmp) / "repeat.db"))
        far7 = (NOW + timedelta(days=60)).date().isoformat()
        base = {**rows[0], "depart_date": far7, "depart_month": far7[:7]}
        random.seed(11)
        collect._insert(c7, [{**base, "price": float(random.gauss(40000, 2000)),
                              "airline": f"H{i}", "fetched_at": at(30 + i)}
                             for i in range(20)])
        baseline.compute(c7)

        def seen_on(days_ago, price, airline="ZZ"):
            """One cheap fare for the SAME itinerary, seen N days ago."""
            collect._insert(c7, [{**base, "price": float(price),
                                  "airline": airline, "expires_at": None,
                                  "fetched_at": at(days_ago)}])
            baseline.compute(c7)
            return detect.run(c7, window_days=40)

        r1 = seen_on(2, 14000)
        check(f"a new deal is recorded ({r1['deals_found']} found)",
              r1["deals_found"] == 1)
        r2 = seen_on(1, 14000, airline="YY")
        check(f"the same fare seen again is suppressed "
              f"({r2['repeats_suppressed']} suppressed)",
              r2["deals_found"] == 0 and r2["repeats_suppressed"] >= 1)
        r3 = seen_on(1, 13720, airline="XX")          # 2% cheaper
        check("a 2% improvement is not news", r3["deals_found"] == 0)
        r4 = seen_on(0, 11900, airline="WW")          # 15% cheaper
        check(f"a 15% improvement is ({r4['deals_found']} found)",
              r4["deals_found"] == 1)
        check("so one itinerary produced two rows, not five",
              c7.execute("SELECT count(*) FROM deal").fetchone()[0] == 2)
        check("both share a fingerprint",
              c7.execute("SELECT count(DISTINCT fingerprint) FROM deal")
                .fetchone()[0] == 1)

        print("\ndelivery")
        sent_box = []
        ok_sender = sent_box.append

        def broken_sender(msg):
            raise OSError("connection refused")

        res = notify.run(c7, sender=broken_sender)
        check(f"a failed send reports it ({res['status'][:24]})",
              res["sent"] == 0 and res["status"].startswith("failed"))
        check("and stamps nothing, so tomorrow retries",
              c7.execute("SELECT count(*) FROM deal"
                         " WHERE notified_at IS NULL").fetchone()[0] == 2)

        res = notify.run(c7, sender=ok_sender)
        check(f"a good send delivers every pending deal ({res['sent']})",
              res["sent"] == 2 and len(sent_box) == 1)
        check("and stamps them",
              c7.execute("SELECT count(*) FROM deal"
                         " WHERE notified_at IS NULL").fetchone()[0] == 0)
        again = notify.run(c7, sender=ok_sender)
        check("a second run sends nothing",
              again["sent"] == 0 and len(sent_box) == 1)

        print("\nthe email itself")
        msg = sent_box[0]
        body = msg.get_body(preferencelist=("plain",)).get_content()
        check(f"subject names the headline deal ({msg['Subject'][:40]}...)",
              "BLR" in msg["Subject"] and "DXB" in msg["Subject"])
        check("subject says how many more", "+1 more" in msg["Subject"])
        check("body carries the price and the expectation",
              "11,900" in body and "expected" in body)
        check("body links a dated Google Flights search",
              "google.com/travel/flights" in body and far7 in body)
        check("body keeps the bag/visa caveat", "transit visa" in body)
        check("it has an HTML alternative too",
              msg.get_body(preferencelist=("html",)) is not None)
        # compose is pure: hand it plain dicts, get a message back. Asserted
        # on content, because a check that cannot fail is worse than none.
        plain = notify.compose([{
            "origin": "BLR", "destination": "CDG", "price": 31000.0,
            "baseline_p50": 62000.0, "discount_pct": 50.0, "abs_saving": 31000.0,
            "dtd": 40, "trip_class": 0, "depart_date": "2027-01-10",
            "return_date": "2027-01-20", "kind": "drop", "flags": "[]"}])
        check("compose works on plain dicts, with no database",
              "CDG" in plain["Subject"] and "31,000" in plain["Subject"])
        check("and renders the itinerary in the body",
              "2027-01-10" in plain.get_body(
                  preferencelist=("plain",)).get_content())

        print("\nno backlog on the first successful send")
        # The shipping state: SMTP unconfigured for weeks while deals pile up
        # unnotified. The first working send must not deliver a graveyard.
        c8 = db.connect(str(Path(tmp) / "backlog.db"))
        for i, age in enumerate((40, 30, 20, 1)):
            c8.execute(
                "INSERT INTO deal (observation_id, origin, destination,"
                " depart_date, return_date, trip_class, price, baseline_p50,"
                " discount_pct, kind, flags, fingerprint, detected_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i, "BLR", "DXB", far7, far7, 0, 10000.0 + i, 30000.0, 60.0,
                 "drop", "[]", f"fp{i}", at(age)))
        c8.commit()
        check(f"only recent unnotified deals are pending "
              f"({len(notify.pending(c8))} of 4)",
              len(notify.pending(c8)) == 1)
        box8 = []
        notify.run(c8, sender=box8.append)
        check("the stale ones age out silently, not as one dead email",
              len(box8) == 1
              and "10,003" in box8[0].get_body(
                  preferencelist=("plain",)).get_content())
        check("and they are left unstamped rather than marked delivered",
              c8.execute("SELECT count(*) FROM deal"
                         " WHERE notified_at IS NULL").fetchone()[0] == 3)

        print("\nthe live re-check")
        # Offline: the Google Flights lookup is injected, like notify's sender.
        c9 = db.connect(str(Path(tmp) / "verify.db"))

        def put(conn, i, depart=far7, ret=far7, price=12000.0):
            conn.execute(
                "INSERT INTO deal (observation_id, origin, destination,"
                " depart_date, return_date, trip_class, price, baseline_p50,"
                " discount_pct, kind, flags, fingerprint, detected_at)"
                " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (i, "BLR", "DXB", depart, ret, 0, price, 30000.0, 60.0,
                 "drop", "[]", f"v{i}", at(1)))
            conn.commit()

        def status_of(i):
            return c9.execute("SELECT gf_status, gf_price FROM deal"
                              " WHERE observation_id=?", (i,)).fetchone()

        put(c9, 1, price=12000.0)
        put(c9, 2, price=12500.0)
        put(c9, 3, ret=None)
        live = {12000.0: 13000, 12500.0: 26000}
        r9 = verify.run(c9, fetch=lambda d: live[d["price"]], pause=0)
        check("a fare still well below expected stays a deal",
              tuple(status_of(1)) == ("still", 13000.0))
        check("one that has climbed back is marked gone",
              status_of(2)["gf_status"] == "gone")
        check("an itinerary without both dates is skipped, not guessed",
              status_of(3)["gf_status"] == "skipped" and r9["checked"] == 2)
        again9 = verify.run(c9, fetch=lambda d: 1 / 0, pause=0)
        check("a deal checked recently is not looked up again",
              again9["checked"] == 0 and again9["status"] == "ok")

        box9 = []
        notify.run(c9, sender=box9.append)
        body9 = box9[0].get_body(preferencelist=("plain",)).get_content()
        check("the alert carries the live price",
              "Google Flights now ₹13,000 -- still a deal" in body9)
        check("a gone deal is still sent while suppression is off, flagged",
              "may already be gone" in body9 and "12,500" in body9)
        check("an unchecked one says so",
              "not re-checked on Google Flights" in body9)

        c9 = db.connect(str(Path(tmp) / "verify2.db"))
        for i in range(5):
            put(c9, 10 + i, price=12000.0 + i)
        calls = []

        def blocked(d):
            calls.append(d)
            raise RuntimeError("429 Too Many Requests")
        r10 = verify.run(c9, fetch=blocked, pause=0)
        check("the first failure ends the run instead of retrying",
              len(calls) == 1 and r10["status"].startswith("stopped"))
        check("and the rest are left unchecked, not marked",
              c9.execute("SELECT count(*) FROM deal WHERE gf_status IS NULL")
                .fetchone()[0] == 4)
        c9.execute("UPDATE deal SET gf_status=NULL, gf_checked_at=NULL")
        calls.clear()
        r11 = verify.run(c9, fetch=lambda d: calls.append(d) or 13000,
                         limit=2, pause=0)
        check("the per-run cap holds", len(calls) == 2 and r11["checked"] == 2)

        def missing(d):
            raise verify.Unavailable("No module named 'fast_flights'")
        r12 = verify.run(c9, fetch=missing, pause=0)
        check("no scraper installed is a clean skip",
              r12["status"].startswith("unavailable") and r12["checked"] == 0)

        print("\nreading the Google Flights page")
        # Shaped like the page seen on 2026-10-02: leg = [.., .., .., from,
        # name, name, to, ...]; item = [[type, airlines, legs], [[_, price]]].
        def leg(a, b):
            return [None, None, None, a, "", "", b]

        def item(price, airline, *stops):
            path = ["BLR", *stops, "KUL"]
            legs = [leg(x, y) for x, y in zip(path, path[1:])]
            return [["X", [airline], legs], [[None, price]] if price else []]
        page = [None, None,
                [[item(32680, "AirAsia"), item(33151, "IndiGo")]],
                [[item(40865, "IndiGo", "MAA"), item(None, "Singapore"),
                  ["garbage"]]]]
        best = verify.cheapest(page)
        check("the cheapest fare is found in either list, not just data[3]",
              best == {"price": 32680, "airline": "AirAsia", "via": []})
        page[2] = [[item(45000, "IndiGo")]]
        check("connections are read from the legs",
              verify.cheapest(page)["via"] == ["MAA"])
        check("priceless and malformed results are skipped, not fatal",
              verify.cheapest([None, None, None,
                               [[item(None, "X"), ["garbage"],
                                 item(50000, "Y")]]])["price"] == 50000)
        try:
            verify.cheapest([None, None, None, [[item(None, "X")]]])
            ok = False
        except RuntimeError:
            ok = True
        check("a page with no priced fare at all is an error", ok)

        c11 = db.connect(str(Path(tmp) / "verify3.db"))
        put(c11, 1, price=12000.0)
        verify.run(c11, fetch=lambda d: {"price": 13000, "airline": "IndiGo",
                                         "via": ["MAA"]}, pause=0)
        box11 = []
        notify.run(c11, sender=box11.append)
        check("the alert names the airline and where it connects",
              "₹13,000 on IndiGo via MAA -- still a deal"
              in box11[0].get_body(preferencelist=("plain",)).get_content())

        print("\ndigest recency")
        c7.execute("UPDATE deal SET detected_at = ? WHERE price = 14000.0",
                   (at(30),))
        c7.commit()
        shown = [d["price"] for d in digest.deals_rows(c7)]
        check(f"a 30-day-old deal is not shown ({shown})", 14000.0 not in shown)
        check("today's is", 11900.0 in shown)

        print("\nscheduler")
        c5 = db.connect(str(Path(tmp) / "sched.db"))
        for d in ("DXB", "SIN", "BKK", "LHR"):
            c5.execute("INSERT INTO route (origin,destination) VALUES ('BLR',?)",
                       (d,))
        c5.commit()
        # Next month, not this one: a depart_date in the current month is
        # partly in the past, and distinct_quotes drops those as non-forward
        # prices -- which silently emptied every cell here.
        month = collect.months_ahead(2)[1]

        def stock(dest, n, price0=20000):
            """Give a cell n distinct quotes."""
            collect._insert(c5, [
                {**rows[0], "destination": dest, "price": float(price0 + i),
                 "depart_date": f"{month}-1{i % 9}", "depart_month": month,
                 "fetched_at": at(5)} for i in range(n)])

        stock("DXB", config.MIN_OBSERVATIONS + 4)   # mature
        stock("SIN", config.MIN_OBSERVATIONS - 1)   # one quote short
        stock("BKK", 2)                             # barely started
        # LHR left untouched

        chosen, why = schedule.plan(c5, budget=3)
        order = [c[1] for c in chosen if c[2] == month]
        check(f"mature cells are served first ({order})",
              order and order[0] == "DXB")
        check("then the cell closest to maturity, not the neediest",
              order[1] == "SIN")
        check("a cell at n=11 outranks one at n=2",
              order.index("SIN") < (order.index("BKK")
                                    if "BKK" in order else 99))
        check("the budget is not exceeded", why["planned"] <= 3)

        print("\nscheduler: the reserve keeps it from locking")
        c6 = db.connect(str(Path(tmp) / "lock.db"))
        for d in ("DXB", "SIN", "BKK", "LHR", "CDG", "DOH"):
            c6.execute("INSERT INTO route (origin,destination) VALUES ('BLR',?)",
                       (d,))
        c6.commit()
        # Every route mature except one, and a budget only big enough for
        # maintenance. Without a reserve the new cell is never opened.
        for d in ("DXB", "SIN", "BKK", "LHR", "CDG"):
            collect._insert(c6, [
                {**rows[0], "destination": d, "price": float(20000 + i),
                 "depart_date": f"{month}-1{i % 9}", "depart_month": month,
                 "fetched_at": at(5)}
                for i in range(config.MIN_OBSERVATIONS + 2)])
        chosen6, why6 = schedule.plan(c6, budget=3)
        # The property is that exploration keeps a slice, not that one named
        # destination wins the tie -- asserting the destination made this
        # fail the moment the sort key gained a popularity term.
        matured6 = schedule._maturity(c6)
        fresh = [c for c in chosen6
                 if matured6.get(c, 0) < config.MIN_OBSERVATIONS]
        check(f"an unexplored cell still gets a call "
              f"({why6['mature_due']} due, {why6['maintenance_deferred']} deferred)",
              len(fresh) >= 1)
        check("maintenance was capped, not cancelled",
              why6["planned"] - len(fresh) >= 1)

        print("\nscheduler: honest about starvation")
        _, why7 = schedule.plan(c6, budget=1)
        check(f"a starved budget is reported ({why7['starved']} cells)",
              why7["starved"] > 0)
        check("and nothing is silently dropped from the count",
              why7["planned"] + why7["starved"]
              >= why7["mature_due"] + why7["maturing"] + why7["untouched"]
              - why7["maintenance_deferred"])

        print("\nscheduler: the CLI seam")
        # The path a user actually invokes: plan -> run. Tested end to end
        # because nothing else checks that run() accepts what plan() emits.
        planned, _ = schedule.plan(c5, budget=2)
        walked = collect.run(c5, plan=planned, dry_run=True, pause=0)
        check(f"run consumes a plan verbatim ({walked['cells_planned']} cells)",
              walked["cells_planned"] == len(planned) == 2)
        check("and makes no calls while dry", walked["cells_fetched"] == 0)
        check("an empty plan is walked, not silently replaced by everything",
              collect.run(c5, plan=[], dry_run=True,
                          pause=0)["cells_planned"] == 0)

        print("\nbackup")
        # A WAL-mode DB whose rows are still only in the -wal file: a plain
        # file copy would lose them, the backup API must not.
        src = str(Path(tmp) / "live.db")
        live = db.connect(src)
        db.save_raw(live, "e", {}, 200, "2026-01-01T00:00:00Z", "{}")
        live.commit()
        bdir = Path(tmp) / "bk"
        from datetime import date
        for i in range(5):
            out = backup.backup(src, bdir, keep=3, today=date(2026, 1, 1 + i))
        snap = db.connect(str(out))
        check("snapshot carries rows still in the WAL",
              snap.execute("SELECT count(*) FROM raw_response").fetchone()[0] == 1)
        check("old snapshots pruned to keep", len(backup.snapshots(bdir)) == 3)
        check("pruned by date, so no folder listing is needed",
              [p.name for p in backup.snapshots(bdir)]
              == [f"faredrop-2026-01-0{i}.db" for i in (3, 4, 5)])
        check("no temp file left behind", not list(bdir.glob("*.tmp")))

        print("\nmissed-day alarm")
        from datetime import date as _date
        ch = db.connect(str(Path(tmp) / "health.db"))
        check("never collected is a problem", len(health.check(ch)) == 1)
        for day in ("2026-03-01", "2026-03-02", "2026-03-06"):
            db.save_raw(ch, collect.ENDPOINT, {}, 200, f"{day}T01:45:00+00:00",
                        "{}")
        db.save_raw(ch, "/v1/city-directions", {}, 200,
                    "2026-03-04T01:45:00+00:00", "{}")
        ch.commit()
        check("a normal day is healthy",
              health.check(ch, today=_date(2026, 3, 2)) == [])
        check("a day with nothing collected is flagged",
              any("no collection today" in p
                  for p in health.check(ch, today=_date(2026, 3, 3))))
        gap = health.check(ch, today=_date(2026, 3, 6))
        check(f"a gap is reported with its span ({gap})",
              gap == ["missed 3 day(s): 2026-03-03 to 2026-03-05 "
                      "-- that history is gone"])
        check("other endpoints don't count as collecting",
              "2026-03-04" not in health.collected_days(ch))
        db.save_raw(ch, collect.ENDPOINT, {}, 200,
                    "2026-03-07T01:45:00+00:00", "{}")
        ch.commit()
        check("and it is reported once: the next day is clean",
              health.check(ch, today=_date(2026, 3, 7)) == [])

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
