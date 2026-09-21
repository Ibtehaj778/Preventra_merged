#!/usr/bin/env python3
"""
Denormalise each patient's weekly trend onto their worklist row.

WHY
---
/api/patients used to rebuild the whole picture on every request: read every
worklist row with no projection, aggregate the entire weekly_monitoring
collection, aggregate risk_registry, normalise all of it in Python, and only
then slice out the requested page. With 2,000 patients that took 27 seconds
against Atlas, and the dashboard rendered empty for all of it. The cost grew
with the cohort rather than with the page size, which is the wrong direction.

The trend summary changes only when the loader or the weekly simulator runs -
never between requests - so it belongs on the row rather than being recomputed.
This script writes it there and builds the indexes the endpoint queries on.

Run it after either of:
    python scripts/load_mimic_to_mongo.py
    python scripts/simulate_weekly_monitoring.py

It is idempotent: running it twice writes the same values.

FIELDS WRITTEN
--------------
    current_score       the latest weekly re-score, or the discharge score
    current_band        band of that score
    discharge_score     week 0
    trend_delta         current minus discharge, None with no weekly history
    monitoring_status   improving / stable / deteriorating / action_required
    weeks_tracked       how many points the series has
    summary_refreshed   when this row was last computed

Anything absent falls back inside the API, so a row this script has not reached
still renders - it simply shows the discharge score with no trend.
"""

from __future__ import annotations

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo import UpdateOne

load_dotenv()

# _classify_trend_status lives in the API so the badge on the worklist and the
# badge on the patient page can never disagree. Importing it here keeps one
# definition rather than a copy that drifts.
from api.main import (WEEKLY_COLLECTION, _classify_trend_status,  # noqa: E402
                      _worklist_driver, db, get_latest_batch_date)

# Sort keys. The worklist sorts by trend severity and by risk band, neither of
# which orders correctly as a string - "High" < "Low" < "Medium" alphabetically.
# Storing a rank makes both sortable in MongoDB with an index, which is what
# lets paging happen in the database instead of in the browser.
_STATUS_RANK = {"action_required": 4, "deteriorating": 3, "stable": 2,
                "improving": 1, "insufficient_data": 0}
_BAND_RANK = {"High": 3, "Medium": 2, "Low": 1}


def build_summaries() -> dict:
    """{patient_id: summary} from the weekly monitoring series."""
    pipeline = [
        {"$sort": {"week_number": 1}},
        {"$group": {
            "_id": "$patient_id",
            "scores": {"$push": "$risk_score"},
            "bands": {"$push": "$risk_band"},
            "groups": {"$push": "$clinical_group"},
        }},
    ]
    out = {}
    for doc in db[WEEKLY_COLLECTION].aggregate(pipeline):
        scores = []
        for raw in doc.get("scores", []):
            try:
                scores.append(float(raw))
            except (TypeError, ValueError):
                continue
        if len(scores) < 2:
            continue
        bands = doc.get("bands") or []
        gaps = [None] + [7] * (len(scores) - 1)
        out[str(doc["_id"])] = {
            "discharge_score": scores[0],
            "current_score": scores[-1],
            "current_band": bands[-1] if bands else None,
            "trend_delta": round(scores[-1] - scores[0], 1),
            "monitoring_status": _classify_trend_status(scores, gaps),
            "weeks_tracked": len(scores),
        }
    return out


def main() -> None:
    batch_date = get_latest_batch_date(db, "patient_worklist")
    print(f"batch date : {batch_date}")

    summaries = build_summaries()
    print(f"weekly series with 2+ points : {len(summaries):,}")

    rows = list(db["patient_worklist"].find(
        {"batch_date": batch_date},
        {"_id": 0, "patient_id": 1, "risk_score": 1, "risk_band": 1,
         "driver_1": 1, "driver_2": 1, "driver_3": 1}))
    print(f"worklist rows : {len(rows):,}")

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    ops, with_trend = [], 0
    for row in rows:
        pid = str(row.get("patient_id", ""))
        s = summaries.get(pid)
        if s:
            with_trend += 1
            fields = dict(s)
            if not fields.get("current_band"):
                fields["current_band"] = row.get("risk_band", "Low")
        else:
            # No weekly history: current IS the discharge score, and the status
            # says so rather than implying a flat trend was observed.
            score = float(row.get("risk_score", 0) or 0)
            fields = {
                "discharge_score": score,
                "current_score": score,
                "current_band": row.get("risk_band", "Low"),
                "trend_delta": None,
                "monitoring_status": "insufficient_data",
                "weeks_tracked": 1,
            }
        # The driver shown in the worklist column is a deterministic pick among
        # the patient's top three. Computing it here rather than per request
        # makes the column sortable in the database, and removes three driver
        # strings per row from the API payload.
        fields["primary_driver_label"] = _worklist_driver(pid, row)
        fields["status_rank"] = _STATUS_RANK.get(fields["monitoring_status"], 0)
        fields["band_rank"] = _BAND_RANK.get(fields.get("current_band"), 0)
        fields["summary_refreshed"] = now
        ops.append(UpdateOne({"patient_id": pid, "batch_date": batch_date},
                             {"$set": fields}))

    for i in range(0, len(ops), 1000):
        db["patient_worklist"].bulk_write(ops[i:i + 1000], ordered=False)
        print(f"  {min(i + 1000, len(ops)):>6,} / {len(ops):,}")

    print(f"\n  {with_trend:,} rows carry a real weekly trend, "
          f"{len(ops) - with_trend:,} fall back to the discharge score")

    # Indexes for the queries /api/patients actually issues: newest batch,
    # sorted by current score, optionally filtered by condition or band.
    print("\nensuring indexes ...")
    for spec in (
        [("batch_date", 1), ("current_score", -1)],
        [("batch_date", 1), ("clinical_group", 1)],
        # Multikey - one entry per condition the patient has, so selecting
        # several conditions at once is still an index scan.
        [("batch_date", 1), ("clinical_groups", 1)],
        [("batch_date", 1), ("current_band", 1)],
        [("batch_date", 1), ("monitoring_status", 1)],
        [("batch_date", 1), ("status_rank", -1)],
        [("batch_date", 1), ("band_rank", -1)],
        [("batch_date", 1), ("trend_delta", -1)],
        [("batch_date", 1), ("discharge_date", -1)],
        [("batch_date", 1), ("primary_diagnosis", 1)],
        [("patient_id", 1)],
    ):
        name = db["patient_worklist"].create_index(spec)
        print(f"  {name}")

    print("\ndone")


if __name__ == "__main__":
    main()
