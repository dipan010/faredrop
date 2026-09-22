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
| `schedule.py` | Where the daily call budget goes, when it can't cover everything. |
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

Only fares fetched within `DETECT_WINDOW_DAYS` are candidates. A fare that
was cheap in March is history, not something anyone can book, and without
that bound every run re-walks the whole table and re-serves it as today's
deal. It still counts toward the baseline -- it just isn't offered.

`kind='mistake'` means "look at this one first". Every price in the feed is a
minimum over a ~48h search window, and the left tail of a distribution of
minima is not the tail the score's arithmetic assumes. Logs fix the skew, not
that.

**The thresholds are placeholders.** They have never been fitted -- there are
no observations yet. `simulate.py` shows the code degrades sanely on sparse
input; it cannot tell you the right numbers, because measuring precision on a
generator the model is built to invert proves only that it inverts it.

## Spending a limited budget

40 destinations x 6 months is 240 cells, so a uniform daily walk costs 240
calls. If that's more than your tier allows, **watch fewer destinations
first** -- `MAX_DESTINATIONS` is the same lever as a scheduler and much
easier to reason about.

If you want all 40 watched anyway, `collect.py --scheduled` allocates a fixed
budget instead. The argument is a threshold effect: below `MIN_OBSERVATIONS`
a cell has no baseline, so it can produce no deal at any price. 240 cells at
n=6 are worth zero; 40 at n=12 are worth everything. So mature cells are
served first, and whatever's left goes to the cells *closest* to maturity
rather than the neediest -- finishing a cell at n=11 buys a working baseline,
starting a fifth at n=0 buys nothing.

Measured against a plain round-robin, 24 cells over 30 days:

| calls/day | round-robin matures | cohort matures |
|---:|---:|---:|
| 1 | 0 | 3 |
| 2 | 0 | 9 |
| 3 | 16 | 16 |
| 4 | 24 | 18 |
| 6 | 24 | 24 |
| 12 | 24 (360 calls) | 24 (271 calls) |

**Read this table for its shape, not its numbers.** Every figure in it falls
out of `simulate.py`'s invented yield -- three quotes per call, each lingering
one to four days. Change that and the crossover moves. What the table
establishes is that *two regimes exist* and which one you are in depends on
whether the budget can mature every cell; it does not establish that 3
calls/day is anyone's crossover. `python3 schedule.py` computes the boundary
from your own history once there is any.

Only one regime wants a scheduler. When the budget can't mature everything,
round-robin matures *nothing* -- every cell stalls just short of the line --
and cohorting is the difference between a working system and no system. When
the budget is comfortable, round-robin is as good and simpler; at 12/day the
only gain is a quarter of the calls back. `python3 schedule.py` tells you
which regime you're in. `collect.py` still walks uniformly by default.

One thing that had to be fixed to make this work at all: capping maintenance.
Left uncapped the policy is absorbing -- once enough cells mature, re-polling
them eats the whole budget and no new cell is ever opened again. That showed
up in simulation as the cohort locking at 9 cells while round-robin reached
16. `EXPLORE_RESERVE` is the floor that prevents it.

## Running it daily

Collection is the only step that can't be caught up later, so it shouldn't
depend on you remembering. `daily.sh` runs collect -> baseline -> detect ->
digest; the launchd job runs it at 07:15.

```sh
echo 'export TRAVELPAYOUTS_TOKEN=...' > ~/.faredrop.env && chmod 600 ~/.faredrop.env
cp com.dipanghosh.faredrop.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.dipanghosh.faredrop.plist
```

launchd rather than cron for one reason: if the laptop is asleep at 07:15,
launchd runs the job on wake, whereas cron drops it. A dropped day is history
that can't be recovered.

The token lives in `~/.faredrop.env` because launchd starts with a near-empty
environment and won't inherit a shell export. Without it `daily.sh` exits 78
(`EX_CONFIG`) so launchd doesn't thrash-retry.

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
