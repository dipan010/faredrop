"""Google Flights' calendar (price graph), read by a headless browser.

An experiment from 2026-11-14, the user's call. Since 2026-08 Google answers
its calendar requests (GetCalendarGraph, GetCalendarPicker) only when they
carry a header the page's own JavaScript makes, so fast-flights cannot get
them. A real browser running the page does: tools/calendar_probe.py showed
one opened price graph returns ~60 departure dates, one price each, for the
trip length on the page (BLR->SGN's cheapest matched a deal the normal
pipeline had confirmed to the rupee).

This module only finds dates. It never decides a deal: gfcollect.py looks the
cheapest dates up the normal way (reason 'calendar'), and the usual judge,
later-run confirmation, Travelpayouts cross-check and email rules apply.

* The raw calendar response is stored (gf_cal_raw) before it is parsed into
  gf_cal_price, so a parser fix can replay it.
* It has its own small cap (GF_CAL_ROUTES_PER_RUN), apart from the daily
  judge/confirm budget, and is deliberately narrow: one trip length, one view
  of ~60 departure dates about 4-12 weeks out, routes in rotation.
* Anything going wrong ends the scan quietly: the pipeline carries on
  without it. It may stop working any day if Google changes the page.

    python3 src/gfcalendar.py            # GitHub Actions: calendar.yml
"""

import json
import random
import re
import sys
import time
import zlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import config
import db
import gfcollect

CALENDAR_RPC = re.compile(r"GetCalendar(Graph|Picker)")


def parse(text):
    """[(depart, return, price)] from a calendar response, or [] if none.

    The body is Google's batchexecute framing: ")]}'", then lines holding
    [["wrb.fr", rpc, "<json string>", ...], ...]. The payload's [1] is a list
    of [depart, return, [[null, price], token], flag]. Unpriced dates and
    anything unexpected are skipped, never raised: Google's layout is the one
    fragile thing here, and it lives only in this function.
    """
    out = []
    for line in (text or "").splitlines():
        if not line.startswith("[["):
            continue
        try:
            entries = json.loads(line)
        except ValueError:
            continue
        for e in entries:
            try:
                if e[0] != "wrb.fr" or not e[2]:
                    continue
                items = json.loads(e[2])[1]
            except (IndexError, TypeError, ValueError):
                continue
            for it in items if isinstance(items, list) else []:
                try:
                    price = it[2][0][1]
                    if price:
                        out.append((it[0], it[1], float(price)))
                except (IndexError, TypeError, ValueError):
                    continue
    return out


def due(conn, routes, today, n, rng=None):
    """Routes to scan this run: never-scanned first, then least recently,
    skipping routes Google prices nothing for."""
    rng = rng or random.Random()
    last = {(r[0], r[1]): r[2] for r in conn.execute(
        "SELECT origin, destination, max(fetched_at) FROM gf_cal_raw"
        " GROUP BY 1, 2")}
    live = [r for r in routes if r not in gfcollect.dead_routes(conn, today)]
    return sorted(live, key=lambda r: (last.get(r, ""), rng.random()))[:n]


def store(conn, route, nights, anchor, text, now):
    """Raw first, then the parsed dates. Returns the number of dates."""
    rows = parse(text)
    cur = conn.execute(
        "INSERT INTO gf_cal_raw (origin, destination, nights, anchor_date,"
        " fetched_at, ok, body) VALUES (?,?,?,?,?,?,?)",
        (*route, nights, anchor, now, 1 if rows else 0,
         zlib.compress((text or "").encode()) if text else None))
    conn.executemany(
        "INSERT INTO gf_cal_price (raw_id, origin, destination, depart_date,"
        " return_date, price, fetched_at) VALUES (?,?,?,?,?,?,?)",
        [(cur.lastrowid, *route, d, r, p, now) for d, r, p in rows])
    conn.commit()
    return len(rows)


def browse(page, route, depart, ret):
    """Open the results page and its price graph; the calendar response
    text, or None. Picker as a fallback: both carry the same per-date list."""
    from fast_flights import FlightQuery, Passengers, create_query
    q = create_query(
        flights=[FlightQuery(date=depart, from_airport=route[0],
                             to_airport=route[1]),
                 FlightQuery(date=ret, from_airport=route[1],
                             to_airport=route[0])],
        trip="round-trip", passengers=Passengers(adults=1), currency="INR",
        language="en", max_stops=config.MAX_STOPS)
    got = []

    def keep(resp):
        if CALENDAR_RPC.search(resp.url):
            try:
                got.append(resp.text())
            except Exception:             # noqa: BLE001 - unreadable body
                pass

    page.on("response", keep)
    try:
        page.goto(q.url(), wait_until="networkidle", timeout=60000)
        for find in (lambda: page.get_by_role(
                         "button", name=re.compile("Price graph", re.I)),
                     lambda: page.locator('input[aria-label*="Departure"]')):
            loc = find()
            if loc.count():
                loc.first.click(timeout=5000)
                page.wait_for_timeout(5000)
            if any(parse(t) for t in got):
                break
            page.keyboard.press("Escape")
    finally:
        page.remove_listener("response", keep)
    best = max(got, key=lambda t: len(parse(t)), default=None)
    return best


def run(conn, today=None, fetch=None, rng=None, pause=None, routes=None):
    """One scan. `fetch(route, depart, ret)` -> response text is injectable
    for tests; by default a headless Chrome does it."""
    today = today or datetime.now(timezone.utc).date()
    rng = rng or random.Random()
    pause = config.GF_CAL_PAUSE_SECONDS if pause is None else pause
    routes = routes if routes is not None else gfcollect.watched()
    todo = due(conn, routes, today, config.GF_CAL_ROUTES_PER_RUN, rng)
    depart = today + timedelta(days=config.GF_CAL_ANCHOR_DAYS)
    ret = depart + timedelta(days=config.GF_CAL_NIGHTS)
    stats = {"scanned": 0, "with_dates": 0, "dates": 0, "status": "ok"}
    browser = pw = None
    try:
        if fetch is None:
            from playwright.sync_api import sync_playwright
            pw = sync_playwright().start()
            browser = pw.chromium.launch(headless=True)
            page = browser.new_context(locale="en-US").new_page()

            def fetch(route, d, r):
                return browse(page, route, d, r)
        for i, route in enumerate(todo):
            if i and pause:
                time.sleep(pause * rng.uniform(0.75, 1.25))
            now = datetime.now(timezone.utc).isoformat(timespec="seconds")
            try:
                text = fetch(route, depart.isoformat(), ret.isoformat())
            except Exception as exc:      # noqa: BLE001 - record, go on
                print(f"  {route[0]}->{route[1]}: {type(exc).__name__}",
                      file=sys.stderr)
                text = None
            n = store(conn, route, config.GF_CAL_NIGHTS, depart.isoformat(),
                      text, now)
            stats["scanned"] += 1
            stats["with_dates"] += 1 if n else 0
            stats["dates"] += n
    except Exception as exc:              # noqa: BLE001 - never fatal
        stats["status"] = f"stopped: {type(exc).__name__}: {exc}"[:200]
    finally:
        if browser is not None:
            browser.close()
        if pw is not None:
            pw.stop()
    return stats


def leads(conn, routes, today, n):
    """Calendar dates worth a normal lookup, best first: the cheapest unseen
    date of each route's freshest scan, if it is at most GF_CAL_LEAD_RATIO of
    that scan's median and departs within GF_HORIZON_DAYS."""
    since = (today - timedelta(days=config.GF_CAL_FRESH_DAYS)).isoformat()
    lo, hi = config.GF_HORIZON_DAYS
    first = (today + timedelta(days=lo)).isoformat()
    last = (today + timedelta(days=hi)).isoformat()
    seen = gfcollect._recently_seen(conn, today)
    wanted = set(routes) - gfcollect.dead_routes(conn, today)
    picks = []
    for o, d, raw_id in conn.execute(
            "SELECT origin, destination, max(id) FROM gf_cal_raw"
            " WHERE ok = 1 AND substr(fetched_at, 1, 10) >= ?"
            " GROUP BY 1, 2", (since,)):
        if (o, d) not in wanted:
            continue
        rows = conn.execute(
            "SELECT depart_date, return_date, price FROM gf_cal_price"
            " WHERE raw_id = ?", (raw_id,)).fetchall()
        prices = sorted(r[2] for r in rows)
        if len(prices) < 10:
            continue
        median = prices[len(prices) // 2]
        best = min((r for r in rows if first <= r[0] <= last
                    and (o, d, r[0], r[1]) not in seen),
                   key=lambda r: r[2], default=None)
        if best and best[2] <= median * config.GF_CAL_LEAD_RATIO:
            picks.append((best[2] / median, (o, d, best[0], best[1])))
    picks.sort()
    return [p[1] for p in picks[:n]]


if __name__ == "__main__":
    conn = db.connect()
    res = run(conn)
    for k, v in res.items():
        print(f"  {k:12} {v}")
    # Same marker gf.yml uses: store a snapshot only if this run added rows.
    marker = Path(config.DB_PATH).with_name(".gf_changed")
    if res["scanned"]:
        marker.write_text("1")
    else:
        marker.unlink(missing_ok=True)
