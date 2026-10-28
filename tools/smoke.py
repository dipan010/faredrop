"""One live call, to prove the key works and the parser still fits the API.

test_pipeline.py is token-free by design, so nothing else notices if the key
is revoked or the response shape drifts. This makes a single request on a
busy route, parses it with the collector's own parser, and fails loudly if
either breaks. It writes nothing: no database, no raw file.

    python3 tools/smoke.py
"""

import sys  # noqa: E402 - the pipeline's modules live in src/
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import sys

import api
import collect
import config

ROUTE = ("BLR", "DXB")


def main():
    if not config.TOKEN:
        sys.exit("TRAVEL_PAYOUTS_API_KEY is not set")
    origin, dest = ROUTE

    def fetch(endpoint, params):
        payload, fetched_at = api.get(endpoint, params)
        if payload.get("success") is not True:
            # The error text never contains the key: it travels in a header.
            sys.exit(f"API refused the request: {str(payload)[:200]}")
        return collect._parse(payload, origin, dest, fetched_at, source=endpoint)

    # The calendar is where most fares come from (~1,900 a day), so it is the
    # test. /cheap is thin (1-3 BLR->DXB fares a day in Oct 2026) and came back
    # empty for 3 months on 2026-10-26, failing CI while collection was fine;
    # an empty /cheap is now a warning, not a failure.
    rows = fetch(*collect._request(origin, dest, collect.CALENDAR))
    if not rows:
        sys.exit(f"key accepted, but no calendar fares parsed for {origin}->"
                 f"{dest} -- the response shape may have changed")
    cheap = []
    for month in collect.months_ahead(3):
        cheap += fetch(*collect._request(origin, dest, month))
    if not cheap:
        print(f"warning: /cheap returned no {origin}->{dest} fares in 3 months"
              " (thin cache; not a failure)")
    rows += cheap
    bad = [r for r in rows if r["stops"] is None or not r["return_date"]]
    if bad:
        sys.exit(f"{len(bad)} fare(s) parsed without stops or a return date")
    for r in rows:
        print(f"  {r['origin']}->{r['destination']} {r['depart_date']}"
              f" -> {r['return_date']}  ₹{r['price']:,.0f}"
              f"  {r['stops']} stop(s)  {r['airline']}")
    print(f"smoke: key accepted, {len(rows)} fare(s) parsed")


if __name__ == "__main__":
    main()
