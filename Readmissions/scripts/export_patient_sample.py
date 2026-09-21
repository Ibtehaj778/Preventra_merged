"""
Export a small, self-contained sample of patients across every collection.

WHY
---
The clinical data for one patient is spread over several collections — their
discharge row, their weekly monitoring series, their score history, any
coordinator actions. Pulling one collection gives you a fragment. This walks
all of them for the same patient ids so the folder can be opened, read and
reasoned about on its own.

    .venv/bin/python scripts/export_patient_sample.py --n 10

Patients are chosen to span risk bands and clinical groups rather than taken
off the top of the list, because ten consecutive Low-risk general-recovery rows
demonstrate nothing.

Writes CSV (for spreadsheets) and JSON (nested fields survive intact) plus a
README describing every file.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pandas as pd
from dotenv import load_dotenv

from api.db_utils import get_mongo_client

# collection -> the field holding the patient id
PATIENT_COLLECTIONS = {
    "patient_worklist": "patient_id",
    "weekly_monitoring": "patient_id",
    "risk_registry": "patient_id",
    "care_actions": "patient_id",
    "alerts": "patient_id",
}
# carried for context; has no patient column
CONTEXT_COLLECTIONS = ["executive_summary"]


def pick_patients(db, n: int) -> list:
    """
    Spread the sample across risk bands and clinical groups.

    Round-robins through (band, group) buckets so a sample of ten contains a
    High and a Low, a heart-failure patient and a general one, rather than
    whatever happens to sort first.
    """
    batch = db["patient_worklist"].find_one(
        {}, {"batch_date": 1}, sort=[("batch_date", -1)])["batch_date"]

    rows = list(db["patient_worklist"].find(
        {"batch_date": batch, "source": "mimic"},
        {"_id": 0, "patient_id": 1, "current_band": 1, "risk_band": 1,
         "clinical_group": 1, "current_score": 1, "weeks_tracked": 1}))

    buckets = defaultdict(list)
    for r in rows:
        key = (r.get("current_band") or r.get("risk_band") or "Low",
               r.get("clinical_group") or "general")
        buckets[key].append(r)

    # Highest score first inside each bucket - a sample of deteriorating
    # patients is more informative than a sample of quiet ones.
    for v in buckets.values():
        v.sort(key=lambda r: -(r.get("current_score") or 0))

    def round_robin(pools: dict) -> list:
        """Take one from each pool in turn until they are empty."""
        keys, out, i = sorted(pools), [], 0
        while any(pools[k] for k in keys):
            k = keys[i % len(keys)]
            if pools[k]:
                out.append(pools[k].pop(0))
            i += 1
        return out

    # Cycle bands FIRST, then groups within each band. Cycling groups first
    # fills the whole sample from the High buckets before it ever reaches a
    # Medium one, which is what a naive single round-robin does here.
    by_band = defaultdict(dict)
    for (band, group), members in buckets.items():
        by_band[band][group] = members
    streams = {b: round_robin(by_band[b]) for b in by_band}

    bands = [b for b in ("High", "Medium", "Low") if streams.get(b)]
    picked, i = [], 0
    while len(picked) < n and any(streams[b] for b in bands):
        b = bands[i % len(bands)]
        if streams[b]:
            picked.append(streams[b].pop(0))
        i += 1
    return picked[:n]


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=10, help="how many patients")
    ap.add_argument("--out", default="data/patient_sample", help="output folder")
    a = ap.parse_args()

    load_dotenv()
    db = get_mongo_client(os.environ.get("MONGO_URI", "mongodb://localhost:27017"))["neuroshield"]

    picked = pick_patients(db, a.n)
    ids = [p["patient_id"] for p in picked]
    print(f"  {len(ids)} patients selected\n")
    print(f"  {'patient':18} {'band':8} {'score':>6} {'weeks':>6}  group")
    for p in picked:
        print(f"  {p['patient_id']:18} {str(p.get('current_band') or p.get('risk_band')):8} "
              f"{p.get('current_score', 0):>6} {p.get('weeks_tracked', 0):>6}  "
              f"{p.get('clinical_group')}")

    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    manifest, written = [], {}
    for coll, key in PATIENT_COLLECTIONS.items():
        if coll not in db.list_collection_names():
            continue
        docs = list(db[coll].find({key: {"$in": ids}}, {"_id": 0}))
        written[coll] = len(docs)
        if not docs:
            manifest.append((coll, 0, "no rows for these patients"))
            continue

        (out / f"{coll}.json").write_text(json.dumps(docs, indent=2, default=str))
        # CSV is the convenient form; nested fields are JSON-encoded so the
        # column survives a spreadsheet without silently losing its contents.
        flat = pd.json_normalize(docs, sep=".")
        for c in flat.columns:
            if flat[c].apply(lambda v: isinstance(v, (list, dict))).any():
                flat[c] = flat[c].apply(lambda v: json.dumps(v, default=str)
                                        if isinstance(v, (list, dict)) else v)
        flat.to_csv(out / f"{coll}.csv", index=False)
        manifest.append((coll, len(docs), f"{len(flat.columns)} columns"))

    for coll in CONTEXT_COLLECTIONS:
        docs = list(db[coll].find({}, {"_id": 0}))
        (out / f"{coll}.json").write_text(json.dumps(docs, indent=2, default=str))
        pd.DataFrame(docs).to_csv(out / f"{coll}.csv", index=False)
        manifest.append((coll, len(docs), "whole collection - batch context, not per patient"))

    (out / "patients.json").write_text(json.dumps(picked, indent=2, default=str))

    stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    groups = Counter(p.get("clinical_group") for p in picked)
    bands = Counter(p.get("current_band") or p.get("risk_band") for p in picked)

    readme = [
        f"# Patient sample — {len(ids)} patients",
        "",
        f"Exported {stamp} from the `neuroshield` MongoDB database.",
        "",
        "Every file here is filtered to the same patient ids, so the folder is a",
        "coherent slice rather than five unrelated extracts. Each collection is",
        "written twice: `.csv` for spreadsheets, `.json` where nested fields",
        "(weekly observations, group evidence) need to stay intact.",
        "",
        "## Patients",
        "",
        "| Patient | Band | Score | Weeks | Group |",
        "|---|---|---:|---:|---|",
    ]
    for p in picked:
        readme.append(f"| `{p['patient_id']}` | {p.get('current_band') or p.get('risk_band')} "
                      f"| {p.get('current_score', 0)} | {p.get('weeks_tracked', 0)} "
                      f"| {p.get('clinical_group')} |")
    readme += [
        "",
        f"Bands: {', '.join(f'{k} {v}' for k, v in bands.most_common())}  ",
        f"Groups: {', '.join(f'{k} {v}' for k, v in groups.most_common())}",
        "",
        "## Files",
        "",
        "| File | Rows | Notes |",
        "|---|---:|---|",
    ]
    descriptions = {
        "patient_worklist": "one row per patient — discharge score, current band, drivers, diagnoses, clinical group",
        "weekly_monitoring": "one row per patient per week — week 0 is the model, weeks 1-4 the rule layer",
        "risk_registry": "score history across scoring batches",
        "care_actions": "coordinator assignments and notes",
        "alerts": "raised when a score crosses a 15-point or band jump",
        "executive_summary": "band counts per batch",
    }
    for coll, n, note in manifest:
        if n == 0:
            # No file is written for an empty result, so do not advertise one.
            readme.append(f"| _(not written)_ | 0 | `{coll}` — {descriptions.get(coll, note)}; "
                          f"none for these patients |")
        else:
            readme.append(f"| `{coll}.csv` / `.json` | {n} | {descriptions.get(coll, note)} |")
    readme += [
        "| `patients.json` | " + str(len(picked)) + " | the selection itself, with why each was picked |",
        "",
        "## Joining them",
        "",
        "Everything keys on `patient_id`:",
        "",
        "```python",
        "import pandas as pd",
        "wl = pd.read_csv('patient_worklist.csv')",
        "wk = pd.read_csv('weekly_monitoring.csv').sort_values(['patient_id', 'week_number'])",
        "wk.merge(wl[['patient_id', 'clinical_group', 'primary_diagnosis']], on='patient_id')",
        "```",
        "",
        "In the CSV the nested `monitoring` object is flattened to dotted columns —",
        "`monitoring.adherence_pct`, `monitoring.spo2`, `monitoring.weight_change_kg` and",
        "so on. The JSON keeps it nested. `driver_1..3` are",
        "`label: value (explanation)` strings in both.",
        "",
        "## Provenance",
        "",
        "Discharge scores and their SHAP drivers are real model output over MIMIC-IV.",
        "The weekly observations are augmented — MIMIC holds no post-discharge data —",
        "with trajectories drawn from the model's own calibrated probability. Every",
        "weekly row carries `source` saying so.",
    ]
    (out / "README.md").write_text("\n".join(readme) + "\n")

    print(f"\n  written to {out}/")
    for coll, n, _ in manifest:
        print(f"    {coll + '.csv':28} {n:>6} rows")
    print(f"    {'README.md':28}")


if __name__ == "__main__":
    main()
