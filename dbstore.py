"""Keep the price history on GitHub, encrypted, for the Actions collector.

The scheduled workflow runs on a fresh machine every time, so the database
has to come from somewhere and go back afterwards. It lives as dated,
encrypted snapshots attached to a prerelease tagged `data` in this repo:

* **Encrypted** (AES-256, key in FAREDROP_DB_KEY) because the repo is public
  and the history is Travelpayouts' data, not ours to republish.
* **A new asset per run, never overwritten.** Replacing an asset deletes the
  old one first, so a failed upload would leave nothing. Old ones are pruned
  after the new one is safely up.
* **Never from scratch.** db.connect() would quietly create an empty database
  if the file were missing, and the next upload would replace months of
  history with it. So `pull` fails the job unless a snapshot decrypts and
  passes an integrity check, and `push` refuses a database smaller than the
  one pulled.

The key travels as an environment variable (openssl -pass env:...), never on
a command line, where other processes could read it.

    python3 dbstore.py pull           # newest usable snapshot -> data/faredrop.db
    python3 dbstore.py push           # data/faredrop.db -> new snapshot, prune
    python3 dbstore.py push --seed    # first upload: no pull to compare against
    python3 dbstore.py latest         # name of the newest snapshot
"""

import os
import re
import sqlite3
import subprocess
import sys
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import config

TAG = "data"
KEY_ENV = "FAREDROP_DB_KEY"
PULLED = Path("data/.pulled_responses")   # row count at pull, for push's guard
NAME = re.compile(r"^faredrop-(\d{4}-\d{2}-\d{2})T(\d{4})Z-[\w-]+\.db\.enc$")
# How many recent snapshots pull will fall back through if the newest is bad.
FALLBACK = 3
# Pruning: every snapshot from the last day is kept, then the newest per day
# for KEEP_DAYS days.
KEEP_DAYS = 14
CIPHER = ["-aes-256-cbc", "-pbkdf2", "-iter", "200000"]


def snapshot_name(now=None, run=None):
    now = now or datetime.now(timezone.utc)
    run = run or os.environ.get("GITHUB_RUN_ID", "local")
    return f"faredrop-{now:%Y-%m-%dT%H%M}Z-{run}.db.enc"


def newest_first(names):
    return sorted((n for n in names if NAME.match(n)), reverse=True)


def to_prune(names, today):
    """Snapshot names safe to delete. Pure, so it can be tested."""
    keep, seen_days = set(), set()
    for n in newest_first(names):
        day = date.fromisoformat(NAME.match(n).group(1))
        age = (today - day).days
        if age <= 1:
            keep.add(n)                     # today and yesterday: all of them
        elif age <= KEEP_DAYS and day not in seen_days:
            keep.add(n)                     # older: newest of each day
        seen_days.add(day)
    snaps = newest_first(names)
    keep.update(snaps[:FALLBACK])           # never prune below the fallbacks
    return [n for n in snaps if n not in keep]


def gh(*args, capture=True):
    return subprocess.run(["gh", *args], check=True, text=True,
                          capture_output=capture).stdout


def assets():
    out = gh("release", "view", TAG, "--json", "assets",
             "-q", ".assets[].name")
    return out.split()


def openssl(*args):
    if not os.environ.get(KEY_ENV):
        sys.exit(f"{KEY_ENV} is not set")
    subprocess.run(["openssl", "enc", *args, *CIPHER,
                    "-pass", f"env:{KEY_ENV}"], check=True)


def responses(path):
    """Row count of raw_response, after an integrity check. Raises if bad."""
    conn = sqlite3.connect(path)
    try:
        ok = conn.execute("PRAGMA integrity_check").fetchone()[0]
        if ok != "ok":
            raise RuntimeError(f"integrity check failed: {ok}")
        return conn.execute("SELECT count(*) FROM raw_response").fetchone()[0]
    finally:
        conn.close()


def pull():
    names = newest_first(assets())
    if not names:
        sys.exit("FATAL: no snapshots on the data release -- refusing to "
                 "start from an empty database (seed it with push --seed)")
    dest = Path(config.DB_PATH)
    dest.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        for name in names[:FALLBACK]:
            try:
                gh("release", "download", TAG, "-p", name, "-D", tmp)
                plain = Path(tmp) / "plain.db"
                openssl("-d", "-in", str(Path(tmp) / name), "-out", str(plain))
                n = responses(plain)
            except Exception as exc:        # noqa: BLE001 - try the next one
                print(f"snapshot {name} unusable: {exc}", file=sys.stderr)
                continue
            os.replace(plain, dest)
            PULLED.write_text(str(n))
            print(f"restored {name}: {n} responses")
            return name
    sys.exit("FATAL: none of the newest snapshots could be restored")


def push(seed=False):
    src = Path(config.DB_PATH)
    n = responses(src)
    if not seed:
        if not PULLED.exists():
            sys.exit("FATAL: nothing was pulled this run; refusing to upload")
        before = int(PULLED.read_text())
        if n < before:
            sys.exit(f"FATAL: database shrank ({before} -> {n} responses); "
                     "refusing to upload")
    name = snapshot_name()
    with tempfile.TemporaryDirectory() as tmp:
        # A self-contained copy: the live file may still have pages in -wal.
        flat = Path(tmp) / "flat.db"
        s, d = sqlite3.connect(src), sqlite3.connect(flat)
        try:
            s.backup(d)
            d.execute("PRAGMA journal_mode=DELETE")
        finally:
            d.close()
            s.close()
        out = Path(tmp) / name
        openssl("-salt", "-in", str(flat), "-out", str(out))
        gh("release", "upload", TAG, str(out))
    print(f"stored {name}: {n} responses")
    gone = to_prune(assets(), datetime.now(timezone.utc).date())
    for old in gone:
        try:
            gh("release", "delete-asset", TAG, old, "-y")
        except subprocess.CalledProcessError as exc:
            print(f"couldn't prune {old}: {exc}", file=sys.stderr)
    if gone:
        print(f"pruned {len(gone)} old snapshot(s)")


def latest():
    names = newest_first(assets())
    print(names[0] if names else "")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "pull":
        pull()
    elif cmd == "push":
        push(seed="--seed" in sys.argv)
    elif cmd == "latest":
        latest()
    else:
        sys.exit(__doc__)
