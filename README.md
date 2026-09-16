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
| `baseline.py` | The price model: distinct quotes, booking horizon, log space. |
| `detect.py` | Flags fares below the baseline. |
| `digest.py` | The review queue -- deals plus how ready the data is. |
| `simulate.py` | Synthetic history, for exercising the model with no data. |
| `test_pipeline.py` | Token-free checks of parse -> baseline -> detect. |

## How a deal is decided

Everything hinges on predicting what a route-month *should* cost, then asking
how far below it a fare sits.

**Count distinct quotes, not rows.** The feed repeats the same fare day after
day, so thirty rows can be four fares. Counting the repeats overstates how
much history exists and collapses the spread estimate -- which is the exact
number the outlier score divides by. Rows stay verbatim as the audit trail;
they are collapsed on read, in `baseline.distinct_quotes`.

**Condition on how far ahead you are booking.** A fare 200 days out and one
10 days out are different distributions; pooled, the median is a blend and a
fixed ratio is wrong against both. Four coarse buckets, not a fitted curve --
at roughly one quote per cell per day a smooth booking curve is unfittable
for months, whereas a bucket that never fills falls back to the route's own
level and costs nothing.

**Work in log space.** Fares are right-skewed and move multiplicatively. In
logs, "20% below normal" is one distance on a ₹15k route and a ₹150k one, so
a single threshold serves both.

    log price  =  route level  +  horizon offset  +  cell offset  +  residual

A route's horizon offset is trusted in proportion to the data behind it --
`n/(n+k)` of the say, the rest from that bucket pooled across all routes,
itself damped toward zero by the same rule. Both shrinkages bias the offset
low, so the horizon is deliberately *under*-corrected: fewer false deals, at
the cost of missing some real last-minute ones.

Then three gates, and they are not equally trustworthy:

| Gate | What it is |
|---|---|
| Ratio | Below `DEAL_RATIO` of prediction. Scale-free. |
| Absolute saving | At least `MIN_ABS_SAVING` below it. The only gate that needs no calibrated scale. |
| Outlier score | How far into the left tail, in robust log units. **Ranks, does not classify.** |

`kind='mistake'` means "look at this one first". Every price in the feed is a
minimum over a ~48h search window, and the left tail of a distribution of
minima is not the tail the score's arithmetic assumes. Logs fix the skew, not
that.

**The thresholds are placeholders.** They have never been fitted -- there are
no observations yet. `simulate.py` shows the code degrades sanely on sparse
input; it cannot tell you the right numbers, because measuring precision on a
generator the model is built to invert proves only that it inverts it.

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
- Sustained drops get absorbed. A genuine fare war becomes the new normal
  within a few weeks and stops flagging. That is the correct behaviour for
  "cheaper than usual" and the wrong one for "cheap in absolute terms" --
  `MIN_ABS_SAVING` is the only thing pushing back, and it is a blunt one.
- A thin route-month produces no baseline rather than a guessed one. Pooling
  it toward the route's other months (seasonality with shrinkage) is the
  right next step; the decomposition has the slot, but three levels of
  shrinkage cannot be checked against zero observations.
