"""Experiment: can a real (headless) browser read Google Flights' calendar prices?

Since 2026-08 Google's calendar RPC (GetCalendarGraph) only answers requests
carrying a header that the page's own JavaScript produces, so a plain HTTP
client like fast-flights gets nothing back. A browser running that page does
produce it. This probe opens the ordinary results page for a few trips in
headless Chrome, opens the date picker and the price graph the way a person
would, and saves every Google Flights data response the page loads, plus a
screenshot. It writes nothing to the database and sends no email: phase 1 is
only "what does the page give us", read by hand afterwards.

Runs on GitHub Actions (calendar-probe.yml), never on the laptop:

    python3 tools/calendar_probe.py OUT_DIR
"""

import sys  # noqa: E402 - the pipeline's modules live in src/
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import json
import re
import time

from fast_flights import FlightQuery, Passengers, create_query
from playwright.sync_api import sync_playwright

# Three trips: a busy short-haul, a deal route, and a new long-haul.
TRIPS = [("BLR", "SGN", "2027-02-10", "2027-02-17"),
         ("GOI", "CMB", "2027-01-07", "2027-01-14"),
         ("DEL", "NYC", "2027-01-20", "2027-02-03")]
# Only Google Flights' own data calls; nothing else on the page is kept.
DATA = re.compile(r"FlightsFrontendService|batchexecute|GetCalendar", re.I)
PAUSE = 20                       # seconds between trips; a person's pace


def url(origin, dest, depart, ret):
    q = create_query(
        flights=[FlightQuery(date=depart, from_airport=origin, to_airport=dest),
                 FlightQuery(date=ret, from_airport=dest, to_airport=origin)],
        trip="round-trip", passengers=Passengers(adults=1), currency="INR",
        language="en", max_stops=1)
    return q.url()


def try_click(page, label, *candidates):
    """Click the first locator that exists; report which, or that none did."""
    last = f"{label}: not found"
    for make in candidates:
        try:
            loc = make()
            if loc.count():
                loc.first.click(timeout=5000)
                page.wait_for_timeout(5000)
                return f"{label}: clicked"
        except Exception as exc:          # noqa: BLE001 - an experiment: record, go on
            last = f"{label}: {type(exc).__name__}"
    return last


def probe(page, trip, out):
    name = "-".join(trip[:3])
    seen = []

    def keep(resp):
        if DATA.search(resp.url):
            try:
                body = resp.text()
            except Exception:             # noqa: BLE001 - some bodies are unreadable
                body = None
            seen.append({"url": resp.url.split("?")[0], "status": resp.status,
                         "rpc": re.findall(r"rpcids=([\w,]+)", resp.url),
                         "bytes": len(body or ""), "body": body})

    page.on("response", keep)
    steps = []
    page.goto(url(*trip), wait_until="networkidle", timeout=60000)
    steps.append(f"landed: {page.url[:80]}")
    if "consent." in page.url:
        steps.append(try_click(page, "consent",
                               lambda: page.get_by_role("button", name=re.compile("Reject all", re.I))))
        page.wait_for_load_state("networkidle")
    steps.append(try_click(page, "date picker",
                           lambda: page.locator('input[aria-label*="Departure"]'),
                           lambda: page.get_by_role("textbox", name=re.compile("Departure", re.I))))
    page.screenshot(path=str(out / f"{name}-picker.png"))
    page.keyboard.press("Escape")
    steps.append(try_click(page, "price graph",
                           lambda: page.get_by_role("button", name=re.compile("Price graph", re.I)),
                           lambda: page.get_by_text(re.compile("Price graph", re.I))))
    page.screenshot(path=str(out / f"{name}-graph.png"))
    steps.append(try_click(page, "date grid",
                           lambda: page.get_by_role("button", name=re.compile("Date grid", re.I)),
                           lambda: page.get_by_text(re.compile("Date grid", re.I))))
    page.screenshot(path=str(out / f"{name}-grid.png"))
    page.remove_listener("response", keep)
    (out / f"{name}.json").write_text(json.dumps(
        {"trip": trip, "steps": steps, "responses": seen}, indent=1))
    return name, steps, [(r["rpc"], r["status"], r["bytes"]) for r in seen]


def main():
    out = Path(sys.argv[1] if len(sys.argv) > 1 else "calendar_out")
    out.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_context(locale="en-US").new_page()
        for i, trip in enumerate(TRIPS):
            if i:
                time.sleep(PAUSE)
            try:
                name, steps, calls = probe(page, trip, out)
                print(name, *steps, sep="\n  ")
                for c in calls:
                    print("   ", c)
            except Exception as exc:      # noqa: BLE001 - keep probing the others
                print("-".join(trip[:3]), "FAILED", type(exc).__name__, str(exc)[:200])
        browser.close()


if __name__ == "__main__":
    main()
