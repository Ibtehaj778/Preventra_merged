#!/usr/bin/env python3
"""
Rewrite the stored `days_since_prev` driver label in MongoDB.

WHY
---
Driver strings are rendered at scoring time and persisted verbatim as
"<label>: <value> (<explanation>)", so changing the label map in
models/mimic_drivers.py only affects documents written after the change.
Everything already in the database keeps the old wording.

The old label read "Days since previous discharge". In the weekly monitoring
cards that sits directly beneath a "7 days later" header, where it reads as
"it has been 2 days since you were discharged" - which is a different quantity
from what the feature means, and contradicts the header.

The feature is the gap between the patient's PREVIOUS discharge and the start
of THIS admission. It is fixed when the admission opens and correctly never
changes across the weekly series. Only the wording was wrong, so this is a
pure relabel: no score, band, value or ordering is touched.

USAGE
-----
    python scripts/relabel_gap_driver.py --dry-run
    python scripts/relabel_gap_driver.py
"""

from __future__ import annotations

import argparse
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pymongo import MongoClient  # noqa: E402

OLD_LABEL = "Days since previous discharge"
NEW_LABEL = "Gap before this admission"

# Old explanation -> new. Keyed on the exact strings _gap_explain used to emit.
# "no previous discharge on record" is unchanged and so is absent here.
EXPLANATIONS = {
    "a short gap since the last stay indicates unresolved illness":
        "this admission began soon after the previous discharge, which indicates unresolved illness",
    "a previous stay within the last three months":
        "the previous stay ended within three months of this admission",
    "the previous stay was some time ago; the model weighted the fact of a prior admission rather than its recency":
        "the previous stay was well before this admission; the model weighted the fact of a prior admission rather than its recency",
}

COLLECTIONS = ("weekly_monitoring", "patient_worklist", "risk_registry")
DRIVER_FIELDS = ("driver_1", "driver_2", "driver_3")


def rewrite(driver: str) -> str:
    """Relabel one driver string, leaving value and structure untouched."""
    if not isinstance(driver, str) or not driver.startswith(OLD_LABEL + ":"):
        return driver
    out = NEW_LABEL + driver[len(OLD_LABEL):]
    for old, new in EXPLANATIONS.items():
        # The explanation is the trailing "(...)" of the driver string.
        if out.endswith(f"({old})"):
            out = out[: -len(f"({old})")] + f"({new})"
            break
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true",
                    help="report what would change without writing")
    args = ap.parse_args()

    uri = os.environ.get("MONGO_URI")
    if not uri:
        # Match api/main.py: read .env from the repo root if the var is unset.
        from dotenv import load_dotenv
        load_dotenv(os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), ".env"))
        uri = os.environ.get("MONGO_URI")
    if not uri:
        print("MONGO_URI is not set", file=sys.stderr)
        return 1

    # The database name is not in the URI; api/main.py hard-codes it.
    db = MongoClient(uri)[os.environ.get("MONGO_DB", "neuroshield")]

    def _retry(fn, attempts=6):
        """Atlas drops the odd TLS handshake here; it clears on a retry."""
        import time
        from pymongo.errors import AutoReconnect, ServerSelectionTimeoutError
        for n in range(1, attempts + 1):
            try:
                return fn()
            except (AutoReconnect, ServerSelectionTimeoutError):
                if n == attempts:
                    raise
                time.sleep(min(2 ** n, 20))
    pattern = re.compile("^" + re.escape(OLD_LABEL) + ":")
    query = {"$or": [{f: {"$regex": pattern}} for f in DRIVER_FIELDS]}

    grand_total = 0
    for name in COLLECTIONS:
        col = db[name]
        matched = col.count_documents(query)
        changed = 0
        samples: list[tuple[str, str]] = []

        # Batched: one round-trip per 1,000 documents rather than per document.
        # Atlas here intermittently drops a TLS handshake, and 4,000 sequential
        # update_one calls gave it 4,000 chances to do so.
        from pymongo import UpdateOne
        ops = []
        for doc in col.find(query, {f: 1 for f in DRIVER_FIELDS}):
            update = {}
            for field in DRIVER_FIELDS:
                before = doc.get(field)
                after = rewrite(before)
                if after != before:
                    update[field] = after
                    if len(samples) < 2:
                        samples.append((before, after))
            if update:
                changed += 1
                ops.append(UpdateOne({"_id": doc["_id"]}, {"$set": update}))

        if ops and not args.dry_run:
            for i in range(0, len(ops), 1000):
                _retry(lambda b=ops[i:i + 1000]: col.bulk_write(b, ordered=False))

        grand_total += changed
        verb = "would update" if args.dry_run else "updated"
        print(f"  {name:<20} matched {matched:>6,}  {verb} {changed:>6,}")
        for before, after in samples:
            print(f"      - {before}")
            print(f"      + {after}")

    print(f"\n{'would update' if args.dry_run else 'updated'} {grand_total:,} documents")
    if args.dry_run:
        print("dry run - nothing written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
