#!/usr/bin/env python3
"""
Carry age and sex from the cohort into patient_worklist.

WHY THIS IS NEEDED
------------------
"What does our high-risk population look like?" is the first question a
clinician asks, and the serving database could not answer it: no age, sex or
race field existed on any collection. Those attributes live only in the
training matrix, so anything asking about them had to be refused.

WHY A SUBJECT-LEVEL JOIN IS SAFE
--------------------------------
anchor_age and gender come from MIMIC's `patients` table, not `admissions`, so
they are fixed per patient rather than per stay. Verified against the extract:
of 148,669 subjects, zero have more than one distinct anchor_age or gender. A
join on subject_id alone therefore cannot pick the wrong value.

WHAT IS DELIBERATELY NOT CARRIED
--------------------------------
Race and insurance. Both are in the matrix and neither is needed to answer a
clinical question about a monitoring cohort; putting them on the serving row
invites subgroup comparisons the cohort is too imbalanced to support (WHITE is
roughly two thirds of it). Add them only with a specific question in mind.

    python scripts/backfill_demographics.py [--dry-run]
"""
from __future__ import annotations

import argparse
import os
import sys

import pandas as pd
from dotenv import load_dotenv

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
load_dotenv(os.path.join(ROOT, ".env"))

from pymongo import UpdateOne  # noqa: E402

from api.db_utils import get_mongo_client  # noqa: E402

MATRIX = os.path.join(ROOT, "data", "mimic", "model", "results", "phase1_matrix.parquet")
# Age above 89 is recorded as 91 for de-identification, so the top of the
# distribution is a spike. Stored as-is and flagged, rather than silently
# reshaped, so anyone reading it can see the censoring.
AGE_CENSOR_AT = 91


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    db = get_mongo_client(os.environ["MONGO_URI"])["neuroshield"]
    worklist = db["patient_worklist"]

    demo = (pd.read_parquet(MATRIX, columns=["subject_id", "anchor_age", "gender"])
              .drop_duplicates("subject_id")
              .set_index("subject_id"))
    print(f"cohort demographics loaded: {len(demo):,} subjects")

    matched = missing = 0
    updates = []
    for row in worklist.find({}, {"_id": 1, "patient_id": 1}):
        pid = str(row["patient_id"])
        if not pid.startswith("MIMIC-"):
            missing += 1
            continue
        try:
            subject = int(pid.split("-", 1)[1])
        except ValueError:
            missing += 1
            continue
        if subject not in demo.index:
            missing += 1
            continue
        age = int(demo.at[subject, "anchor_age"])
        updates.append((row["_id"], {
            "anchor_age": age,
            "age_is_censored": age >= AGE_CENSOR_AT,
            "gender": str(demo.at[subject, "gender"]),
        }))
        matched += 1

    print(f"matched {matched:,} rows; {missing:,} rows have no cohort demographics "
          f"(manually entered patients)")

    if args.dry_run:
        print("dry run - nothing written")
        return 0

    # One update_one per document is ~4,000 round trips to Atlas, which takes
    # minutes over a slow link. Batched writes make it seconds. Every write is
    # a $set, so the whole script is idempotent and an interrupted run can just
    # be repeated.
    batch_size = 500
    written = 0
    for start in range(0, len(updates), batch_size):
        chunk = updates[start:start + batch_size]
        worklist.bulk_write(
            [UpdateOne({"_id": _id}, {"$set": fields}) for _id, fields in chunk],
            ordered=False)
        written += len(chunk)
        print(f"  written {written:,}/{len(updates):,}", flush=True)

    have = worklist.count_documents({"anchor_age": {"$exists": True}})
    print(f"verify: anchor_age now present on {have:,} documents")
    return 0


if __name__ == "__main__":
    sys.exit(main())
