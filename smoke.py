"""One live call, to prove the key works and the parser still fits the API.

test_pipeline.py is token-free by design, so nothing else notices if the key
is revoked or the response shape drifts. This makes a single request on a
busy route, parses it with the collector's own parser, and fails loudly if
either breaks. It writes nothing: no database, no raw file.

    python3 smoke.py
"""

import sys

import api
import collect
import config

ROUTE = ("BLR", "DXB")


def main():
    if not config.TOKEN:
        sys.exit("TRAVEL_PAYOUTS_API_KEY is not set")
    origin, dest = ROUTE
    rows = []
    for month in collect.months_ahead(3):
        payload, fetched_at = api.get(
            collect.ENDPOINT,
            {"origin": origin, "destination": dest, "depart_date": month})
        if payload.get("success") is not True:
            # The error text never contains the key: it travels in a header.
            sys.exit(f"API refused the request: {str(payload)[:200]}")
        rows += collect._parse(payload, origin, dest, fetched_at)
    if not rows:
        sys.exit(f"key accepted, but no fares parsed for {origin}->{dest} "
                 "in 3 months -- the response shape may have changed")
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
