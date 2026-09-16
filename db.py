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
    n            INTEGER NOT NULL,
    p10          REAL,
    p50          REAL,
    mad          REAL,
    lowest_seen  REAL,
    computed_at  TEXT NOT NULL,
    PRIMARY KEY (origin, destination, depart_month, trip_class)
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
    baseline_p50  REAL NOT NULL,
    discount_pct  REAL NOT NULL,
    kind          TEXT NOT NULL,   -- 'drop' | 'mistake'
    flags         TEXT,            -- JSON list of quality warnings
    detected_at   TEXT NOT NULL,
    reviewed      INTEGER NOT NULL DEFAULT 0,
    UNIQUE (observation_id)
);
"""


def connect(path=None):
    path = path or config.DB_PATH
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    conn.executescript(SCHEMA)
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
