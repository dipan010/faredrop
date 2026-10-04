"""Notice, from the laptop, when the GitHub Actions collector has gone quiet.

The collector's own alarm (health.py) runs inside the same workflow, so it
can't report the workflow not running at all -- and GitHub stops scheduled
workflows in a public repo after 60 days without activity, silently. This
runs from the laptop's launchd job instead and reads the public list of
snapshots on the `data` release: no token, nothing written to GitHub. If the
newest snapshot is older than STALE_HOURS, it alerts (macOS notification and
email), once per UTC day.

    python3 watchdog.py
"""

import json
import sys
import urllib.error
import urllib.request
from datetime import datetime, timezone

import db
import dbstore
import health

REPO = "dipan010/faredrop"
# Four runs a day, so a healthy collector never leaves a gap this long.
STALE_HOURS = 30


def newest_snapshot_time(names):
    snaps = dbstore.newest_first(names)
    if not snaps:
        return None
    day, hhmm = dbstore.NAME.match(snaps[0]).groups()
    return datetime.strptime(f"{day}T{hhmm}", "%Y-%m-%dT%H%M") \
        .replace(tzinfo=timezone.utc)


def problem(names, now):
    """-> message, or None when the collector looks alive. Pure."""
    newest = newest_snapshot_time(names)
    if newest is None:
        return "GitHub Actions collector: no snapshots on the data release"
    hours = (now - newest).total_seconds() / 3600
    if hours > STALE_HOURS:
        return (f"GitHub Actions collector: newest snapshot is {hours:.0f}h "
                f"old ({newest:%Y-%m-%d %H:%M}Z) -- check the collect "
                "workflow is still enabled")
    return None


def release_assets():
    url = f"https://api.github.com/repos/{REPO}/releases/tags/{dbstore.TAG}"
    req = urllib.request.Request(url, headers={
        "Accept": "application/vnd.github+json",
        "User-Agent": "faredrop-watchdog"})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            return [a["name"] for a in json.load(resp).get("assets", [])]
    except urllib.error.HTTPError as exc:
        if exc.code == 404:
            return []
        raise


def main():
    now = datetime.now(timezone.utc)
    try:
        msg = problem(release_assets(), now)
    except Exception as exc:                # noqa: BLE001 - offline is not stale
        print(f"watchdog: couldn't reach GitHub ({exc}); not judging")
        return
    if not msg:
        print("watchdog: GitHub Actions collector is current")
        return
    print(f"watchdog: {msg}", file=sys.stderr)
    conn = db.connect()
    key = (now.date().isoformat(), "actions-stale", msg)
    reported = {(r[0], r[1]) for r in conn.execute("SELECT day, kind FROM alert")}
    if key[:2] in reported:
        return
    health.notify_mac(msg.replace('"', "'"))
    health.notify_mail([msg])
    health.mark(conn, [key])


if __name__ == "__main__":
    main()
