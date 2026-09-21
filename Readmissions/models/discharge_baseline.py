"""
The patient's own clinical reference point, recorded at discharge.

WHY THIS EXISTS
---------------
Disease-specific monitoring is mostly comparison against the patient, not
against a population. "Two kilos above dry weight" is a heart failure warning;
"84 kg" is not. "Walking half their usual distance" means something; "300
metres" does not. And an oxygen saturation of 90% is an emergency in one patient
and a Tuesday in another.

Before this module the weekly rules had no per-patient reference at all. An
unsupplied signal fell back to a POPULATION value - SpO2 97%, systolic 125 - so
every threshold was implicitly a population threshold with a disease label
attached. That is the exact failure the COPD saturation rule was written to
avoid, and it recurred for every new signal.

So the baseline is captured once, at discharge, and every relative observation
is expressed against it.

WHAT IS REAL AND WHAT IS NOT
----------------------------
MIMIC contains no post-discharge measurements and no discharge-time dry weight,
walking distance or pain score. These baselines are therefore SIMULATED, like
the weekly observations that use them. They are derived deterministically from
the patient id so a patient's dry weight does not change between page loads, and
they are conditioned on the patient's clinical group so a COPD patient's
baseline saturation sits where a COPD patient's would.

In a live deployment this record is filled in by whoever discharges the patient.
The shape and the API do not change when that happens; only the source does.
"""

from __future__ import annotations

import hashlib
from typing import Optional

# ---------------------------------------------------------------------------
# What a baseline record holds
# ---------------------------------------------------------------------------
# Each entry: (label, unit, why it is needed). Only fields that an actual rule
# consumes are here - a baseline nobody compares against is a form field that
# wastes a clinician's time at the moment they are busiest.
BASELINE_FIELDS = {
    "dry_weight_kg": (
        "Dry weight at discharge", "kg",
        "the reference for every later weight. Fluid gain is measured from here, "
        "not from an arbitrary starting point"),
    "baseline_spo2": (
        "Usual oxygen saturation", "%",
        "what this patient normally sits at. In chronic lung disease that is "
        "often 88-92%, where a population threshold would flag them weekly"),
    "baseline_sbp": (
        "Usual systolic blood pressure", "mmHg",
        "their normal, so a reading is judged as a change rather than against a "
        "population target"),
    "baseline_hr": (
        "Usual resting pulse", "bpm",
        "the same, for heart rate"),
    "usual_walk_metres": (
        "Usual walking distance", "metres",
        "exercise tolerance is one of the earliest things to fall in heart "
        "failure, lung disease and surgical recovery, and it is only readable "
        "against the patient's own usual distance"),
    "baseline_pain": (
        "Pain score at discharge", "out of 10",
        "post-operative pain should trend down. Whether it is doing so needs the "
        "starting point"),
}

# Plausible central values per clinical group, used to simulate a baseline.
# Format: field -> (centre, spread). Anything absent uses _DEFAULT_BASELINE.
_DEFAULT_BASELINE = {
    "dry_weight_kg": (78.0, 14.0),
    "baseline_spo2": (97.0, 1.2),
    "baseline_sbp": (128.0, 12.0),
    "baseline_hr": (76.0, 9.0),
    "usual_walk_metres": (500.0, 180.0),
    "baseline_pain": (2.0, 1.5),
}

_GROUP_BASELINE = {
    # Heart failure: heavier on average, and exercise tolerance already reduced.
    "heart_failure": {"dry_weight_kg": (86.0, 16.0), "baseline_spo2": (95.0, 1.5),
                      "usual_walk_metres": (320.0, 130.0), "baseline_hr": (78.0, 10.0)},
    # Chronic lung disease: this is the group the whole module exists for. A
    # baseline saturation of 90% is normal here and alarming anywhere else.
    "respiratory": {"baseline_spo2": (91.5, 2.0), "usual_walk_metres": (280.0, 120.0),
                    "baseline_hr": (82.0, 10.0)},
    "renal": {"dry_weight_kg": (82.0, 15.0), "baseline_sbp": (138.0, 14.0),
              "usual_walk_metres": (380.0, 150.0)},
    # Surgical recovery starts from a much higher pain score and a much shorter
    # walk than the patient's normal life.
    "surgical_injury": {"baseline_pain": (4.5, 1.8), "usual_walk_metres": (200.0, 110.0)},
    "sepsis_infection": {"usual_walk_metres": (300.0, 140.0), "baseline_hr": (84.0, 11.0)},
    "oncology": {"dry_weight_kg": (70.0, 14.0), "usual_walk_metres": (350.0, 150.0)},
    "neuro_stroke": {"usual_walk_metres": (220.0, 120.0), "baseline_sbp": (140.0, 14.0)},
}

# Physiological floors and ceilings, so a simulated draw can never produce a
# baseline no human has.
_BOUNDS = {
    "dry_weight_kg": (38.0, 180.0),
    "baseline_spo2": (85.0, 100.0),
    "baseline_sbp": (85.0, 190.0),
    "baseline_hr": (45.0, 110.0),
    "usual_walk_metres": (20.0, 2000.0),
    "baseline_pain": (0.0, 10.0),
}


def _unit_normal(patient_id: str, field: str) -> float:
    """
    A stable pseudo-random value in roughly [-1, 1] for one patient and field.

    Derived from a hash rather than drawn, so a patient's dry weight is the same
    on every request. A value that changed between page loads would read as a
    data fault, and would make the weekly deltas meaningless.
    """
    digest = hashlib.md5(f"{patient_id}|baseline|{field}".encode("utf-8")).hexdigest()
    # Two draws averaged: a flat hash gives a uniform distribution, and averaging
    # pulls it toward the centre so extremes are rare rather than common.
    a = int(digest[:8], 16) / 0xFFFFFFFF
    b = int(digest[8:16], 16) / 0xFFFFFFFF
    return (a + b) - 1.0


def derive_baseline(patient_id: str, group: str = "general") -> dict:
    """
    A simulated discharge baseline for one patient.

    Deterministic in (patient_id, field), conditioned on the clinical group.
    Carries `source: "simulated"` so nothing downstream can mistake it for a
    measurement somebody took.
    """
    spec = {**_DEFAULT_BASELINE, **_GROUP_BASELINE.get(group, {})}
    out = {}
    for field, (centre, spread) in spec.items():
        value = centre + _unit_normal(patient_id, field) * spread
        lo, hi = _BOUNDS[field]
        value = max(lo, min(hi, value))
        # Pain is reported on an integer 0-10 scale; the rest keep one decimal.
        out[field] = int(round(value)) if field == "baseline_pain" else round(value, 1)
    out["source"] = "simulated"
    out["group"] = group
    return out


def describe(baseline: dict) -> list:
    """The baseline as display rows: [{key, label, value, unit, why}]."""
    rows = []
    for field, (label, unit, why) in BASELINE_FIELDS.items():
        if baseline.get(field) is None:
            continue
        rows.append({"key": field, "label": label, "value": baseline[field],
                     "unit": unit, "why": why})
    return rows


# ---------------------------------------------------------------------------
# Turning raw readings into observations the rules can score
# ---------------------------------------------------------------------------
# The rules stay pure functions of one value. Everything that needs the
# patient's own reference is converted here instead, which keeps the comparison
# in one place rather than spread across ten rule bodies.

def relative_observations(raw: dict, baseline: Optional[dict]) -> dict:
    """
    Convert absolute readings into the relative form the rules expect.

        current_weight_kg  ->  weight_change_kg   (against dry weight)
        walk_metres        ->  walk_distance_pct  (against usual distance)
        spo2               ->  spo2_drop          (points below their usual)

    Absolute values already in `raw` are passed through untouched, so a caller
    that has no baseline still works - it simply loses the relative signals
    rather than silently comparing against a population number.
    """
    obs = dict(raw)
    if not baseline:
        return obs

    if raw.get("current_weight_kg") is not None and baseline.get("dry_weight_kg"):
        obs["weight_change_kg"] = round(
            float(raw["current_weight_kg"]) - float(baseline["dry_weight_kg"]), 1)
        obs.pop("current_weight_kg", None)

    if raw.get("walk_metres") is not None and baseline.get("usual_walk_metres"):
        usual = float(baseline["usual_walk_metres"]) or 1.0
        obs["walk_distance_pct"] = round(float(raw["walk_metres"]) / usual * 100, 0)
        obs.pop("walk_metres", None)

    if raw.get("spo2") is not None and baseline.get("baseline_spo2"):
        obs["spo2_drop"] = round(float(baseline["baseline_spo2"]) - float(raw["spo2"]), 1)

    return obs
