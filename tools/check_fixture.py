"""Validate a product snapshot (docs/fixtures/snapshot.sample.json by default)
against the contract in docs/lld.md.

Everything it checks is read from docs/lld.md itself, so the check can't drift
from the contract:
- the keys of the section 3 JSON example (top level, pipeline, deal, route price);
- the NOT NULL columns of the D1 `deals` table (section 4);
- the export allowlist (section 2.2) and the status values (section 2.3).

It also checks deal_id format, saving = usual - price, saving_pct, that every
group_id names a deal in the snapshot, and the status rules against the
snapshot's own generated_at.

Failures listed in KNOWN_GAPS are reported but don't fail the run: each one is a
gap in docs/ui-spec.md section 7 that only real data (phase 3) can close.

    python3 tools/check_fixture.py [path]
"""
import json
import re
import sys
from datetime import datetime, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
LLD = ROOT / "docs" / "lld.md"
DEFAULT = ROOT / "docs" / "fixtures" / "snapshot.sample.json"

# (deal_id, field) -> gap id in docs/ui-spec.md section 7.
KNOWN_GAPS = {
    ("GOI-DXB-2026-11-01-2026-11-15", "stops"): "G35",
}


def lld_contract(text):
    sec3 = text.split("## 3. Snapshot contract", 1)[1].split("## 4.", 1)[0]
    example = json.loads(re.search(r"```json\n(.*?)\n```", sec3, re.S).group(1))
    table = re.search(r"CREATE TABLE deals \((.*?)\n\);", text, re.S).group(1)
    not_null = set()
    for part in re.split(r",\s*(?![^()]*\))", re.sub(r"--[^\n]*", "", table)):
        m = re.match(r"\s*(\w+)\s+\w+.*NOT NULL", part, re.S)
        if m:
            not_null.add(m.group(1))
    # Multi-column lines ("origin TEXT NOT NULL, destination TEXT NOT NULL, ...")
    for name, rest in re.findall(r"(\w+)\s+(?:TEXT|INTEGER|REAL)([^,\n]*)", table):
        if "NOT NULL" in rest:
            not_null.add(name)
    origins = set(re.findall(r'"(\w{3})"', re.search(r"EXPORT_ORIGINS = \{(.*?)\}", text, re.S).group(1)))
    dests = set(re.findall(r'"(\w{3})"', re.search(r"EXPORT_DESTINATIONS = \{(.*?)\}", text, re.S).group(1)))
    statuses = set(re.findall(r"^\| `(\w+)` \|", text.split("### 2.3", 1)[1].split("###", 1)[0], re.M))
    return example, not_null, origins, dests, statuses


def ts(s):
    return datetime.strptime(s, "%Y-%m-%dT%H:%M:%SZ")


def check(snap, contract):
    example, not_null, origins, dests, statuses = contract
    errors, known = [], []

    def fail(msg, key=None):
        (known if key in KNOWN_GAPS else errors).append(
            msg + (f"  [known gap {KNOWN_GAPS[key]}]" if key in KNOWN_GAPS else ""))

    def same_keys(where, got, want):
        if set(got) != set(want):
            fail(f"{where}: keys differ from lld §3: missing {sorted(set(want) - set(got))}, "
                 f"extra {sorted(set(got) - set(want))}")

    same_keys("snapshot", snap, example)
    same_keys("pipeline", snap.get("pipeline", {}), example["pipeline"])
    now = ts(snap["generated_at"])
    today = now.date().isoformat()
    ids = {d["deal_id"] for d in snap["deals"]}
    for d in snap["deals"]:
        did = d.get("deal_id", "?")
        same_keys(did, d, example["deals"][0])
        nulls = set()
        for col in sorted(not_null - {"region", "first_price", "updated_run"}):
            # region, first_price and updated_run are set by the Worker on ingest.
            if d.get(col) is None:
                nulls.add(col)
                fail(f"{did}: {col} is missing or null but NOT NULL in D1 deals", (did, col))
        if nulls & {"origin", "destination", "depart_date", "return_date", "price", "nights",
                    "status", "checked_at", "group_id"}:
            continue  # the remaining checks need these fields
        want_id = f"{d['origin']}-{d['destination']}-{d['depart_date']}-{d['return_date']}"
        if did != want_id:
            fail(f"{did}: deal_id should be {want_id}")
        if d["group_id"] not in ids:
            fail(f"{did}: group_id {d['group_id']} is not a deal in the snapshot")
        if d["origin"] not in origins or d["destination"] not in dests:
            fail(f"{did}: route outside the export allowlist")
        if d["status"] not in statuses:
            fail(f"{did}: status {d['status']} not in {sorted(statuses)}")
        if d.get("usual") is not None:
            if d["saving"] != d["usual"] - d["price"]:
                fail(f"{did}: saving {d['saving']} != usual - price")
            if abs(d["saving_pct"] - (1 - d["price"] / d["usual"]) * 100) > 0.05:
                fail(f"{did}: saving_pct {d['saving_pct']} disagrees with price/usual")
        nights = (datetime.fromisoformat(d["return_date"]) - datetime.fromisoformat(d["depart_date"])).days
        if nights != d["nights"]:
            fail(f"{did}: nights {d['nights']} but dates give {nights}")
        if (d.get("range_low") is None) != (d.get("range_high") is None):
            fail(f"{did}: range_low and range_high must both be set or both null")
        if d.get("stops") is not None and d.get("via") is not None and len(d["via"]) > d["stops"]:
            fail(f"{did}: more via airports than stops")
        # lld §2.3 status rules, judged at generated_at.
        old = now - ts(d["checked_at"]) > timedelta(hours=72)
        want = "ended" if d["depart_date"] <= today else ("stale" if old else "live")
        if d["status"] != want and not (d["status"] == "ended" and want != "ended"):
            fail(f"{did}: status {d['status']} but lld §2.3 rules give {want}")
    for r in snap["route_prices"]:
        same_keys("route_prices", r, example["route_prices"][0])
    return errors, known


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT
    snap = json.loads(path.read_text())
    errors, known = check(snap, lld_contract(LLD.read_text()))
    for k in known:
        print("KNOWN ", k)
    for e in errors:
        print("FAIL  ", e)
    print(f"{len(snap['deals'])} deals, {len(errors)} failures, {len(known)} known gaps")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
