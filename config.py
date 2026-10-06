"""Configuration for the faredrop collector.

Everything here is meant to be edited by hand. The route list in particular
is just data -- widening from one origin to seven is a change to ORIGINS,
not a rewrite.
"""

import os

# --- credentials -------------------------------------------------------

# Get one at https://www.travelpayouts.com/developers/api
TOKEN = os.environ.get("TRAVEL_PAYOUTS_API_KEY", "")

# --- what we watch -----------------------------------------------------

ORIGINS = ["BLR"]          # <- change to your home airport

# Seeded by `python refdata.py destinations`, which asks the API which
# destinations are actually popular from each origin. Hand-edit freely.
DESTINATIONS_FILE = "data/destinations.json"

MAX_DESTINATIONS = 40

# Watched whatever the popularity feed says. /v1/city-directions reflects
# Aviasales' own user base -- it offers MOW and AER from BLR but not SIN or
# anywhere in Europe -- so the routes that matter to you go here by hand.
EXTRA_DESTINATIONS = {
    "BLR": ["SIN", "KUL",                      # SE Asia hubs, added 2026-10-02
            "LON", "PAR", "FRA", "AMS"],       # Europe, added 2026-10-02
}
# City codes (LON, PAR) rather than airports (LHR, CDG): the feed files most
# fares under the city, and Google Flights accepts both. Europe is thin in
# this feed -- on 2026-10-02 FRA and AMS had no fares in any month.

# How many departure months ahead to track. Each (route, month) pair is one
# cell of the price distribution we are building.
MONTHS_AHEAD = 6

CURRENCY = "inr"           # API default is RUB. Never omit this.

TRIP_CLASSES = {0: "economy", 1: "business", 2: "first"}

# --- quality bar -------------------------------------------------------
# The filters that make a deal worth surfacing rather than just cheap.

MAX_STOPS = 1              # Zomunk's bar: non-stop or one-stop only. Fares
                           # over it are never deals (detect.py skips them).

# Departure cities whose deals are emailed. Collection covers every origin in
# routes.json; deals elsewhere are still detected and shown by digest.py, but
# not sent. BLR plus nearby, chosen 2026-10-06.
ALERT_ORIGINS = {"BLR", "MAA", "COK", "HYD", "GOI"}
# Carriers we don't want to be alerted about, by IATA code.
AIRLINE_BLOCKLIST = set()

# Layover limits and transit-visa rules used to live here. They are gone, not
# postponed: /v1/prices/cheap returns a stop COUNT and nothing else about the
# routing -- no layover durations, no transit airports. A hub list that
# nothing can evaluate reads like a working safety check, which is worse than
# having none. The digest says so on every deal instead, and the README's
# limits section states it plainly.

# --- the price model ---------------------------------------------------
# What a route-month "normally" costs, conditioned on how far ahead you are
# booking. Fares 200 days out and 10 days out are not the same distribution,
# and pooling them makes the median a blend of two things and the threshold
# meaningless against either.

# Days-to-departure buckets, as (label, upper_bound_exclusive). Coarse on
# purpose: at roughly one quote per cell per day, a smooth booking curve is
# unfittable for months, whereas a bucket that never fills simply falls back
# to the route-level pool and costs nothing.
DTD_BUCKETS = [("last-minute", 14),
               ("near", 45),
               ("mid", 120),
               ("far", 10**6)]

# Shrinkage weight for the cross-route pooled offset: a bucket with m quotes
# behind it keeps m/(m+MIN_BUCKET_QUOTES) of its pooled estimate and is
# damped toward zero for the rest. Not a hard cutoff -- a threshold here
# makes the offset jump discontinuously as a bucket fills.
MIN_BUCKET_QUOTES = 30
# Shrinkage weight: a route's own bucket offset gets n/(n+k) of the say, the
# pooled cross-route offset the rest. Larger k = more pooling.
SHRINK_K = 40
# Floor on the robust log-scale, so a cell whose quotes happen to agree
# exactly cannot manufacture an infinite outlier score.
MIN_LOG_SCALE = 0.05

# --- detection ---------------------------------------------------------
# PLACEHOLDERS. These have never been fitted against real observations --
# there are none yet. They are exercised on synthetic data in simulate.py,
# which only shows the code degrades sanely when data is thin; it cannot
# tell you what the right number is. Revisit once history exists.

# A fare is a candidate if it lands below this fraction of the predicted
# price for its route-month and booking horizon.
DEAL_RATIO = 0.60
# ...and must also beat the prediction by this many rupees, so a cheap route
# doesn't spam the digest over a few hundred rupees of noise. This is the one
# gate that doesn't depend on a calibrated scale.
MIN_ABS_SAVING = 4000
# Outlier score below which a candidate is *ranked* as a possible mistake
# fare. A ranking heuristic, not a classifier -- see detect.py on why the
# left tail of a distribution of minima won't support a real one.
MISTAKE_Z = 3.5
# Only observations fetched within this many days are candidates. Without it
# detection re-walks the whole history every run and re-surfaces fares that
# were cheap months ago as if they were bookable today. expires_at does not
# cover this: it is frequently NULL, and whether it is populated at all
# depends on a field mapping that is still unverified.
DETECT_WINDOW_DAYS = 3

# Don't model a route-month until it has this many DISTINCT quotes. Not raw
# rows: the same fare reappears in the feed day after day, and counting the
# repeats would both overstate readiness and collapse the scale estimate.
MIN_OBSERVATIONS = 12

# ...and those quotes must come from at least this many different collection
# days. The calendar endpoint returns a whole month of departure dates in one
# call, so a single day can already hold 12+ distinct quotes. A "normal"
# built from one day is the spread across departure dates, and a deal against
# it only means "the cheapest date this month", not a price that dropped. That
# is exactly what fired on 2026-10-06 (GOI->SVX, every baseline one day old).
# A week of days makes it a history. A readiness rule, not a tuned threshold.
MIN_HISTORY_DAYS = 7

# --- the daily budget --------------------------------------------------
# ORIGINS x MAX_DESTINATIONS x MONTHS_AHEAD is 240 cells, so a uniform daily
# walk costs 240 calls. If that is more than the tier allows, the cheapest
# fix is fewer destinations -- MAX_DESTINATIONS is the same lever as a
# scheduler and far more legible. schedule.py only earns its place if you
# want all 40 routes watched on a budget that can't walk them.

# Calls per day. PLACEHOLDER: the free-tier rate limit is not known here.
# The scheduler is correct for any value; if the token comes back with a
# hard limit, this one constant changes.
DAILY_CALL_BUDGET = 240

# How often a matured cell is re-polled. Tied to DETECT_WINDOW_DAYS on
# purpose: a mature cell polled less often than the detection window is
# invisible to detect.run on the days in between. Raising this above the
# window buys budget by accepting deliberate blind spots -- which may be a
# fine trade, but it should be a choice and not a surprise.
MAINTENANCE_DAYS = 3

# Share of the daily budget that maintenance may never take. Without a floor
# the policy is absorbing: once enough cells mature, re-polling them consumes
# everything and no new cell is ever opened again. Observed directly in
# simulation -- at 3 calls/day the cohort locked at 9 cells while a plain
# round-robin reached 16.
EXPLORE_RESERVE = 0.34

# Distinct new quotes a single call is expected to yield. PLACEHOLDER, and
# only used to estimate how long maturity will take -- never to allocate.
# schedule.measured_yield() replaces it with the real figure as soon as
# there is enough history to measure one.
QUOTES_PER_CALL = 0.5

# --- alerting ----------------------------------------------------------
# A deal you find out about on Thursday for a fare that went on Monday is not
# a deal. Delivery is the difference between a pipeline and a product.

# The same itinerary will not alert again within this many days...
ALERT_SUPPRESS_DAYS = 7
# ...unless it has got at least this much cheaper since. A fare falling from
# 18k to 15k is news; the same 18k seen a third day running is not, and a
# channel that repeats itself is one you learn to ignore.
ALERT_IMPROVE_PCT = 0.10

# How far back the digest looks. Without it a great fare from March stays
# pinned to the top of the list forever.
DIGEST_WINDOW_DAYS = 7

# --- the live re-check -------------------------------------------------
# Before an alert goes out, verify.py looks the deal up on Google Flights and
# records the live price, standing in for the human who checks a candidate
# before it is published. It uses fast-flights, an unofficial scraper: free,
# against Google's terms, and liable to break or be blocked. So it is run
# gently, is never fatal, and a deal it could not check is still sent.

# Lookups per daily run, and the pause between them. Each pending deal is a
# lookup, so this caps the load on Google, not the number of deals.
VERIFY_MAX_PER_RUN = 10
VERIFY_PAUSE_SECONDS = 5
# A deal already re-checked within this many hours is not looked up again.
VERIFY_RECHECK_HOURS = 20
# Hold back deals the re-check says are gone. OFF until real deals show how
# often Google Flights and Travelpayouts disagree: the scraper returns
# Google's short "best" list, which may omit the cheapest fare, and an alert
# wrongly dropped is worse than one sent with a warning on it.
VERIFY_SUPPRESS_GONE = False

# SMTP, from the environment only -- never checked in. Put them in
# ~/.faredrop.env (chmod 600), which daily.sh sources; launchd inherits no
# shell environment of its own. Gmail needs an app-specific password.
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
ALERT_FROM = os.environ.get("ALERT_FROM", "") or SMTP_USER
ALERT_TO = os.environ.get("ALERT_TO", "")

DB_PATH = "data/faredrop.db"

# Daily DB snapshots (backup.py), kept for BACKUP_KEEP days in each folder.
# The second is iCloud Drive, so losing this laptop doesn't lose the history.
BACKUP_DIRS = [
    "backups",
    os.path.expanduser(
        "~/Library/Mobile Documents/com~apple~CloudDocs/faredrop-backups"),
]
BACKUP_KEEP = 14
RAW_DIR = "raw"
