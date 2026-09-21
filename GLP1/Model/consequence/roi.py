"""
Pure ROI math for Phase 3 — Payer ROI Synthesizer.

All functions are stateless. The script entry point (`payer_roi.py`) wires
these together with the Markov rollouts from `markov.py` and the per-patient
adherence data; everything in this file can be unit-tested without I/O.

Formula (from the plan):
    expected_downstream  = (1 − α) × C_dropout + α × C_adherent
    gross_benefit        = C_dropout − expected_downstream
                         = α × (C_dropout − C_adherent)
    drug_cost            = α × D_annual × annuity(t) + (1 − α) × D_annual × t_drop/365
    net_benefit          = gross_benefit − drug_cost
    ROI                  = net_benefit / drug_cost
    break_even_α         = D_annual / (C_dropout − C_adherent)   (at 1-year drug cost)
    intervention_threshold = gross_benefit − drug_cost           (max spend that keeps ROI ≥ 0)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass(frozen=True)
class ROIInputs:
    """All cluster-level numbers needed to compute ROI at one horizon."""

    adherence_probability:        float
    annual_drug_cost:             float
    avg_time_to_dropout_days:     float
    downstream_dropout:           float   # per-patient cumulative discounted, at horizon
    downstream_adherent:          float   # per-patient cumulative discounted, at horizon
    horizon_years:                int
    discount_rate:                float = 0.03
    intervention_cost_per_patient: float = 0.0


@dataclass(frozen=True)
class ROIOutput:
    """Per-horizon ROI summary."""

    horizon_years:           int
    expected_downstream:     float
    gross_benefit:           float
    expected_drug_cost:      float
    intervention_cost:       float
    net_benefit:             float
    roi:                     float
    break_even_adherence:    Optional[float]
    intervention_threshold:  float


def annuity_factor(years: int, discount_rate: float) -> float:
    """Discounted annuity for a stream of $1/year over `years` years.

    Year-0 payment is undiscounted; year-N payment is discounted by (1+r)^N.
    Sum of 1/(1+r)^i for i in 0..years-1.
    """
    if years <= 0:
        return 0.0
    return sum(1.0 / ((1.0 + discount_rate) ** i) for i in range(years))


def expected_drug_cost(
    adherence: float,
    annual_drug_cost: float,
    horizon_years: int,
    avg_time_to_dropout_days: float,
    discount_rate: float = 0.03,
) -> float:
    """Expected per-patient cumulative drug spend over `horizon_years`.

    Adherent cohort pays D_annual every year (discounted). Dropout cohort
    pays D_annual × time_to_dropout/365 once (occurs in year 0, undiscounted).
    """
    adherent_share = adherence * annual_drug_cost * annuity_factor(horizon_years, discount_rate)
    dropout_share = (1.0 - adherence) * annual_drug_cost * (avg_time_to_dropout_days / 365.0)
    return adherent_share + dropout_share


def break_even_adherence(annual_drug_cost: float, downstream_dropout: float, downstream_adherent: float) -> Optional[float]:
    """Minimum adherence at which annual drug cost equals the per-patient avoided cost.

    Returns None if the on-therapy projection is not strictly cheaper than the
    dropout projection (denominator would be zero or negative — the program
    cannot break even at any adherence rate).
    """
    diff = downstream_dropout - downstream_adherent
    if diff <= 0:
        return None
    rate = annual_drug_cost / diff
    return float(rate)


def compute_roi(inputs: ROIInputs) -> ROIOutput:
    """Run the per-horizon ROI calculation. Pure, no I/O."""
    alpha = inputs.adherence_probability
    cd = inputs.downstream_dropout
    ca = inputs.downstream_adherent

    expected_ds = (1.0 - alpha) * cd + alpha * ca
    gross = cd - expected_ds  # equivalently: alpha * (cd - ca)

    drug = expected_drug_cost(
        alpha,
        inputs.annual_drug_cost,
        inputs.horizon_years,
        inputs.avg_time_to_dropout_days,
        inputs.discount_rate,
    )
    intervention = inputs.intervention_cost_per_patient
    net = gross - drug - intervention
    roi = (net / drug) if drug > 0 else 0.0
    be = break_even_adherence(inputs.annual_drug_cost, cd, ca)
    threshold = gross - drug

    return ROIOutput(
        horizon_years=inputs.horizon_years,
        expected_downstream=expected_ds,
        gross_benefit=gross,
        expected_drug_cost=drug,
        intervention_cost=intervention,
        net_benefit=net,
        roi=roi,
        break_even_adherence=be,
        intervention_threshold=threshold,
    )


def time_to_positive_roi(yearly_results: List[ROIOutput]) -> Optional[float]:
    """First (interpolated) year at which ROI crosses zero.

    Takes a list of ROIOutput, one per year 1..N (must be sorted ascending by
    horizon_years and start at 1). Returns:
      - 0.0 if year-1 ROI is already non-negative,
      - linearly interpolated crossing year if some later year is non-negative,
      - None if no year in the input series reaches non-negative ROI.
    """
    if not yearly_results:
        return None
    if yearly_results[0].roi >= 0:
        return float(yearly_results[0].horizon_years)
    for prev, curr in zip(yearly_results, yearly_results[1:]):
        if prev.roi < 0 and curr.roi >= 0:
            # Linear interpolation between (prev.horizon_years, prev.roi) and (curr.horizon_years, curr.roi)
            span = curr.roi - prev.roi
            if span == 0:
                return float(curr.horizon_years)
            frac = -prev.roi / span
            return float(prev.horizon_years + frac * (curr.horizon_years - prev.horizon_years))
    return None


def population_roi(per_cluster: List[Dict[str, float]], horizon_years: int) -> float:
    """Patient-count-weighted ROI across clusters at a given horizon.

    Each dict must have keys: n_patients, gross_benefit_<t>yr, expected_drug_cost_<t>yr.
    Returns net_benefit / drug_cost aggregated at population level.
    """
    total_net = 0.0
    total_drug = 0.0
    g_key = f"gross_benefit_{horizon_years}yr"
    d_key = f"expected_drug_cost_{horizon_years}yr"
    i_key = f"intervention_cost_{horizon_years}yr"
    for row in per_cluster:
        n = row["n_patients"]
        gross = row.get(g_key, 0.0)
        drug = row.get(d_key, 0.0)
        interv = row.get(i_key, 0.0)
        total_net += n * (gross - drug - interv)
        total_drug += n * drug
    return float(total_net / total_drug) if total_drug > 0 else 0.0
