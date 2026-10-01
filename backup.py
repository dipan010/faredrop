"""Snapshot the database, so a bad write or a stray rm can't take the history.

The history is the one thing here that can't be refetched (the API keeps 7
days), so it gets a dated copy every day. sqlite3's online backup API is used
rather than a file copy: the DB is in WAL mode, and copying faredrop.db alone
would miss whatever is still sitting in the -wal file.

Local copies guard against corruption and mistakes, not against losing the
disk. Point BACKUP_DIR somewhere off-machine for that.

    python3 backup.py            # snapshot today, prune old ones
    python3 backup.py --list
"""

import sqlite3
import sys
from datetime import date
from pathlib import Path

import config

BACKUP_DIR = Path(getattr(config, "BACKUP_DIR", "backups"))
KEEP = getattr(config, "BACKUP_KEEP", 14)


def snapshots(d=BACKUP_DIR):
    return sorted(d.glob("faredrop-*.db"))


def backup(src=config.DB_PATH, dest_dir=BACKUP_DIR, keep=KEEP, today=None):
    if not Path(src).exists():
        print(f"no database at {src} -- nothing to back up", file=sys.stderr)
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    dest = dest_dir / f"faredrop-{(today or date.today()).isoformat()}.db"
    tmp = dest.with_suffix(".db.tmp")
    # Write to a temp name and rename, so a crash mid-backup never leaves a
    # truncated file wearing a valid snapshot's name.
    with sqlite3.connect(src) as s, sqlite3.connect(tmp) as d:
        s.backup(d)
    tmp.replace(dest)
    for old in snapshots(dest_dir)[:-keep]:
        old.unlink()
    return dest


def main():
    if "--list" in sys.argv:
        for p in snapshots():
            print(f"{p}  {p.stat().st_size:,} bytes")
        return
    dest = backup()
    if dest:
        print(f"backed up to {dest} (keeping {KEEP})")


if __name__ == "__main__":
    main()
