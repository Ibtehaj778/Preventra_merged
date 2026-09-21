"""Unit tests for Model/consequence/roi.py.

Run from project root:
    python -m pytest Model/consequence/tests/test_roi.py -v
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[3]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Model.consequence.roi import (  # noqa: E402
    ROIInputs,
    ROIOutput,
    annuity_factor,
    break_even_adherence,
    compute_roi,
    expected_drug_cost,
    population_roi,
    time_to_positive_roi,
)


# ── annuity_factor ─────────────────────────────────────────────────────────

def test_annuity_zero_years():
    assert annuity_factor(0, 0.03) == 0.0


def test_annuity_zero_discount_equals_years():
    assert annuity_factor(5, 0.0) == pytest.approx(5.0)


def test_annuity_positive_discount_less_than_years():
    a = annuity_factor(5, 0.03)
    assert 0 < a < 5.0
    # Sanity: sum_{i=0..4} 1/(1.03)^i ≈ 4.717
    assert a == pytest.approx(4.7171, abs=1e-3)


# ── expected_drug_cost ─────────────────────────────────────────────────────

def test_drug_cost_full_adherence_matches_annuity():
    """If everyone is adherent, cost = D × annuity."""
    d = expected_drug_cost(adherence=1.0, annual_drug_cost=10000, horizon_years=5,
                           avg_time_to_dropout_days=90, discount_rate=0.03)
    assert d == pytest.approx(10000 * annuity_factor(5, 0.03))


def test_drug_cost_zero_adherence_prorated():
    """If everyone drops, cost = D × time_to_dropout/365."""
    d = expected_drug_cost(adherence=0.0, annual_drug_cost=10000, horizon_years=5,
                           avg_time_to_dropout_days=90, discount_rate=0.03)
    assert d == pytest.approx(10000 * 90 / 365)


def test_drug_cost_mixed_cohort():
    """50/50 mix produces the expected blend."""
    d = expected_drug_cost(adherence=0.5, annual_drug_cost=10000, horizon_years=5,
                           avg_time_to_dropout_days=90, discount_rate=0.03)
    adherent = 0.5 * 10000 * annuity_factor(5, 0.03)
    dropout = 0.5 * 10000 * 90 / 365
    assert d == pytest.approx(adherent + dropout)


# ── break_even_adherence ───────────────────────────────────────────────────

def test_break_even_simple():
    """D=$10k, savings=$20k → break-even at 50% adherence."""
    be = break_even_adherence(annual_drug_cost=10000, downstream_dropout=50000,
                              downstream_adherent=30000)
    assert be == pytest.approx(0.5)


def test_break_even_none_when_no_savings():
    """If adherent cost >= dropout cost, program can never break even."""
    be = break_even_adherence(annual_drug_cost=10000, downstream_dropout=30000,
                              downstream_adherent=30000)
    assert be is None
    be = break_even_adherence(annual_drug_cost=10000, downstream_dropout=30000,
                              downstream_adherent=35000)
    assert be is None


def test_break_even_returns_float_type():
    be = break_even_adherence(10000, 50000, 30000)
    assert isinstance(be, float)


# ── compute_roi ─────────────────────────────────────────────────────────────

def _sample_inputs(alpha=0.5, cd=50000, ca=30000, drug=10000, days=100, horizon=5,
                   intervention=0):
    return ROIInputs(
        adherence_probability=alpha,
        annual_drug_cost=drug,
        avg_time_to_dropout_days=days,
        downstream_dropout=cd,
        downstream_adherent=ca,
        horizon_years=horizon,
        discount_rate=0.03,
        intervention_cost_per_patient=intervention,
    )


def test_compute_roi_returns_output_dataclass():
    r = compute_roi(_sample_inputs())
    assert isinstance(r, ROIOutput)


def test_compute_roi_gross_benefit_formula():
    """gross_benefit = α × (C_d − C_a)."""
    r = compute_roi(_sample_inputs(alpha=0.4, cd=50000, ca=30000))
    assert r.gross_benefit == pytest.approx(0.4 * 20000)


def test_compute_roi_expected_downstream_formula():
    """E[downstream] = (1-α)×C_d + α×C_a."""
    r = compute_roi(_sample_inputs(alpha=0.4, cd=50000, ca=30000))
    assert r.expected_downstream == pytest.approx(0.6 * 50000 + 0.4 * 30000)


def test_compute_roi_positive_when_gross_exceeds_costs():
    """Very high avoided-cost → positive ROI."""
    r = compute_roi(_sample_inputs(alpha=0.8, cd=200000, ca=20000, drug=5000, horizon=5))
    assert r.roi > 0


def test_compute_roi_negative_when_drug_dominates():
    """Realistic-ish: modest savings, high drug cost → negative ROI."""
    r = compute_roi(_sample_inputs(alpha=0.3, cd=50000, ca=45000, drug=10000, horizon=5))
    assert r.roi < 0


def test_compute_roi_intervention_reduces_net():
    r0 = compute_roi(_sample_inputs(intervention=0))
    r1 = compute_roi(_sample_inputs(intervention=1000))
    assert r1.net_benefit == pytest.approx(r0.net_benefit - 1000)


def test_compute_roi_intervention_threshold_is_pre_intervention_net():
    """intervention_threshold should equal gross_benefit − drug_cost (with intervention=0)."""
    r = compute_roi(_sample_inputs(intervention=500))
    assert r.intervention_threshold == pytest.approx(r.gross_benefit - r.expected_drug_cost)


def test_compute_roi_horizon_1_matches_annual_cost():
    """At horizon=1, drug_cost annuity factor is 1.0."""
    r = compute_roi(_sample_inputs(alpha=1.0, drug=10000, horizon=1))
    # Full-adherent 1-year: drug cost = $10k
    assert r.expected_drug_cost == pytest.approx(10000)


# ── time_to_positive_roi ────────────────────────────────────────────────────

def _mk_output(year, roi):
    return ROIOutput(
        horizon_years=year, expected_downstream=0, gross_benefit=0,
        expected_drug_cost=1000, intervention_cost=0, net_benefit=roi * 1000,
        roi=roi, break_even_adherence=None, intervention_threshold=0,
    )


def test_time_to_positive_year1_positive():
    ys = [_mk_output(1, 0.1)]
    assert time_to_positive_roi(ys) == 1.0


def test_time_to_positive_interpolates_crossing():
    """Cross zero between year 3 (roi=-0.2) and year 4 (roi=0.2) → year 3.5."""
    ys = [_mk_output(1, -1.0), _mk_output(2, -0.6), _mk_output(3, -0.2), _mk_output(4, 0.2), _mk_output(5, 0.6)]
    assert time_to_positive_roi(ys) == pytest.approx(3.5)


def test_time_to_positive_returns_none_when_never_positive():
    ys = [_mk_output(1, -1.0), _mk_output(2, -0.9), _mk_output(3, -0.8)]
    assert time_to_positive_roi(ys) is None


def test_time_to_positive_empty_input():
    assert time_to_positive_roi([]) is None


# ── population_roi ──────────────────────────────────────────────────────────

def test_population_roi_weights_by_patient_count():
    """Cluster with more patients dominates the weighted ROI."""
    rows = [
        {"n_patients": 100, "gross_benefit_5yr": 1000, "expected_drug_cost_5yr": 500,
         "intervention_cost_5yr": 0},
        {"n_patients": 900, "gross_benefit_5yr": 400,  "expected_drug_cost_5yr": 500,
         "intervention_cost_5yr": 0},
    ]
    roi = population_roi(rows, horizon_years=5)
    # 100 patients: net=500, drug=500 → contrib net=50000, drug=50000
    # 900 patients: net=-100, drug=500 → contrib net=-90000, drug=450000
    # aggregate net=-40000, drug=500000 → roi=-0.08
    assert roi == pytest.approx(-0.08)


def test_population_roi_zero_drug_cost_safe():
    rows = [{"n_patients": 100, "gross_benefit_5yr": 0, "expected_drug_cost_5yr": 0,
             "intervention_cost_5yr": 0}]
    assert population_roi(rows, 5) == 0.0
