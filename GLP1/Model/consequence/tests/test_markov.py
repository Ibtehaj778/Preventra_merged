"""Unit tests for Model/consequence/markov.py.

Run from project root:
    python -m pytest Model/consequence/tests -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Model.consequence.markov import (  # noqa: E402
    DEATH,
    N_STATES,
    S0,
    S1,
    S2,
    S3,
    MarkovParams,
    build_transition_matrix,
    cv_hazard,
    entry_state,
    primary_cost_driver,
    run_markov,
    s0_to_s1_rate,
)


@pytest.fixture
def params() -> MarkovParams:
    """Realistic parameter set sourced from the parameter registry."""
    return MarkovParams(
        cost_s0_controlled=7900.0,
        cost_s1_uncontrolled=13240.0,
        cost_s2_ckd=28850.0,
        cost_s3_esrd=93191.0,
        cv_acute_cost=53700.0,
        cv_followup_annual=12400.0,
        p_s0_to_s1_normal=0.005,
        p_s0_to_s1_pre_dm=0.06,
        p_s1_to_s2=0.026,
        p_s2_to_s3=0.029,
        p_s3_to_death=0.18,
        p_other_to_death=0.012,
        cv_hazard_s0=0.009,
        cv_hazard_s1=0.022,
        cv_hazard_s2=0.038,
        on_therapy_cv_rr=0.74,
        on_therapy_renal_rr=0.64,
        discount_rate=0.03,
    )


# ── entry_state / s0_to_s1_rate ─────────────────────────────────────────────

def test_entry_state_t2d_threshold():
    assert entry_state(6.5) == S1
    assert entry_state(8.0) == S1
    assert entry_state(6.49) == S0
    assert entry_state(5.0) == S0


def test_s0_to_s1_rate_stratification(params):
    assert s0_to_s1_rate(5.5, params) == pytest.approx(params.p_s0_to_s1_normal)
    assert s0_to_s1_rate(5.7, params) == pytest.approx(params.p_s0_to_s1_pre_dm)
    assert s0_to_s1_rate(6.4, params) == pytest.approx(params.p_s0_to_s1_pre_dm)


# ── transition matrix structure ─────────────────────────────────────────────

def test_transition_matrix_rows_sum_to_one(params):
    for lbxgh in [5.0, 6.0, 7.5]:
        T = build_transition_matrix(s0_to_s1_rate(lbxgh, params), params)
        for state in range(N_STATES):
            assert T[state].sum() == pytest.approx(1.0, abs=1e-9), (
                f"row {state} does not sum to 1"
            )


def test_transition_matrix_non_negative(params):
    T = build_transition_matrix(0.06, params)
    assert (T >= 0).all()


def test_death_is_absorbing(params):
    T = build_transition_matrix(0.06, params)
    assert T[DEATH, DEATH] == 1.0
    assert T[DEATH, :DEATH].sum() == 0.0


def test_esrd_only_exits_to_death(params):
    """S3 should only transition to itself or Death."""
    T = build_transition_matrix(0.06, params)
    assert T[S3, S0] == 0
    assert T[S3, S1] == 0
    assert T[S3, S2] == 0
    assert T[S3, DEATH] == pytest.approx(params.p_s3_to_death)
    assert T[S3, S3] == pytest.approx(1 - params.p_s3_to_death)


def test_on_therapy_renal_rr_reduces_progression(params):
    T_off = build_transition_matrix(0.06, params, on_therapy=False)
    T_on = build_transition_matrix(0.06, params, on_therapy=True)
    # On-therapy patients have lower S1→S2 and S2→S3
    assert T_on[S1, S2] < T_off[S1, S2]
    assert T_on[S2, S3] < T_off[S2, S3]
    # And they spend more time in S1 (residual mass redistributed to self)
    assert T_on[S1, S1] > T_off[S1, S1]


# ── state vector evolution ──────────────────────────────────────────────────

def test_state_vector_stays_a_probability(params):
    traj = run_markov(entry=S1, lbxgh=7.2, horizon_years=10, params=params)
    for t in range(traj.state_probs.shape[0]):
        s = traj.state_probs[t].sum()
        assert s == pytest.approx(1.0, abs=1e-9)
        assert (traj.state_probs[t] >= -1e-12).all()


def test_state_vector_starts_one_hot(params):
    traj = run_markov(entry=S1, lbxgh=7.2, horizon_years=5, params=params)
    expected = np.zeros(N_STATES)
    expected[S1] = 1.0
    np.testing.assert_array_almost_equal(traj.state_probs[0], expected)


def test_death_probability_monotone(params):
    traj = run_markov(entry=S1, lbxgh=7.2, horizon_years=10, params=params)
    deaths = traj.state_probs[:, DEATH]
    diffs = np.diff(deaths)
    assert (diffs >= -1e-12).all(), "death probability must be monotonically non-decreasing"


# ── cost dynamics ───────────────────────────────────────────────────────────

def test_horizon_1_no_discount_no_followup(params):
    """At horizon=1, discounted cost == undiscounted == entry-state cost + CV acute."""
    traj = run_markov(entry=S1, lbxgh=7.2, horizon_years=1, params=params)
    # year 0: state cost on S1, plus first-year CV hazard (S1 = 0.022)
    expected_state = params.cost_s1_uncontrolled
    expected_cv = params.cv_hazard_s1 * params.cv_acute_cost
    # no CV follow-up yet (cv_cum at t=0 is 0)
    assert traj.discounted_cost[0] == pytest.approx(expected_state + expected_cv)
    assert traj.annual_cost[0] == pytest.approx(expected_state + expected_cv)


def test_higher_hba1c_entry_costs_more(params):
    """Patients entering at S1 (HbA1c ≥ 6.5) accrue more 5yr cost than S0 controls."""
    s0_traj = run_markov(entry=S0, lbxgh=5.5, horizon_years=5, params=params)
    s1_traj = run_markov(entry=S1, lbxgh=7.5, horizon_years=5, params=params)
    assert s1_traj.total_discounted_cost > s0_traj.total_discounted_cost


def test_discount_reduces_late_year_cost(params):
    """Year-N discounted cost should equal annual_cost / (1+r)^N."""
    traj = run_markov(entry=S1, lbxgh=7.0, horizon_years=5, params=params)
    for t in range(5):
        expected = traj.annual_cost[t] / ((1 + params.discount_rate) ** t)
        assert traj.discounted_cost[t] == pytest.approx(expected)


def test_zero_discount_matches_undiscounted(params):
    """With discount_rate=0 the discounted and undiscounted totals must agree."""
    p2 = MarkovParams(**{**params.__dict__, "discount_rate": 0.0})
    traj = run_markov(entry=S1, lbxgh=7.0, horizon_years=10, params=p2)
    assert traj.discounted_cost.sum() == pytest.approx(traj.annual_cost.sum())


def test_on_therapy_costs_less_than_off_therapy(params):
    """A patient on GLP-1 should accrue less downstream cost than the same patient off."""
    off = run_markov(entry=S1, lbxgh=7.2, horizon_years=10, params=params, on_therapy=False)
    on = run_markov(entry=S1, lbxgh=7.2, horizon_years=10, params=params, on_therapy=True)
    assert on.total_discounted_cost < off.total_discounted_cost


# ── CV stream ───────────────────────────────────────────────────────────────

def test_cv_cumulative_prob_monotone(params):
    traj = run_markov(entry=S1, lbxgh=7.0, horizon_years=10, params=params)
    diffs = np.diff(traj.cv_cumulative_prob)
    assert (diffs >= -1e-12).all()


def test_cv_hazard_zero_for_death_state(params):
    p = np.zeros(N_STATES)
    p[DEATH] = 1.0
    assert cv_hazard(p, params) == 0.0


# ── primary cost driver ─────────────────────────────────────────────────────

def test_primary_cost_driver_picks_largest():
    bd = {"esrd": 100, "cv_event": 200, "uncontrolled_t2d": 50, "ckd": 30, "controlled_t2d": 0}
    # CKD folds into Uncontrolled_T2D bucket → 80 vs ESRD 100 vs CV 200
    assert primary_cost_driver(bd) == "CV_event"


def test_primary_cost_driver_folds_ckd_into_t2d():
    bd = {"esrd": 80, "cv_event": 70, "uncontrolled_t2d": 30, "ckd": 60, "controlled_t2d": 0}
    # T2D + CKD = 90, beats ESRD = 80 and CV = 70
    assert primary_cost_driver(bd) == "Uncontrolled_T2D"


def test_primary_cost_driver_handles_zero():
    bd = {"esrd": 0, "cv_event": 0, "uncontrolled_t2d": 0, "ckd": 0, "controlled_t2d": 0}
    # All zero → max is fine, just need a deterministic choice
    assert primary_cost_driver(bd) in ("ESRD", "CV_event", "Uncontrolled_T2D")
