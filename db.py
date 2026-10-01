"""SQLite schema and helpers.

Design notes that matter:

* `fetched_at` is OUR clock and is the real observation timestamp. The API's
  `found_at` is when an Aviasales user happened to find that fare, which can
  be up to 48h stale -- using it as the observation date smears the history.
* Every price row is a *minimum over a 48h search window*, not a spot fare.
  So the baseline we compute is a median-of-minima. It is internally
  consistent and useful for spotting drops; it is NOT the same number Google
  Flights or Zomunk would call "normal". Don't present it as such.
* Raw payloads are kept verbatim in `raw_response` so a parser bug never
  costs us data we can't refetch (the API only retains 7 days).
"""

import json
import sqlite3
from pathlib import Path

import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS route (
    origin       TEXT NOT NULL,
    destination  TEXT NOT NULL,
    active       INTEGER NOT NULL DEFAULT 1,
    popularity   INTEGER,
    added_at     TEXT NOT NULL DEFAULT (datetime('now')),
    PRIMARY KEY (origin, destination)
);

CREATE TABLE IF NOT EXISTS fare_observation (
    id            INTEGER PRIMARY KEY,
    origin        TEXT NOT NULL,
    destination   TEXT NOT NULL,
    depart_date   TEXT,
    return_date   TEXT,
    depart_month  TEXT NOT NULL,
    trip_class    INTEGER NOT NULL DEFAULT 0,
    stops         INTEGER,
    price         REAL NOT NULL,
    currency      TEXT NOT NULL,
    airline       TEXT,
    flight_number TEXT,
    duration      INTEGER,
    distance      INTEGER,
    found_at      TEXT,
    expires_at    TEXT,
    actual        INTEGER,
    fetched_at    TEXT NOT NULL,
    source        TEXT NOT NULL,
    UNIQUE (origin, destination, depart_date, return_date,
            trip_class, stops, price, fetched_at)
);

CREATE INDEX IF NOT EXISTS idx_obs_routemonth
    ON fare_observation (origin, destination, depart_month, trip_class);
CREATE INDEX IF NOT EXISTS idx_obs_fetched
    ON fare_observation (fetched_at);

CREATE TABLE IF NOT EXISTS raw_response (
    id          INTEGER PRIMARY KEY,
    endpoint    TEXT NOT NULL,
    params      TEXT NOT NULL,
    status      INTEGER,
    fetched_at  TEXT NOT NULL,
    body        TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS baseline (
    origin       TEXT NOT NULL,
    destination  TEXT NOT NULL,
    depart_month TEXT NOT NULL,
    trip_class   INTEGER NOT NULL,
    n            INTEGER NOT NULL,   -- DISTINCT quotes, not rows
    n_raw        INTEGER,            -- rows they were collapsed from
    p10          REAL,
    p50          REAL,
    mad          REAL,
    -- The model proper lives in log space: prices are right-skewed and
    -- multiplicative, so a 20% drop is the same distance on every route.
    p50_log      REAL,               -- median log price at the reference horizon
    log_scale    REAL,               -- robust (MAD) spread of log residuals
    lowest_seen  REAL,
    computed_at  TEXT NOT NULL,
    PRIMARY KEY (origin, destination, depart_month, trip_class)
);

-- How much a booking horizon moves the price, in log space, relative to the
-- route's own reference level. Estimated per route where there is enough
-- data and shrunk toward the cross-route pooled value where there isn't.
CREATE TABLE IF NOT EXISTS bucket_offset (
    origin       TEXT NOT NULL,
    destination  TEXT NOT NULL,
    trip_class   INTEGER NOT NULL,
    bucket       TEXT NOT NULL,
    offset_log   REAL NOT NULL,
    n            INTEGER NOT NULL,
    pooled_from  INTEGER NOT NULL,   -- quotes behind the cross-route value
    computed_at  TEXT NOT NULL,
    PRIMARY KEY (origin, destination, trip_class, bucket)
);

CREATE TABLE IF NOT EXISTS deal (
    id            INTEGER PRIMARY KEY,
    observation_id INTEGER NOT NULL REFERENCES fare_observation(id),
    origin        TEXT NOT NULL,
    destination   TEXT NOT NULL,
    depart_date   TEXT,
    return_date   TEXT,
    trip_class    INTEGER NOT NULL,
    price         REAL NOT NULL,
    baseline_p50  REAL NOT NULL,   -- predicted for THIS booking horizon
    discount_pct  REAL NOT NULL,
    abs_saving    REAL,
    dtd           INTEGER,         -- days to departure when we saw it
    dtd_bucket    TEXT,
    outlier_z     REAL,            -- how far into the left tail; ranking only
    kind          TEXT NOT NULL,   -- 'drop' | 'mistake'
    flags         TEXT,            -- JSON list of quality warnings
    -- The itinerary's identity, price deliberately excluded: the same trip
    -- seen again is the same deal, and only a materially cheaper price for
    -- it is new information.
    fingerprint   TEXT,
    detected_at   TEXT NOT NULL,
    notified_at   TEXT,             -- stamped only on a SUCCESSFUL send
    gf_price      REAL,             -- live Google Flights price at re-check
    gf_status     TEXT,             -- 'still' | 'gone' | 'skipped' | 'error'
    gf_airline    TEXT,
    gf_via        TEXT,             -- connecting airports, '' = non-stop
    gf_checked_at TEXT,
    reviewed      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (observation_id)
);
"""


# Columns added after the first databases were created. CREATE TABLE IF NOT
# EXISTS won't add them, and the price history is the one thing we can't
# refetch -- so we widen in place rather than asking anyone to start over.
MIGRATIONS = [
    ("baseline", "n_raw", "INTEGER"),
    ("baseline", "p50_log", "REAL"),
    ("baseline", "log_scale", "REAL"),
    ("deal", "abs_saving", "REAL"),
    ("deal", "dtd", "INTEGER"),
    ("deal", "dtd_bucket", "TEXT"),
    ("deal", "outlier_z", "REAL"),
    ("deal", "fingerprint", "TEXT"),
    ("deal", "notified_at", "TEXT"),
    ("deal", "gf_price", "REAL"),
    ("deal", "gf_status", "TEXT"),
    ("deal", "gf_checked_at", "TEXT"),
    ("deal", "gf_airline", "TEXT"),
    ("deal", "gf_via", "TEXT"),
]


# Indexes over migrated columns. These cannot live in SCHEMA: executescript
# runs before the ALTERs, so on an existing database the column they index
# does not exist yet.
POST_MIGRATION_INDEXES = """
CREATE INDEX IF NOT EXISTS idx_deal_fingerprint ON deal (fingerprint, detected_at);
CREATE INDEX IF NOT EXISTS idx_deal_unnotified  ON deal (notified_at);
"""


def migrate(conn):
    for table, column, decl in MIGRATIONS:
        existing = {r["name"] for r in
                    conn.execute(f"PRAGMA table_info({table})")}
        if existing and column not in existing:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")
    conn.executescript(POST_MIGRATION_INDEXES)
    conn.commit()


def connect(path=None):
    path = path or config.DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
    migrate(conn)
    return conn


def save_raw(conn, endpoint, params, status, fetched_at, body):
    """Keep the verbatim payload. Cheap insurance -- the API only holds 7 days."""
    safe = {k: v for k, v in params.items() if k != "token"}
    conn.execute(
        "INSERT INTO raw_response (endpoint, params, status, fetched_at, body)"
        " VALUES (?,?,?,?,?)",
        (endpoint, json.dumps(safe, sort_keys=True), status, fetched_at, body),
    )


def counts(conn):
    q = lambda sql: conn.execute(sql).fetchone()[0]
    return {
        "routes": q("SELECT count(*) FROM route WHERE active=1"),
        "observations": q("SELECT count(*) FROM fare_observation"),
        "route_months": q(
            "SELECT count(*) FROM (SELECT 1 FROM fare_observation"
            " GROUP BY origin,destination,depart_month,trip_class)"
        ),
        "baselines": q("SELECT count(*) FROM baseline"),
        "deals": q("SELECT count(*) FROM deal"),
        "first_observation": conn.execute(
            "SELECT min(fetched_at) FROM fare_observation"
        ).fetchone()[0],
    }


if __name__ == "__main__":
    conn = connect()
    print(f"schema ready at {config.DB_PATH}")
    for k, v in counts(conn).items():
        print(f"  {k:18} {v}")
