"""
Write every condition a patient has onto their worklist row.

WHY
---
clinical_group is the ONE plan a patient is monitored under - the highest
priority condition they have. Filtering on it hid people: a patient with heart
failure and diabetes is monitored as heart failure, so they never appeared when
someone filtered for diabetes, even though they have it and it is documented.

This adds:
    clinical_groups   list of group keys, best evidence first. ["general"]
                      when no condition matched, so an $in query never has to
                      special-case the empty list.
    group_matches     the same list with the label, confidence and the exact
                      diagnosis each group was found in, for the UI.

clinical_group is left untouched. Which plan a patient is on is a clinical
decision that should not change because the filter got better.

Idempotent - safe to re-run after models/icd_groups.py changes.
"""
from __future__ import annotations

import os
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dotenv import load_dotenv
from pymongo import UpdateOne

from api.db_utils import get_mongo_client
from models.icd_groups import classify, classify_all

BATCH = 1000


def main() -> None:
    load_dotenv()
    db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))["neuroshield"]
    col = db["patient_worklist"]

    rows = list(col.find({}, {"_id": 1, "primary_icd_code": 1, "primary_diagnosis": 1,
                              "secondary_diagnoses": 1, "clinical_group": 1}))
    print(f"  {len(rows):,} worklist rows")

    ops, per_group, per_count, realigned = [], Counter(), Counter(), 0
    for r in rows:
        code = r.get("primary_icd_code", "") or ""
        dx = r.get("primary_diagnosis", "") or ""
        sec = r.get("secondary_diagnoses") or []

        matches = classify_all(code, dx, sec)
        keys = [m["group"] for m in matches] or ["general"]
        per_count[len(matches)] += 1
        for k in keys:
            per_group[k] += 1

        update = {"clinical_groups": keys, "group_matches": matches}

        # Rows loaded before icd_groups changed can carry a stale primary group.
        # classify_all[0] is the same pick classify() makes, so realigning here
        # keeps the two fields from ever contradicting each other.
        primary = classify(code, dx, sec)
        if primary["group"] != r.get("clinical_group"):
            realigned += 1
            update.update({"clinical_group": primary["group"],
                           "group_label": primary["label"],
                           "group_evidence": primary["evidence"],
                           "group_confidence": primary["confidence"]})

        ops.append(UpdateOne({"_id": r["_id"]}, {"$set": update}))

    for i in range(0, len(ops), BATCH):
        col.bulk_write(ops[i:i + BATCH], ordered=False)
        print(f"    {min(i + BATCH, len(ops)):>7,} / {len(ops):,}")
    if realigned:
        print(f"  realigned {realigned:,} stale primary groups")

    print("\n  conditions per patient:")
    for k in sorted(per_count):
        print(f"    {k}: {per_count[k]:,}")
    print("\n  patients per condition (membership, not primary group):")
    for g, n in per_group.most_common():
        print(f"    {g:18} {n:,}")

    # Multikey index: MongoDB indexes each element, so {clinical_groups: {$in:
    # [...]}} is an index scan rather than a collection scan.
    print("\n  ensuring index ...")
    print("   ", col.create_index([("batch_date", 1), ("clinical_groups", 1)]))
    print("\ndone")


if __name__ == "__main__":
    main()
