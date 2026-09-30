"""Red flags, several conditions per patient, and vitals that follow the
patient's conditions (models/monitoring_rules, models/icd_groups and the weekly
simulator).

The case that prompted this: a patient admitted with hepatitis C and hepatic
coma, acute kidney failure and ascites, whose only diagnosis that matched a
monitoring group was bipolar disorder. They were monitored as a mental health
patient, their oxygen saturation was weighted at 0.3, and an 85% saturation in
the same week as an attended appointment made their score FALL.
"""
import pytest

from models.icd_groups import classify, monitoring_groups
from models.monitoring_rules import (GROUP_PROFILES, RED_FLAG_MIN_POINTS, red_flags,
                                     score_week, weights_for)

LIVER_PATIENT = ("07044", "Chronic hepatitis C with hepatic coma",
                 ["Acute kidney failure, unspecified", "Other ascites",
                  "Bipolar I disorder, most recent episode (or current) depressed, unspecified"])

WEEK = {"weight_change_kg": 0.5, "adherence_pct": 23, "refill_status": "late",
        "followup_status": "attended", "sbp": 135, "heart_rate": 88, "spo2": 96}


# ------------------------------------------------------- several conditions
def test_the_liver_patient_is_not_monitored_as_mental_health_alone():
    assert classify(*LIVER_PATIENT)["group"] == "mental_health"      # the plan, as before
    assert monitoring_groups(*LIVER_PATIENT) == ["mental_health", "general"]


def test_a_patient_whose_every_diagnosis_matched_gets_no_general_entry():
    assert monitoring_groups("F319", "Bipolar disorder", ["Major depressive disorder"]) == \
        ["mental_health"]
    assert monitoring_groups("", "", []) == ["general"]


def test_weights_take_the_strongest_condition():
    assert weights_for(["mental_health"])["spo2"] == 0.3
    assert weights_for(["mental_health", "general"])["spo2"] == 1.0
    # heart failure raises weight; mental health alongside it cannot lower it back
    assert weights_for(["heart_failure", "mental_health"])["weight_change_kg"] == 1.6


# ---------------------------------------------------------------- red flags
@pytest.mark.parametrize("obs, flag", [
    ({"spo2": 85}, "spo2"), ({"sbp": 85}, "sbp"), ({"sbp": 190}, "sbp"),
    ({"heart_rate": 135}, "heart_rate"), ({"temperature_c": 39.4}, "temperature_c"),
    ({"new_confusion": "yes"}, "new_confusion")])
def test_red_flags_are_recognised(obs, flag):
    assert red_flags(obs) == [flag]
    assert red_flags({"spo2": 94, "sbp": 130, "heart_rate": 80}) == []


@pytest.mark.parametrize("group", sorted(GROUP_PROFILES))
def test_a_saturation_of_85_is_never_muted_by_a_group(group):
    _, _, contribs = score_week(57.5, {**WEEK, "spo2": 85}, 0, group=group)
    points, driver = contribs[0]                                     # leads the card
    assert driver.startswith("Oxygen saturation: 85%") and "red flag" in driver
    assert points >= RED_FLAG_MIN_POINTS


@pytest.mark.parametrize("group", sorted(GROUP_PROFILES))
def test_a_red_flag_week_never_scores_lower_than_a_clean_one(group):
    flagged = score_week(57.5, {**WEEK, "spo2": 85}, 0, group=group)[0]
    clean = score_week(57.5, {**WEEK, "spo2": 97}, 0, group=group)[0]
    assert flagged > clean


def test_a_red_flag_stops_the_score_falling_below_last_week():
    """Week 4 of the liver patient: appointment attended, saturation 85%."""
    groups = monitoring_groups(*LIVER_PATIENT)
    score, _, _ = score_week(57.5, {**WEEK, "spo2": 85}, 0, group="mental_health",
                             groups=groups, prev_score=89.9)
    assert score >= 89.9


def test_without_a_red_flag_the_score_may_fall():
    score, _, _ = score_week(57.5, WEEK, 0, group="mental_health", prev_score=89.9)
    assert score < 89.9


def test_the_red_flag_explanation_keeps_the_driver_format():
    """The API splits "<label>: <value> (<explanation>)" on the last " (" -
    an explanation containing one would break the card."""
    _, _, contribs = score_week(57.5, {**WEEK, "spo2": 85}, 0, group="mental_health")
    driver = contribs[0][1]
    assert driver.count(" (") == 1 and driver.endswith(")")


# ------------------------------------------------------ simulated vitals
def test_vitals_follow_the_patients_conditions():
    np = pytest.importorskip("numpy")
    sim = pytest.importorskip("scripts.simulate_weekly_monitoring")
    lows = {"psychiatric only": 0, "liver + psychiatric": 0}
    for seed in range(200):
        for name, groups in (("psychiatric only", ["mental_health"]),
                             ("liver + psychiatric", ["mental_health", "general"])):
            obs = sim.observe_week(4, 4, True, 1.35, np.random.default_rng(seed),
                                   group="mental_health", groups=groups)
            lows[name] += obs["spo2"] < 90
    assert lows["psychiatric only"] == 0
    assert lows["liver + psychiatric"] > 20            # the liver disease is real


def test_patients_with_full_vital_relevance_get_identical_data():
    np = pytest.importorskip("numpy")
    sim = pytest.importorskip("scripts.simulate_weekly_monitoring")
    a = sim.observe_week(3, 4, True, 1.0, np.random.default_rng(5), group="heart_failure")
    b = sim.observe_week(3, 4, True, 1.0, np.random.default_rng(5), group="heart_failure",
                         groups=["heart_failure", "diabetes"])
    assert a == b
