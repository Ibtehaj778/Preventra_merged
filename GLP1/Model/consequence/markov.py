"""
Markov chain logic for the Downstream Cost Model.

Pure functions only — no I/O, no DataFrame ops. All parameters arrive via
the MarkovParams dataclass so the same logic can be re-used for the on-therapy
projection in the Payer ROI Synthesizer (Phase 3).

States (see docs/evidence/markov_scope_decision.md):
    S0 — Controlled glycemia (HbA1c < 7 OR on therapy)
    S1 — Uncontrolled T2D
    S2 — CKD / nephropathy
    S3 — ESRD / dialysis
    DEATH — absorbing

CV events are modeled as an independent stochastic stream layered on top of
the clinical Markov chain (per-state hazard, acute + follow-up cost).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict

import numpy as np


S0, S1, S2, S3, DEATH = 0, 1, 2, 3, 4
N_STATES = 5

STATE_NAMES = {
    S0: "Controlled",
    S1: "Uncontrolled_T2D",
    S2: "CKD",
    S3: "ESRD",
    DEATH: "Death",
}

PRIMARY_DRIVER_CHOICES = ("ESRD", "CV_event", "Uncontrolled_T2D")


@dataclass(frozen=True)
class MarkovParams:
    """All parameters required for one Markov rollout.

    Cost weights are annual USD. Transition probabilities are per-year.
    """

    # Cost weights (annual, USD)
    cost_s0_controlled: float
    cost_s1_uncontrolled: float
    cost_s2_ckd: float
    cost_s3_esrd: float
    cv_acute_cost: float
    cv_followup_annual: float

    # Clinical state transitions (annual probability)
    p_s0_to_s1_normal: float    # HbA1c < 5.7
    p_s0_to_s1_pre_dm: float    # 5.7 ≤ HbA1c < 6.5
    p_s1_to_s2: float
    p_s2_to_s3: float
    p_s3_to_death: float
    p_other_to_death: float

    # CV event hazards (annual, per state)
    cv_hazard_s0: float
    cv_hazard_s1: float
    cv_hazard_s2: float

    # GLP-1 on-therapy relative-risk modifiers (1.0 = off therapy)
    on_therapy_cv_rr: float = 1.0
    on_therapy_renal_rr: float = 1.0
    on_therapy_glycemic_rr: float = 1.0   # applies to S0→S1 while on therapy

    # Health-economics discount rate
    discount_rate: float = 0.03


def entry_state(lbxgh: float) -> int:
    """Map baseline HbA1c to the entry state at the moment of dropout.

    Threshold rationale: ≥6.5 is the ADA T2D diagnostic cutoff; patients above
    that line who drop GLP-1 are clinically uncontrolled.
    """
    if lbxgh >= 6.5:
        return S1
    return S0


def s0_to_s1_rate(lbxgh: float, params: MarkovParams) -> float:
    """HbA1c-stratified S0→S1 transition probability."""
    if lbxgh < 5.7:
        return params.p_s0_to_s1_normal
    return params.p_s0_to_s1_pre_dm


def build_transition_matrix(
    s01_rate: float, params: MarkovParams, on_therapy: bool = False
) -> np.ndarray:
    """5×5 row-stochastic transition matrix.

    On-therapy renal RR is applied to S1→S2 and S2→S3 only (per FLOW trial).
    CV events are not part of this matrix — they are a separate stream.
    """
    renal_rr = params.on_therapy_renal_rr if on_therapy else 1.0
    glycemic_rr = params.on_therapy_glycemic_rr if on_therapy else 1.0
    p_12 = params.p_s1_to_s2 * renal_rr
    p_23 = params.p_s2_to_s3 * renal_rr
    p_01 = s01_rate * glycemic_rr
    p_3d = params.p_s3_to_death
    p_d = params.p_other_to_death

    T = np.zeros((N_STATES, N_STATES))
    T[S0, S1] = p_01
    T[S0, DEATH] = p_d
    T[S0, S0] = 1.0 - p_01 - p_d

    T[S1, S2] = p_12
    T[S1, DEATH] = p_d
    T[S1, S1] = 1.0 - p_12 - p_d

    T[S2, S3] = p_23
    T[S2, DEATH] = p_d
    T[S2, S2] = 1.0 - p_23 - p_d

    T[S3, DEATH] = p_3d
    T[S3, S3] = 1.0 - p_3d

    T[DEATH, DEATH] = 1.0
    return T


def cv_hazard(p: np.ndarray, params: MarkovParams, on_therapy: bool = False) -> float:
    """State-weighted CV event hazard for a single cycle."""
    rr = params.on_therapy_cv_rr if on_therapy else 1.0
    return (
        p[S0] * params.cv_hazard_s0 * rr
        + p[S1] * params.cv_hazard_s1 * rr
        + p[S2] * params.cv_hazard_s2 * rr
    )


@dataclass
class MarkovTrajectory:
    """Per-cycle output from a single patient's rollout."""

    state_probs: np.ndarray              # (horizon + 1, N_STATES)
    cv_hazard_per_year: np.ndarray       # (horizon,)
    cv_cumulative_prob: np.ndarray       # (horizon,) — prob CV event has occurred by end of year t
    annual_cost: np.ndarray              # (horizon,) undiscounted
    discounted_cost: np.ndarray          # (horizon,)
    cost_breakdown: Dict[str, float] = field(default_factory=dict)

    @property
    def total_discounted_cost(self) -> float:
        return float(self.discounted_cost.sum())


def run_markov(
    entry: int,
    lbxgh: float,
    horizon_years: int,
    params: MarkovParams,
    on_therapy: bool = False,
) -> MarkovTrajectory:
    """Roll the Markov chain forward for `horizon_years` annual cycles.

    Cost accrual rule: a CV event in year t adds the acute episode cost in
    year t and the follow-up annual cost in every subsequent year (weighted by
    the cumulative probability that a CV event has occurred).
    """
    if horizon_years <= 0:
        raise ValueError("horizon_years must be positive")

    s01 = s0_to_s1_rate(lbxgh, params)
    T = build_transition_matrix(s01, params, on_therapy=on_therapy)

    state_probs = np.zeros((horizon_years + 1, N_STATES))
    state_probs[0, entry] = 1.0

    cv_haz = np.zeros(horizon_years)
    cv_cum = np.zeros(horizon_years)
    annual_total = np.zeros(horizon_years)
    discounted = np.zeros(horizon_years)

    breakdown = {
        "controlled_t2d": 0.0,
        "uncontrolled_t2d": 0.0,
        "ckd": 0.0,
        "esrd": 0.0,
        "cv_event": 0.0,
    }

    cv_cum_prob = 0.0
    for t in range(horizon_years):
        p = state_probs[t]

        h = cv_hazard(p, params, on_therapy=on_therapy)
        cv_haz[t] = h
        cv_acute = h * params.cv_acute_cost
        cv_followup = cv_cum_prob * params.cv_followup_annual

        c_s0 = p[S0] * params.cost_s0_controlled
        c_s1 = p[S1] * params.cost_s1_uncontrolled
        c_s2 = p[S2] * params.cost_s2_ckd
        c_s3 = p[S3] * params.cost_s3_esrd
        state_cost = c_s0 + c_s1 + c_s2 + c_s3

        annual_total[t] = state_cost + cv_acute + cv_followup
        disc = (1.0 + params.discount_rate) ** t
        discounted[t] = annual_total[t] / disc

        breakdown["controlled_t2d"] += c_s0 / disc
        breakdown["uncontrolled_t2d"] += c_s1 / disc
        breakdown["ckd"] += c_s2 / disc
        breakdown["esrd"] += c_s3 / disc
        breakdown["cv_event"] += (cv_acute + cv_followup) / disc

        cv_cum_prob = 1.0 - (1.0 - cv_cum_prob) * (1.0 - h)
        cv_cum[t] = cv_cum_prob

        state_probs[t + 1] = p @ T

    return MarkovTrajectory(
        state_probs=state_probs,
        cv_hazard_per_year=cv_haz,
        cv_cumulative_prob=cv_cum,
        annual_cost=annual_total,
        discounted_cost=discounted,
        cost_breakdown=breakdown,
    )


def primary_cost_driver(breakdown: Dict[str, float]) -> str:
    """Largest discounted-cost contributor among the three reportable categories.

    CKD cost is folded into the Uncontrolled_T2D bucket because the scope decision
    pins the dashboard categories at {ESRD, CV_event, Uncontrolled_T2D}.
    """
    candidates = {
        "ESRD": breakdown.get("esrd", 0.0),
        "CV_event": breakdown.get("cv_event", 0.0),
        "Uncontrolled_T2D": breakdown.get("uncontrolled_t2d", 0.0)
        + breakdown.get("ckd", 0.0),
    }
    return max(candidates, key=candidates.get)
