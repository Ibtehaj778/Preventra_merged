"""
Rebound trajectory logic for Phase 2 — Metabolic Rebound Risk Engine.

Pure functions only. The same trajectory math is used for the dashboard line
chart (per-cluster expected HbA1c over months 0–12 post-dropout) and the
per-patient severity score.

Model (v1):
    1. Estimate on-therapy HbA1c reduction attained by the moment of dropout,
       prorated by time-to-dropout vs. steady-state timing (~90 days for GLP-1s).
    2. HbA1c at dropout = baseline − reduction_attained.
    3. Rebound is linear at `rate_per_month` until the asymptote
       (reduction_attained × plateau_pct_of_loss) is reached, then flat.
    4. BMI follows the same shape with its own rate and plateau.
    5. Threshold crossings (6.5 for pre-DM → T2D, 8.0 for T2D → uncontrolled)
       give per-patient probabilities and time-to-crossing.

The linear-to-plateau approximation is documented in the parameter registry
(`hba1c_rebound_rate_per_month` notes). Biological reality is closer to a
monoexponential approach; a v2 upgrade is gated behind an explicit flag.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional

import numpy as np


@dataclass(frozen=True)
class ReboundParams:
    """All parameters required to project a single patient's rebound trajectory."""

    # HbA1c rebound
    hba1c_rate_per_month: float       # %/month, linear segment
    hba1c_plateau_pct: float          # fraction of on-therapy gain that is regained

    # BMI rebound
    bmi_rate_per_month: float         # kg/m²/month
    bmi_plateau_pct: float            # fraction of on-therapy weight loss regained

    # GLP-1 onset
    steady_state_days: float          # days to reach near-full benefit

    # Clinical thresholds
    t2d_threshold_hba1c: float        # 6.5
    uncontrolled_threshold_hba1c: float  # 8.0

    # Background T2D incidence (used as floor for p_new_t2d_12mo when rebound stays sub-threshold)
    t2d_incidence_low_per_year: float    # HbA1c 5.7–5.9
    t2d_incidence_high_per_year: float   # HbA1c 6.0–6.4

    # Uncontrolled progression (used as floor for p_uncontrolled_12mo)
    uncontrolled_progression_per_year: float  # HbA1c 7.0–7.9 → ≥8.0 in one year

    # Clinical floor on attainable HbA1c — trial reductions were measured in T2D
    # cohorts (baseline ~8); applying full reduction to pre-DM baselines overshoots.
    # Lower limit of normal HbA1c is ~5.0; we cap reduction so on-therapy HbA1c
    # cannot drop below this floor.
    hba1c_floor: float = 5.0


# Per-molecule on-therapy efficacy. Keyed by the same uppercase strings used
# in GLP1_FINAL_WITH_SURVIVAL.csv. Values come from the parameter registry —
# this dict is built by load_efficacy_from_registry().
MoleculeEfficacy = dict[str, dict[str, float]]


def reduction_attained(
    trial_reduction: float,
    time_to_dropout_days: float,
    steady_state_days: float,
    baseline_hba1c: Optional[float] = None,
    floor: float = 5.0,
) -> float:
    """Prorate the trial-grade reduction by how long the patient stayed on therapy.

    Patients who drop before steady state (~12 weeks) have attained less than
    the full clinical benefit; the rebound model should not let them lose
    more than they actually gained.

    If `baseline_hba1c` is supplied, the reduction is also capped so that the
    resulting on-therapy HbA1c does not fall below `floor` (default 5.0,
    approximating the lower limit of normal). This corrects for the fact that
    trial benchmarks come from T2D cohorts (baseline ~8) and overshoot when
    applied to pre-DM/normal-glycemia patients in our synthetic cohort.
    """
    if time_to_dropout_days <= 0:
        return 0.0
    fraction = min(time_to_dropout_days / steady_state_days, 1.0)
    reduction = trial_reduction * fraction
    if baseline_hba1c is not None:
        reduction = min(reduction, max(0.0, baseline_hba1c - floor))
    return reduction


def hba1c_trajectory(
    baseline: float,
    trial_reduction: float,
    time_to_dropout_days: float,
    months_post_dropout: np.ndarray,
    params: ReboundParams,
) -> np.ndarray:
    """Project HbA1c forward for `months_post_dropout` (vector of months).

    Returns an array the same shape as the input months vector.
    """
    attained = reduction_attained(
        trial_reduction,
        time_to_dropout_days,
        params.steady_state_days,
        baseline_hba1c=baseline,
        floor=params.hba1c_floor,
    )
    hba1c_at_dropout = baseline - attained
    asymptote_rebound = attained * params.hba1c_plateau_pct

    months = np.maximum(months_post_dropout, 0.0)
    rebound = np.minimum(params.hba1c_rate_per_month * months, asymptote_rebound)
    return hba1c_at_dropout + rebound


def bmi_trajectory(
    baseline_bmi: float,
    molecule_weight_loss_pct: float,
    time_to_dropout_days: float,
    months_post_dropout: np.ndarray,
    params: ReboundParams,
) -> np.ndarray:
    """Project BMI forward.

    on-therapy BMI ≈ baseline × (1 - weight_loss_pct/100), prorated by time
    on therapy. Rebound climbs back toward baseline at `bmi_rate_per_month`,
    capped at the asymptote (plateau_pct of the regain pool).
    """
    if time_to_dropout_days <= 0:
        loss_fraction = 0.0
    else:
        loss_fraction = min(time_to_dropout_days / params.steady_state_days, 1.0)

    bmi_loss = baseline_bmi * (molecule_weight_loss_pct / 100.0) * loss_fraction
    bmi_at_dropout = baseline_bmi - bmi_loss
    asymptote_regain = bmi_loss * params.bmi_plateau_pct

    months = np.maximum(months_post_dropout, 0.0)
    regain = np.minimum(params.bmi_rate_per_month * months, asymptote_regain)
    return bmi_at_dropout + regain


def dm_status_at_dropout(hba1c_at_dropout: float, params: ReboundParams) -> str:
    """One of {"normal", "pre_dm", "t2d", "uncontrolled_t2d"}."""
    if hba1c_at_dropout < 5.7:
        return "normal"
    if hba1c_at_dropout < params.t2d_threshold_hba1c:
        return "pre_dm"
    if hba1c_at_dropout < params.uncontrolled_threshold_hba1c:
        return "t2d"
    return "uncontrolled_t2d"


def months_to_threshold(
    hba1c_at_dropout: float,
    asymptote_rebound: float,
    threshold: float,
    rate_per_month: float,
) -> Optional[float]:
    """Time in months until HbA1c trajectory crosses `threshold`.

    Returns None if the asymptote is below the threshold (patient never reaches it
    under the model) or if already at/above threshold at dropout.
    """
    if rate_per_month <= 0:
        return None
    if hba1c_at_dropout >= threshold:
        return 0.0
    max_value = hba1c_at_dropout + asymptote_rebound
    if max_value < threshold:
        return None
    return (threshold - hba1c_at_dropout) / rate_per_month


def p_new_t2d_12mo(
    hba1c_at_dropout: float,
    expected_hba1c_12mo: float,
    params: ReboundParams,
) -> Optional[float]:
    """Probability the patient develops new-onset T2D within 12 months.

    Returns None for patients who are not pre-DM at dropout (T2D and uncontrolled
    T2D patients have a different metric: `p_uncontrolled_12mo`).
    """
    if hba1c_at_dropout >= params.t2d_threshold_hba1c:
        return None
    if hba1c_at_dropout < 5.7:
        # Sub-pre-DM: only the background rate applies, and the trajectory rarely crosses.
        if expected_hba1c_12mo >= params.t2d_threshold_hba1c:
            return 1.0
        return params.t2d_incidence_low_per_year * 0.5  # very low baseline

    # Pre-DM range
    if expected_hba1c_12mo >= params.t2d_threshold_hba1c:
        return 1.0

    # Trajectory does not cross; use DPP-stratified baseline incidence
    if hba1c_at_dropout >= 6.0:
        return params.t2d_incidence_high_per_year
    return params.t2d_incidence_low_per_year


def p_uncontrolled_12mo(
    hba1c_at_dropout: float,
    expected_hba1c_12mo: float,
    params: ReboundParams,
) -> Optional[float]:
    """Probability the patient becomes uncontrolled (HbA1c ≥ 8.0) within 12 months."""
    if hba1c_at_dropout < params.t2d_threshold_hba1c:
        return None
    if hba1c_at_dropout >= params.uncontrolled_threshold_hba1c:
        return 1.0
    if expected_hba1c_12mo >= params.uncontrolled_threshold_hba1c:
        return 1.0
    return params.uncontrolled_progression_per_year


def rebound_severity_score(
    hba1c_at_dropout: float,
    expected_hba1c_12mo: float,
    bmi_at_dropout: float,
    expected_bmi_12mo: float,
    p_threshold_crossing: Optional[float],
) -> float:
    """Composite severity in [0, 1].

    Components:
      - 40%: HbA1c rebound magnitude, normalized to a 2.0-point regain ceiling.
      - 30%: BMI rebound magnitude, normalized to a 5.0 kg/m² regain ceiling.
      - 30%: probability of crossing the clinical threshold (T2D or uncontrolled).
    """
    hba1c_rebound = max(0.0, expected_hba1c_12mo - hba1c_at_dropout)
    bmi_rebound = max(0.0, expected_bmi_12mo - bmi_at_dropout)

    hba1c_norm = min(hba1c_rebound / 2.0, 1.0)
    bmi_norm = min(bmi_rebound / 5.0, 1.0)
    threshold_norm = float(p_threshold_crossing) if p_threshold_crossing is not None else 0.0

    score = 0.4 * hba1c_norm + 0.3 * bmi_norm + 0.3 * threshold_norm
    return float(min(max(score, 0.0), 1.0))
