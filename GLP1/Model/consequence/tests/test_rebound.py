"""Unit tests for Model/consequence/rebound.py.

Run from project root:
    python -m pytest Model/consequence/tests/test_rebound.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Model.consequence.rebound import (  # noqa: E402
    ReboundParams,
    bmi_trajectory,
    dm_status_at_dropout,
    hba1c_trajectory,
    months_to_threshold,
    p_new_t2d_12mo,
    p_uncontrolled_12mo,
    rebound_severity_score,
    reduction_attained,
)


@pytest.fixture
def params() -> ReboundParams:
    """Realistic parameter set sourced from the parameter registry."""
    return ReboundParams(
        hba1c_rate_per_month=0.10,
        hba1c_plateau_pct=0.66,
        bmi_rate_per_month=0.42,
        bmi_plateau_pct=0.67,
        steady_state_days=90.0,
        t2d_threshold_hba1c=6.5,
        uncontrolled_threshold_hba1c=8.0,
        t2d_incidence_low_per_year=0.05,
        t2d_incidence_high_per_year=0.11,
        uncontrolled_progression_per_year=0.18,
        hba1c_floor=5.0,
    )


# ── reduction_attained ──────────────────────────────────────────────────────

def test_reduction_attained_zero_time(params):
    assert reduction_attained(1.6, 0, params.steady_state_days) == 0.0


def test_reduction_attained_partial_steady_state(params):
    # 45 days = half of 90-day steady state → half of trial reduction
    r = reduction_attained(1.6, 45, params.steady_state_days)
    assert r == pytest.approx(0.8)


def test_reduction_attained_capped_at_full(params):
    # 180 days > 90-day steady state → full reduction
    r = reduction_attained(1.6, 180, params.steady_state_days)
    assert r == pytest.approx(1.6)


def test_reduction_floor_enforced(params):
    """A patient at baseline 5.3 cannot have HbA1c driven below 5.0 by GLP-1."""
    r = reduction_attained(
        1.6, 180, params.steady_state_days, baseline_hba1c=5.3, floor=params.hba1c_floor
    )
    assert r == pytest.approx(0.3)  # 5.3 - 5.0 = 0.3 max


def test_reduction_no_floor_when_baseline_high(params):
    """Patient with baseline 8.0 can absorb full 1.6-pt reduction (down to 6.4)."""
    r = reduction_attained(
        1.6, 180, params.steady_state_days, baseline_hba1c=8.0, floor=params.hba1c_floor
    )
    assert r == pytest.approx(1.6)


# ── hba1c_trajectory ────────────────────────────────────────────────────────

def test_hba1c_trajectory_at_dropout_equals_on_therapy(params):
    """At month 0 the trajectory equals the on-therapy HbA1c."""
    months = np.array([0.0])
    traj = hba1c_trajectory(7.0, 1.6, 180.0, months, params)
    assert traj[0] == pytest.approx(7.0 - 1.6)


def test_hba1c_trajectory_monotone_non_decreasing(params):
    months = np.arange(0, 24, 0.5)
    traj = hba1c_trajectory(7.0, 1.6, 180.0, months, params)
    assert (np.diff(traj) >= -1e-12).all()


def test_hba1c_trajectory_caps_at_plateau(params):
    """At very large t the HbA1c equals baseline minus (1 - plateau) × reduction."""
    months = np.array([100.0])
    traj = hba1c_trajectory(7.0, 1.6, 180.0, months, params)
    expected_max = 7.0 - 1.6 + 1.6 * params.hba1c_plateau_pct  # = 7.0 - 1.6*0.34
    assert traj[0] == pytest.approx(expected_max)


def test_hba1c_trajectory_early_dropout_worse_12mo(params):
    """Early dropout → worse 12-month HbA1c.

    A patient who drops at day 30 attained only ~0.5 HbA1c reduction; they
    retain 34% of that (0.17) as durable benefit. A patient who stayed 180
    days attained the full 1.6 reduction; they retain 34% of that (0.54).
    So late-dropout patients end up LOWER (better) at 12 months — the model
    reflects the published finding that longer GLP-1 exposure is more durable.
    """
    months = np.array([12.0])
    early = hba1c_trajectory(7.0, 1.6, 30.0, months, params)
    late = hba1c_trajectory(7.0, 1.6, 180.0, months, params)
    assert early[0] > late[0]


def test_hba1c_trajectory_normal_baseline_no_floor_breach(params):
    """A patient with baseline HbA1c 5.5 cannot have on-therapy HbA1c < 5.0."""
    months = np.array([0.0])
    traj = hba1c_trajectory(5.5, 1.6, 180.0, months, params)
    assert traj[0] >= params.hba1c_floor - 1e-9


# ── bmi_trajectory ──────────────────────────────────────────────────────────

def test_bmi_trajectory_at_dropout(params):
    months = np.array([0.0])
    # 14.9% weight loss on baseline 30 BMI = 30 - 4.47 = 25.53
    traj = bmi_trajectory(30.0, 14.9, 180.0, months, params)
    assert traj[0] == pytest.approx(30.0 - 30.0 * 0.149)


def test_bmi_trajectory_caps_at_baseline_minus_residual(params):
    """At long t, BMI plateaus below baseline by (1 - plateau) × loss."""
    months = np.array([100.0])
    traj = bmi_trajectory(30.0, 14.9, 180.0, months, params)
    loss = 30.0 * 0.149
    expected_max = 30.0 - loss + loss * params.bmi_plateau_pct  # rebounds 67% of the loss
    assert traj[0] == pytest.approx(expected_max)


def test_bmi_trajectory_monotone(params):
    months = np.arange(0, 24, 0.5)
    traj = bmi_trajectory(30.0, 14.9, 180.0, months, params)
    assert (np.diff(traj) >= -1e-12).all()


# ── dm_status_at_dropout ────────────────────────────────────────────────────

def test_dm_status_partitions(params):
    assert dm_status_at_dropout(5.0, params) == "normal"
    assert dm_status_at_dropout(5.7, params) == "pre_dm"
    assert dm_status_at_dropout(6.49, params) == "pre_dm"
    assert dm_status_at_dropout(6.5, params) == "t2d"
    assert dm_status_at_dropout(7.99, params) == "t2d"
    assert dm_status_at_dropout(8.0, params) == "uncontrolled_t2d"


# ── months_to_threshold ─────────────────────────────────────────────────────

def test_months_to_threshold_basic(params):
    # From 6.0 with 0.10/month rate to threshold 6.5 → 5 months
    m = months_to_threshold(6.0, 1.0, 6.5, 0.10)
    assert m == pytest.approx(5.0)


def test_months_to_threshold_already_above(params):
    m = months_to_threshold(7.0, 1.0, 6.5, 0.10)
    assert m == 0.0


def test_months_to_threshold_unreachable(params):
    # Patient at 6.0 with asymptote only 0.2 — can't reach 6.5
    m = months_to_threshold(6.0, 0.2, 6.5, 0.10)
    assert m is None


def test_months_to_threshold_zero_rate(params):
    m = months_to_threshold(6.0, 1.0, 6.5, 0.0)
    assert m is None


# ── p_new_t2d_12mo / p_uncontrolled_12mo ────────────────────────────────────

def test_p_new_t2d_none_for_t2d_patient(params):
    assert p_new_t2d_12mo(7.5, 8.0, params) is None


def test_p_new_t2d_one_when_trajectory_crosses(params):
    # pre-DM at dropout (HbA1c 6.2), trajectory ends at 6.8 → crosses 6.5
    assert p_new_t2d_12mo(6.2, 6.8, params) == 1.0


def test_p_new_t2d_uses_dpp_high_when_subthreshold(params):
    # pre-DM at 6.2, trajectory ends at 6.3 → below threshold, use high stratum
    assert p_new_t2d_12mo(6.2, 6.3, params) == params.t2d_incidence_high_per_year


def test_p_new_t2d_uses_dpp_low_when_below_six(params):
    # pre-DM 5.8 → low stratum
    assert p_new_t2d_12mo(5.8, 5.9, params) == params.t2d_incidence_low_per_year


def test_p_uncontrolled_none_for_pre_dm(params):
    assert p_uncontrolled_12mo(6.0, 6.2, params) is None


def test_p_uncontrolled_one_when_already_uncontrolled(params):
    assert p_uncontrolled_12mo(8.5, 9.0, params) == 1.0


def test_p_uncontrolled_one_when_trajectory_crosses(params):
    assert p_uncontrolled_12mo(7.5, 8.2, params) == 1.0


def test_p_uncontrolled_uses_progression_baseline(params):
    assert p_uncontrolled_12mo(7.0, 7.4, params) == params.uncontrolled_progression_per_year


# ── rebound_severity_score ──────────────────────────────────────────────────

def test_severity_in_unit_interval():
    s = rebound_severity_score(5.5, 6.5, 28.0, 30.0, 0.5)
    assert 0.0 <= s <= 1.0


def test_severity_zero_when_no_rebound():
    s = rebound_severity_score(5.5, 5.5, 28.0, 28.0, 0.0)
    assert s == 0.0


def test_severity_one_at_extremes():
    # max HbA1c rebound (>=2), max BMI rebound (>=5), p_crossing=1 → score=1
    s = rebound_severity_score(5.0, 7.5, 25.0, 31.0, 1.0)
    assert s == pytest.approx(1.0)


def test_severity_handles_none_p_crossing():
    # When p_crossing is None (e.g., patient is normal HbA1c with no T2D risk to compute)
    s = rebound_severity_score(5.0, 5.5, 28.0, 30.0, None)
    assert 0.0 <= s <= 1.0
    # Should equal 0.4 * 0.25 + 0.3 * 0.4 + 0.3 * 0.0 = 0.22
    assert s == pytest.approx(0.4 * 0.25 + 0.3 * 0.4 + 0.0, abs=1e-6)
