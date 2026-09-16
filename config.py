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

# --- detection ---------------------------------------------------------

# A fare is a deal if it lands below this fraction of the route-month median.
DEAL_RATIO = 0.60
# ...and a mistake-fare candidate if it's this many MADs below the median.
MISTAKE_Z = 3.5
# Don't emit anything for a route-month until we have this many observations.
MIN_OBSERVATIONS = 12

DB_PATH = "data/faredrop.db"
RAW_DIR = "raw"
