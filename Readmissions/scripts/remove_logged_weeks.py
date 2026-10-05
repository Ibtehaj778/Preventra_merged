"""
List, and optionally remove, weekly monitoring weeks that did NOT come from the
simulator - weeks logged through the patient portal (source "patient_reported")
or anything else that is not "simulated".

WHY
---
scripts/simulate_weekly_monitoring.py replaces only the weeks it wrote itself
(source "simulated"). A patient-logged week survives every regeneration and is
appended after the new weeks, so a 4-week demo shows weeks 5 and 6. Those weeks
also keep the score they were given when they were logged, worked out from the
OLD weeks, and they record only what the logging form asked - so a red flag the
form never asked about (new confusion, say) silently disappears and the score
drops.

The current code has no endpoint that writes such weeks; the ones in the
database came from earlier testing. This script shows them, then removes them
when asked:

    .venv/bin/python scripts/remove_logged_weeks.py            # list only
    .venv/bin/python scripts/remove_logged_weeks.py --delete   # remove them

Run scripts/refresh_worklist_summary.py afterwards so the worklist's current
score and "weeks monitored" match the remaining weeks.
"""
from __future__ import annotations

import argparse
import os
import sys
from collections import defaultdict

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from api.db_utils import get_db_name, get_mongo_client

COLLECTION = "weekly_monitoring"
SIMULATED = "simulated"


def logged_weeks(db) -> list:
    """Every weekly document the simulator did not write, oldest week first."""
    return list(db[COLLECTION].find(
        {"source": {"$ne": SIMULATED}},
        {"patient_id": 1, "week_number": 1, "week_date": 1, "source": 1, "risk_score": 1},
    ).sort([("patient_id", 1), ("week_number", 1)]))


def remove(db, docs: list) -> int:
    if not docs:
        return 0
    return db[COLLECTION].delete_many({"_id": {"$in": [d["_id"] for d in docs]}}).deleted_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    parser.add_argument("--delete", action="store_true", help="remove them (default: list only)")
    args = parser.parse_args()
    load_dotenv()
    db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))[get_db_name()]

    docs = logged_weeks(db)
    by_patient = defaultdict(list)
    for d in docs:
        by_patient[str(d["patient_id"])].append(d)
    print(f"  {len(docs)} non-simulated weeks across {len(by_patient)} patients")
    for pid, weeks in by_patient.items():
        detail = ", ".join(f"week {w.get('week_number')} ({w.get('week_date') or 'no date'}, "
                           f"{w.get('source') or 'no source'}, {w.get('risk_score')}%)" for w in weeks)
        print(f"    {pid}: {detail}")

    if not args.delete:
        print("  Listed only. Run again with --delete to remove them.")
        return
    print(f"  Removed {remove(db, docs)} weeks. Now run scripts/refresh_worklist_summary.py.")


if __name__ == "__main__":
    main()
