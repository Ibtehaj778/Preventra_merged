"""
Re-band every stored score against docs/band_thresholds_mimic.json.

WHY THIS EXISTS
---------------
The band a patient is in is denormalised onto several collections so the
worklist can filter and sort on an index. Change the thresholds and those
stored strings are stale until something rewrites them - and a stale band is
worse than no band, because the number and the label on screen disagree.

Run after editing the thresholds file, then run refresh_worklist_summary.py so
current_band and band_rank follow.

    .venv/bin/python scripts/apply_risk_bands.py

Idempotent: re-running it changes nothing.
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo import UpdateOne

from api.db_utils import get_mongo_client

THRESHOLDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                          "docs", "band_thresholds_mimic.json")
BATCH = 2000

# (collection, score field, band field)
TARGETS = [
    ("patient_worklist",  "risk_score",    "risk_band"),
    ("patient_worklist",  "current_score", "current_band"),
    ("weekly_monitoring", "risk_score",    "risk_band"),
    ("risk_registry",     "risk_score",    "risk_band"),
]


def band_of(score: float, low: float, high: float) -> str:
    if score >= high:
        return "High"
    if score >= low:
        return "Medium"
    return "Low"


def main() -> None:
    load_dotenv()
    t = json.load(open(THRESHOLDS))
    low, high = float(t["low_score_threshold"]), float(t["high_score_threshold"])
    print(f"  Low < {low}%   Medium {low}-{high}%   High >= {high}%\n")

    db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))["neuroshield"]

    for coll, score_field, band_field in TARGETS:
        rows = list(db[coll].find({score_field: {"$exists": True, "$ne": None}},
                                  {"_id": 1, score_field: 1, band_field: 1}))
        ops, moved, tally = [], Counter(), Counter()
        for r in rows:
            try:
                want = band_of(float(r[score_field]), low, high)
            except (TypeError, ValueError):
                continue
            tally[want] += 1
            if r.get(band_field) != want:
                moved[(r.get(band_field), want)] += 1
                ops.append(UpdateOne({"_id": r["_id"]}, {"$set": {band_field: want}}))

        for i in range(0, len(ops), BATCH):
            db[coll].bulk_write(ops[i:i + BATCH], ordered=False)

        print(f"  {coll}.{band_field}: {len(rows):,} scored, {len(ops):,} rebanded")
        print(f"     now  " + "  ".join(f"{b} {tally.get(b, 0):,}" for b in ("High", "Medium", "Low")))
        for (was, now), n in moved.most_common(4):
            print(f"     {str(was):>7} -> {now:<7} {n:,}")
        print()

    # ---- executive_summary ------------------------------------------------
    # The header counts and the worklist filter disagreed even before the
    # thresholds changed: the summary was computed from the DISCHARGE band at
    # load time, while the worklist filters on the patient's CURRENT band. Two
    # numbers for "how many are high risk" on one screen is a bug regardless of
    # where the thresholds sit, so both now read current_band.
    print("  executive_summary:")
    for doc in db["executive_summary"].find({}, {"_id": 1, "batch_date": 1}):
        bd = doc.get("batch_date")
        rows = list(db["patient_worklist"].find(
            {"batch_date": bd}, {"current_band": 1, "risk_band": 1, "_id": 0}))
        if not rows:
            print(f"     {bd}: no worklist rows, left as it was")
            continue
        c = Counter((r.get("current_band") or r.get("risk_band") or "Low") for r in rows)
        total = len(rows)
        db["executive_summary"].update_one({"_id": doc["_id"]}, {"$set": {
            "total_patients": total,
            "high_count": c.get("High", 0),
            "medium_count": c.get("Medium", 0),
            "low_count": c.get("Low", 0),
            "pct_high": round(100 * c.get("High", 0) / total, 2) if total else 0.0,
        }})
        print(f"     {bd}: {total:,} patients — High {c.get('High',0):,} "
              f"Medium {c.get('Medium',0):,} Low {c.get('Low',0):,}")

    print("\ndone - now run scripts/refresh_worklist_summary.py")


if __name__ == "__main__":
    main()
