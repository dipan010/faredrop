"""Snapshot the database, so a bad write or a stray rm can't take the history.

The history is the one thing here that can't be refetched (the API keeps 7
days), so it gets a dated copy every day. sqlite3's online backup API is used
rather than a file copy: the DB is in WAL mode, and copying faredrop.db alone
would miss whatever is still sitting in the -wal file.

Copies go to every folder in config.BACKUP_DIRS: one on this disk, against
corruption and mistakes, and one in iCloud Drive, against losing the disk.

Old snapshots are pruned by name, never by listing the folder. Under launchd,
macOS lets the job write into iCloud Drive but not list it, and a listing
that fails comes back empty without complaint -- pruning that way would
silently never happen and the folder would grow forever.

macOS also ties each iCloud file to the program that made it: the daily job
can replace and delete its own snapshots, but not one made by a manual run
or a test (seen 2026-10-02: "Operation not permitted"). So a snapshot that
can't be replaced is saved under a fallback name, and one that can't be
pruned is reported and left, rather than failing the backup.

    python3 backup.py            # snapshot today, prune old ones
    python3 backup.py --list
"""

import os
import sqlite3
import sys
from datetime import date, timedelta
from pathlib import Path

import config

DIRS = [Path(d) for d in getattr(config, "BACKUP_DIRS", ["backups"])]
KEEP = getattr(config, "BACKUP_KEEP", 14)
# How far past KEEP pruning looks for stragglers, e.g. after the job was off
# for a while. Beyond this, an old snapshot is simply left alone.
PRUNE_REACH = 90


def name(day):
    return f"faredrop-{day.isoformat()}.db"


def snapshots(d):
    return sorted(Path(d).glob("faredrop-*.db"))


def backup(src=config.DB_PATH, dest_dir=DIRS[0], keep=KEEP, today=None):
    if not Path(src).exists():
        print(f"no database at {src} -- nothing to back up", file=sys.stderr)
        return None
    today = today or date.today()
    dest_dir = Path(dest_dir)
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / name(today)
    # A per-run temp name, renamed into place, so a crash mid-backup never
    # leaves a truncated file wearing a valid snapshot's name, and a leftover
    # temp from an earlier failure can't get in the way.
    tmp = dest_dir / f".{dest.name}.{os.getpid()}.tmp"
    s, d = sqlite3.connect(src), sqlite3.connect(tmp)
    try:
        s.backup(d)
        # One self-contained file: a WAL-mode copy grows -wal/-shm files
        # beside it the first time anyone opens it.
        d.execute("PRAGMA journal_mode=DELETE")
    finally:
        d.close()
        s.close()
    # Some SQLite builds (3.54, the system python3 launchd runs) leave an empty
    # -shm behind even after the switch out of WAL. It holds nothing now.
    for side in ("-wal", "-shm"):
        try:
            Path(f"{tmp}{side}").unlink(missing_ok=True)
        except OSError:                     # cosmetic; never fail on it
            pass
    try:
        os.replace(tmp, dest)
    except PermissionError:
        fallback = dest.with_name(f"{dest.stem}-{os.getpid()}.db")
        os.replace(tmp, fallback)
        print(f"{dest} is not ours to replace; saved as {fallback.name}",
              file=sys.stderr)
        dest = fallback
    for age in range(keep, keep + PRUNE_REACH):
        old = dest_dir / name(today - timedelta(days=age))
        try:
            old.unlink(missing_ok=True)
        except PermissionError:
            print(f"can't prune {old} (made by another program); left it",
                  file=sys.stderr)
    return dest


def main():
    if "--list" in sys.argv:
        for d in DIRS:
            for p in snapshots(d):
                print(f"{p}  {p.stat().st_size:,} bytes")
        return
    failed = 0
    for d in DIRS:
        # Each copy stands alone: iCloud being unavailable must not cost the
        # local snapshot, and vice versa.
        try:
            dest = backup(dest_dir=d)
            if dest:
                print(f"backed up to {dest} (keeping {KEEP})")
        except Exception as exc:            # noqa: BLE001 - report, carry on
            failed += 1
            print(f"backup to {d} failed: {exc}", file=sys.stderr)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
