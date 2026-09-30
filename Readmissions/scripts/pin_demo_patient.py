"""
Pin one demo patient's weekly monitoring series to fixed readings.

MIMIC-10683325 is the patient the red-flag change was made for: hepatitis C
with hepatic coma, acute kidney failure, ascites and bipolar disorder. The demo
walks through their four weeks as they were first generated - the same
readings and the same wording on every card - so only the risk each week moves
is changed:

    week   before          now             why
    1      83.2  (+25.7)   83.2  (+25.7)   unchanged
    2      87.4  (+4.2)    87.4  (+4.2)    unchanged
    3      89.9  (+2.5)    89.9  (+2.5)    unchanged
    4      81.2  (-8.7)    96.0  (+6.1)    the regimen has stopped and saturation
                                           is 85% - a red flag, so the score
                                           cannot fall and the week is
                                           "Action required"

Weeks 1-3 are the original scores. Week 4 is what models/monitoring_rules
gives today for the same readings (every condition counted, red flag applied).

The readings are the simulator's own for this patient (seed 42, 4 weeks), so
nothing on the cards is invented here. Run AFTER simulate_weekly_monitoring.py
(which rewrites every simulated week) and BEFORE refresh_worklist_summary.py
(which copies the latest week onto the worklist):

    .venv/bin/python scripts/simulate_weekly_monitoring.py --weeks 4
    .venv/bin/python scripts/pin_demo_patient.py --dry-run
    .venv/bin/python scripts/pin_demo_patient.py
    .venv/bin/python scripts/refresh_worklist_summary.py
"""
from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv

from api.db_utils import get_db_name, get_mongo_client
from models.monitoring_rules import red_flags

COLLECTION = "weekly_monitoring"
BANDS = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                     "docs", "mimic", "band_thresholds_mimic.json")

MH_FOLLOWUP_MISSED = ("Follow-up appointment: missed (in mental health care a missed appointment "
                      "is often the first sign of disengagement, and is the strongest predictor on "
                      "this card. Direct contact matters more than any reading here)")
MH_ADHERENCE = ("psychiatric medicines stopped part-way are a common route back to hospital, and "
                "side effects are usually the reason rather than intent")

PINNED = {
    "MIMIC-10683325": {
        1: {"risk_score": 83.2,
            "monitoring": {"weight_change_kg": 1.7, "adherence_pct": 72, "refill_status": "missed",
                           "followup_status": "missed", "sbp": 140, "heart_rate": 76, "spo2": 94},
            "drivers": [MH_FOLLOWUP_MISSED,
                        "Pharmacy refill: missed (an uncollected prescription is one of the few hard "
                        "signals here - it is a fact from the pharmacy, not a self-report)",
                        f"Medication adherence: 72% ({MH_ADHERENCE})"]},
        2: {"risk_score": 87.4,
            "monitoring": {"weight_change_kg": 2.2, "adherence_pct": 72, "refill_status": "collected",
                           "followup_status": "missed", "sbp": 160, "heart_rate": 102, "spo2": 92},
            "drivers": [MH_FOLLOWUP_MISSED,
                        f"Medication adherence: 72% ({MH_ADHERENCE})",
                        "Weight change since discharge: +2.2 kg (weight is not a meaningful signal in "
                        "mental health recovery, and a change this size is more often an effect of "
                        "the medication than a warning about anything)"]},
        3: {"risk_score": 89.9,
            "monitoring": {"weight_change_kg": 3.1, "adherence_pct": 51, "refill_status": "late",
                           "followup_status": "missed", "sbp": 160, "heart_rate": 109, "spo2": 90},
            "drivers": [MH_FOLLOWUP_MISSED,
                        f"Medication adherence: 51% ({MH_ADHERENCE})",
                        "Pharmacy refill: late (a few days without supply is usually logistics rather "
                        "than intent, but the treatment gap is real either way)"]},
        4: {"risk_score": 96.0,
            "monitoring": {"weight_change_kg": 4.1, "adherence_pct": 23, "refill_status": "collected",
                           "followup_status": "attended", "sbp": 167, "heart_rate": 100, "spo2": 85},
            "drivers": ["Medication adherence: 23% (the regimen has effectively stopped. In mental "
                        "health this needs a conversation rather than a reminder, since the reason is "
                        "usually side effects or a decision the patient has made)",
                        "Follow-up appointment: attended (the patient is still engaged with the "
                        "service, which is the single most protective thing in this group)",
                        "Oxygen saturation: 85% (a saturation this low at home is an assessment "
                        "today, not a note for the next review)"]},
    },
}


def band(score: float) -> str:
    try:
        t = json.load(open(BANDS))
        high, low = t["high_score_threshold"], t["low_score_threshold"]
    except (OSError, KeyError, ValueError):
        high, low = 40.0, 20.0
    return "High" if score >= high else "Medium" if score >= low else "Low"


def pin(db, dry: bool = False) -> list:
    """Rewrite the pinned weeks in place. Returns what was (or would be) done."""
    done = []
    for pid, weeks in PINNED.items():
        existing = {d["week_number"]: d for d in db[COLLECTION].find({"patient_id": pid})}
        if not existing:
            sys.exit(f"  {pid} has no weekly monitoring - run simulate_weekly_monitoring.py first. "
                     "Nothing changed.")
        extra = sorted(w for w in existing if w > max(weeks))
        if extra:
            sys.exit(f"  {pid} has weeks {extra} beyond week {max(weeks)} - regenerate with "
                     "simulate_weekly_monitoring.py --weeks 4 first. Nothing changed.")
        for wk, spec in weeks.items():
            if wk not in existing:
                sys.exit(f"  {pid} has no week {wk}. Nothing changed.")
            d1, d2, d3 = spec["drivers"]
            update = {"risk_score": spec["risk_score"], "risk_band": band(spec["risk_score"]),
                      "monitoring": spec["monitoring"], "red_flags": red_flags(spec["monitoring"]),
                      "driver_1": d1, "driver_2": d2, "driver_3": d3, "observed": True,
                      "pinned_by": "scripts/pin_demo_patient.py"}
            if not dry:
                db[COLLECTION].update_one({"_id": existing[wk]["_id"]}, {"$set": update})
            done.append((pid, wk, existing[wk].get("risk_score"), spec["risk_score"],
                         update["red_flags"]))
    return done


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.strip().split("\n\n")[0])
    parser.add_argument("--dry-run", action="store_true", help="report without writing anything")
    args = parser.parse_args()
    load_dotenv()
    db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))[get_db_name()]
    for pid, wk, before, after, flags in pin(db, args.dry_run):
        note = f"  red flag: {', '.join(flags)}" if flags else ""
        print(f"  {pid} week {wk}: {before} -> {after}{note}")
    print("  Dry run: nothing written." if args.dry_run else
          "  Done. Now run scripts/refresh_worklist_summary.py.")


if __name__ == "__main__":
    main()
