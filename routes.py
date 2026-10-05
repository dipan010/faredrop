"""Add the routes in routes.json to the route table. Add only.

The route table lives inside the database, and on GitHub Actions the
database lives in encrypted snapshots: editing routes on the laptop never
reaches it, and pulling GitHub's copy to edit and push back would race the
scheduled runs. So the route list is a file in the repo, and the workflow
runs this before collecting. Safe to run every time:

* a route already in the table is left exactly as it is, including one that
  was deliberately deactivated (domestic routes, airport codes replaced by
  city codes) -- this never re-activates or removes anything;
* added_at is stamped by the database, so health.py judges a new route only
  from the day it arrived.

    python3 routes.py            # add any routes not yet in the table
    python3 routes.py --dry-run
"""

import json
import sys
from pathlib import Path

import db

ROUTES_FILE = Path(__file__).with_name("routes.json")


def wanted(path=ROUTES_FILE):
    """[(origin, destination, rank)] from the file, in its order."""
    routes = json.loads(Path(path).read_text())["routes"]
    return [(o, d, rank) for o, dests in routes.items()
            for rank, d in enumerate(dests)]


def sync(conn, path=ROUTES_FILE, dry_run=False):
    have = {(r[0], r[1]) for r in
            conn.execute("SELECT origin, destination FROM route")}
    new = [w for w in wanted(path) if (w[0], w[1]) not in have]
    if not dry_run and new:
        conn.executemany(
            "INSERT OR IGNORE INTO route (origin, destination, popularity)"
            " VALUES (?,?,?)", new)
        conn.commit()
    return new


if __name__ == "__main__":
    dry = "--dry-run" in sys.argv
    added = sync(db.connect(), dry_run=dry)
    by_origin = {}
    for o, _, _ in added:
        by_origin[o] = by_origin.get(o, 0) + 1
    print(f"routes {'to add' if dry else 'added'}: {len(added)}"
          + (f" {by_origin}" if by_origin else ""))
