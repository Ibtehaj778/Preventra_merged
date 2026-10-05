"""
The clickable parts of a chatbot answer.

The answer is plain text written by the model, so the browser cannot tell a
patient id from a count, or a condition from a word that happens to share its
name. What it can trust is the data the answer was phrased from: every patient
id, condition, diagnosis and clinician named there is a real row the caller is
allowed to see. This module walks that payload and hands those values back, and
the chat window links each one where it appears in the text.

Nothing is linked that the query did not return. A value the model invented
gets no link, which is the right failure: a dead link to a patient who does not
exist is worse than plain text.
"""

from typing import Optional

from api.doctor_service import DOCTORS
from models.icd_groups import GROUP_LABELS

# Enough for any answer a person would read; a list of every patient in a band
# is capped by the query layer long before this.
MAX_ENTITIES = 300

_LABEL_TO_GROUP = {label.lower(): key for key, label in GROUP_LABELS.items()}
_DIAGNOSIS_KEYS = ("diagnosis", "primary_diagnosis")
_DOCTOR_NAME_KEYS = {"doctors": "name", "workload": "doctor"}


def _walk(value, key: Optional[str], found: dict) -> None:
    if isinstance(value, dict):
        for k, v in value.items():
            _walk(v, k, found)
        return
    if isinstance(value, list):
        for v in value:
            _walk(v, key, found)
        return
    if value is None or isinstance(value, bool):
        return

    if key == "patient_id":
        pid = str(value).strip()
        if pid:
            found["patient"].setdefault(pid, pid)
        return

    if not isinstance(value, str):
        return
    text = value.strip()
    if not text:
        return

    if key in ("clinical_group", "clinical_groups") and text in GROUP_LABELS:
        group, text = text, GROUP_LABELS[text]
    else:
        group = _LABEL_TO_GROUP.get(text.lower())
    if group is not None:
        found["condition"].setdefault(text, group)
        return

    if key in _DIAGNOSIS_KEYS:
        found["diagnosis"].setdefault(text, text)


def _doctor_names(result) -> set:
    names = set()
    if not isinstance(result, dict):
        return names
    for list_key, name_key in _DOCTOR_NAME_KEYS.items():
        for row in result.get(list_key) or []:
            if isinstance(row, dict) and isinstance(row.get(name_key), str):
                name = row[name_key].strip()
                if name and name != "unrouted":
                    names.add(name)
    return names


def extract_entities(result, db=None) -> list:
    """
    The linkable values in one query result, as
    [{"kind": "patient"|"condition"|"diagnosis"|"doctor", "text": ..., "value": ...}].

    `text` is how the value reads in prose; `value` is what the dashboard
    filters on (a patient id, a condition key, a diagnosis to search for, a
    registry doctor id).
    """
    if result is None:
        return []

    found = {"patient": {}, "condition": {}, "diagnosis": {}}
    _walk(result, None, found)

    entities = [{"kind": kind, "text": text, "value": value}
                for kind, items in found.items() for text, value in items.items()]

    # Doctor ids are kept out of the payload on purpose (the model would read
    # them aloud), so the link resolves the name back to the registry here.
    names = _doctor_names(result)
    if names and db is not None:
        try:
            for row in db[DOCTORS].find({"name": {"$in": sorted(names)}},
                                        {"_id": 0, "name": 1, "doctor_id": 1}):
                if row.get("doctor_id"):
                    entities.append({"kind": "doctor", "text": row["name"],
                                     "value": row["doctor_id"]})
        except Exception as exc:
            print(f"[chatbot] could not resolve doctor links: {exc}")

    return entities[:MAX_ENTITIES]
