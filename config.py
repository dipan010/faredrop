"""Configuration for the faredrop collector.

Everything here is meant to be edited by hand. The route list in particular
is just data -- widening from one origin to seven is a change to ORIGINS,
not a rewrite.
"""

import os

# --- credentials -------------------------------------------------------

# Get one at https://www.travelpayouts.com/developers/api
TOKEN = os.environ.get("TRAVELPAYOUTS_TOKEN", "")

# --- what we watch -----------------------------------------------------

ORIGINS = ["BLR"]          # <- change to your home airport

# Seeded by `python refdata.py destinations`, which asks the API which
# destinations are actually popular from each origin. Hand-edit freely.
DESTINATIONS_FILE = "data/destinations.json"

MAX_DESTINATIONS = 40

# How many departure months ahead to track. Each (route, month) pair is one
# cell of the price distribution we are building.
MONTHS_AHEAD = 6

CURRENCY = "inr"           # API default is RUB. Never omit this.

TRIP_CLASSES = {0: "economy", 1: "business", 2: "first"}

# --- quality bar -------------------------------------------------------
# The filters that make a deal worth surfacing rather than just cheap.

MAX_STOPS = 1              # Zomunk's bar: non-stop or one-stop only
MIN_LAYOVER_MIN = 60
MAX_LAYOVER_MIN = 300      # 5h; beyond this it stops being a good deal

# Carriers we don't want to be alerted about, by IATA code.
AIRLINE_BLOCKLIST = set()

# Hubs an Indian passport can transit airside without a visa, for the
# routings we actually see. Not a subsystem -- nationality is fixed and the
# hub set is small. Anything not listed here gets flagged for manual check.
VISA_FREE_TRANSIT_HUBS = {
    "DOH", "DXB", "AUH", "SHJ",       # Gulf
    "IST", "SAW",                      # Turkey (airside)
    "SIN", "KUL", "BKK", "HKG",        # SE/E Asia airside
    "ADD", "NBO",                      # Africa airside
    "CMB", "KTM", "MLE",               # subcontinent
}
# Hubs that require a transit visa for an Indian passport in common
# configurations -- these disqualify an itinerary outright.
VISA_REQUIRED_TRANSIT_HUBS = {
    "LHR", "LGW", "MAN",               # UK: DATV applies to Indian nationals
    "CDG", "FRA", "MUC", "AMS", "ZRH", # Schengen: airside usually OK but
                                       # terminal changes are not -- treat as
                                       # needs-check rather than safe
    "ICN", "CAN", "PVG", "PEK",
}

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
# Don't model a route-month until it has this many DISTINCT quotes. Not raw
# rows: the same fare reappears in the feed day after day, and counting the
# repeats would both overstate readiness and collapse the scale estimate.
MIN_OBSERVATIONS = 12

DB_PATH = "data/faredrop.db"
RAW_DIR = "raw"
