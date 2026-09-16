# faredrop

A free, self-hosted version of the Zomunk model: watch international
round-trips out of one origin, learn what each route normally costs, and
surface the fares that fall well below that.

Teardown of the original: https://claude.ai/code/artifact/942f3281-fbfb-4c44-9515-972c46587f17

## The one thing to understand

**The price history is the product.** No API will sell you the distribution
of what a route normally costs -- you accumulate it by polling. Travelpayouts
retains data for only 7 days, so any day the collector isn't running is a day
of history gone permanently.

That inverts the usual build order. The collector ships first; the dashboard,
the filters and the alerts get built while it accumulates.

## Setup

1. Get a free token at https://www.travelpayouts.com/developers/api
2. `export TRAVELPAYOUTS_TOKEN=your_token_here`
3. Set your home airport in `config.py` (`ORIGINS`)

```sh
python3 refdata.py sync           # reference tables (no token needed)
python3 probe.py BLR DXB          # dump raw payloads, inspect ./raw/
python3 refdata.py destinations   # seed the route list from real demand
python3 collect.py --limit 3      # smoke test, then check the field mapping:
python3 collect.py --show-keys    # <- do this before trusting any number
```

**Confirm the parser once.** `collect._parse` is the only place API field
names appear, and it was written against the documented shape, not an
observed one. `--show-keys` prints what actually came back; fix the mapping
there if it disagrees. Nothing is lost while it's wrong -- raw payloads are
committed before parsing, so `python3 collect.py --reparse` replays a
corrected parser over everything already stored. It's idempotent: each
payload is reparsed with the timestamp saved next to it, so re-running adds
nothing.

## Daily

```sh
python3 collect.py                # walk routes, write observations
python3 baseline.py               # recompute distributions
python3 detect.py                 # flag drops + mistake-fare candidates
python3 digest.py                 # what's worth looking at today
```

## Files

| File | Role |
|---|---|
| `config.py` | Routes, quality bar, thresholds. Hand-edited. |
| `api.py` | Travelpayouts client. https, INR, gzip, raw persistence. |
| `db.py` | Schema. Raw payloads kept verbatim. |
| `refdata.py` | Airport/airline tables; seeds the route list. |
| `probe.py` | Dumps every candidate endpoint for inspection. |
| `collect.py` | The daily walk. The only thing that must not miss a day. |
| `baseline.py` | Rolling p10/p50/MAD per route-month. |
| `detect.py` | Flags fares below the baseline. |
| `digest.py` | The review queue -- deals plus how ready the data is. |
| `test_pipeline.py` | Token-free checks of parse -> baseline -> detect. |

## Known limits, stated honestly

- Each observation is the cheapest fare *users found* in a ~48h window, not a
  spot fare. The baseline is a median-of-minima -- a consistent yardstick for
  "cheaper than usual", not the market average. Don't quote it as one.
- **Checked-bag inclusion is not in this feed.** Neither is enough routing
  detail to decide transit visas. Every deal carries a flag saying so; verify
  before booking.
- Quiet routes get sampled less, so absence of a deal is not evidence of no
  deal.

- An expired quote is not bookable, so `detect.py` won't offer it -- but it
  still counts as history in `baseline.py`. Filtering expiry out of the
  baseline would discard each observation days after recording it, and no
  route would ever reach `MIN_OBSERVATIONS`.
