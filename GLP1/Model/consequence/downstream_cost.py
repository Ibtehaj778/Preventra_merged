"""
Downstream Cost Model — Phase 1 of the Consequence Model layer.

Reads:
    Backend/data/GLP1_FINAL_WITH_SURVIVAL.csv   (patient baselines + dropout timing)
    Backend/data/GLP1_SEGMENTED.csv             (segment labels — joined via row order)
    docs/evidence/parameter_registry.csv             (sourced clinical/economic params)

Writes:
    Backend/data/progression_cost.csv           (per-patient projected downstream cost)

Run from project root:
    python -m Model.consequence.downstream_cost
or:
    python Model/consequence/downstream_cost.py

Phase 1 produces the dropout-side projection only (cost if the patient drops
out / has dropped out). The on-therapy comparator and ROI synthesis live in
Phase 3 (Model/consequence/payer_roi.py).
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict

import numpy as np
import pandas as pd

# Path setup so the script works whether invoked as `python -m` or directly.
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Model.consequence.markov import (  # noqa: E402
    MarkovParams,
    entry_state,
    primary_cost_driver,
    run_markov,
)
from Model.consequence.registry import (  # noqa: E402
    BASE_REGISTRY_PATH as REGISTRY_PATH,
    load_registry,
)

DATA_DIR = PROJECT_ROOT / "Backend" / "data"
SURVIVAL_PATH = DATA_DIR / "GLP1_FINAL_WITH_SURVIVAL.csv"
SEGMENTED_PATH = DATA_DIR / "GLP1_SEGMENTED.csv"
OUTPUT_PATH = DATA_DIR / "progression_cost.csv"

DEFAULT_HORIZON = 5
SENSITIVITY_HORIZON = 10


def build_params(
    reg: Dict[str, float], payer_type: str = "medicare"
) -> MarkovParams:
    """Construct the MarkovParams from the registry.

    payer_type: "medicare" (default, USRDS-based) or "commercial" (HCCI-based).
    """
    if payer_type == "commercial":
        esrd_cost = reg["esrd_annual_cost_commercial_usd"]
    else:
        esrd_cost = reg["esrd_annual_cost_usd"]

    ckd_cost = 0.5 * (
        reg["ckd_stage3_annual_cost_usd"] + reg["ckd_stage4_5_annual_cost_usd"]
    )

    return MarkovParams(
        cost_s0_controlled=reg["controlled_t2d_annual_cost_usd"],
        cost_s1_uncontrolled=reg["uncontrolled_t2d_annual_cost_usd"],
        cost_s2_ckd=ckd_cost,
        cost_s3_esrd=esrd_cost,
        cv_acute_cost=reg["cv_event_cost_acute_usd"],
        cv_followup_annual=reg["cv_event_followup_annual_cost_usd"],
        p_s0_to_s1_normal=reg["trans_s0_to_s1_per_year_normal_hba1c"],
        p_s0_to_s1_pre_dm=reg["trans_s0_to_s1_per_year_low_hba1c"],
        p_s1_to_s2=reg["trans_s1_to_s2_per_year"],
        p_s2_to_s3=reg["trans_s2_to_s3_per_year"],
        p_s3_to_death=reg["trans_s3_to_death_per_year"],
        p_other_to_death=reg["trans_any_to_death_per_year_baseline"],
        cv_hazard_s0=reg["trans_s0_to_s4_per_year"],
        cv_hazard_s1=reg["trans_s1_to_s4_per_year"],
        cv_hazard_s2=reg["trans_s2_to_s4_per_year"],
        on_therapy_cv_rr=reg["glp1_efficacy_residual_complication_rr"],
        on_therapy_renal_rr=reg["glp1_efficacy_residual_renal_rr"],
        on_therapy_glycemic_rr=reg.get("glp1_efficacy_glycemic_progression_rr", 1.0),
        discount_rate=reg["discount_rate_annual"],
    )


def load_patient_frame() -> pd.DataFrame:
    """Join survival + segmented frames by row order (consistent with backend).

    The downstream pipeline relies on row-order alignment: GLP1_SEGMENTED is the
    same row order as GLP1_FINAL_WITH_SURVIVAL. We add patient_idx as the
    canonical ID, mirroring Backend/scripts/migrate_csv_to_mongo.py.
    """
    df_surv = pd.read_csv(SURVIVAL_PATH).reset_index(drop=True)
    df_surv.insert(0, "patient_idx", df_surv.index)
    return df_surv


def project_patient(
    lbxgh: float,
    bmxbmi: float,
    params: MarkovParams,
    horizons: tuple[int, ...] = (DEFAULT_HORIZON, SENSITIVITY_HORIZON),
) -> dict:
    """Run the Markov rollout for one patient at all requested horizons.

    Returns a dict with horizon-suffixed cost columns + state-probability
    summary columns. The longest horizon's trajectory is used for the
    primary_cost_driver and probability summaries.
    """
    entry = entry_state(lbxgh)
    out: dict = {"entry_state": entry, "entry_state_name": _state_label(entry)}

    longest = max(horizons)
    trajectory = run_markov(entry, lbxgh, longest, params, on_therapy=False)

    for h in horizons:
        # Discounted cumulative cost at end of year h
        out[f"expected_downstream_cost_{h}yr"] = float(
            trajectory.discounted_cost[:h].sum()
        )

    # State probability snapshots at the primary horizon
    state_at_default = trajectory.state_probs[DEFAULT_HORIZON]
    out["esrd_probability_5yr"] = float(state_at_default[3])
    out["death_probability_5yr"] = float(state_at_default[4])
    # CV event probability over the primary horizon
    out["cv_event_probability_5yr"] = float(
        trajectory.cv_cumulative_prob[DEFAULT_HORIZON - 1]
    )

    # Primary cost driver — computed on a 5-year breakdown, not the 10-year one.
    breakdown_5yr = _breakdown_at_horizon(trajectory, DEFAULT_HORIZON, params)
    out["primary_cost_driver"] = primary_cost_driver(breakdown_5yr)
    out["cost_share_esrd_5yr"] = _share(breakdown_5yr, "esrd")
    out["cost_share_cv_5yr"] = _share(breakdown_5yr, "cv_event")
    out["cost_share_uncontrolled_t2d_5yr"] = _share(
        breakdown_5yr, "uncontrolled_t2d", "ckd"
    )

    return out


def _state_label(s: int) -> str:
    names = {0: "Controlled", 1: "Uncontrolled_T2D"}
    return names.get(s, f"State_{s}")


def _breakdown_at_horizon(
    trajectory, horizon: int, params: MarkovParams
) -> Dict[str, float]:
    """Recompute the cost breakdown restricted to the first `horizon` years."""
    bd = {"controlled_t2d": 0.0, "uncontrolled_t2d": 0.0, "ckd": 0.0, "esrd": 0.0, "cv_event": 0.0}
    for t in range(horizon):
        p = trajectory.state_probs[t]
        disc = (1.0 + params.discount_rate) ** t
        bd["controlled_t2d"] += p[0] * params.cost_s0_controlled / disc
        bd["uncontrolled_t2d"] += p[1] * params.cost_s1_uncontrolled / disc
        bd["ckd"] += p[2] * params.cost_s2_ckd / disc
        bd["esrd"] += p[3] * params.cost_s3_esrd / disc
        cv_acute = trajectory.cv_hazard_per_year[t] * params.cv_acute_cost
        cv_followup = (
            trajectory.cv_cumulative_prob[t - 1] if t > 0 else 0.0
        ) * params.cv_followup_annual
        bd["cv_event"] += (cv_acute + cv_followup) / disc
    return bd


def _share(breakdown: Dict[str, float], *keys: str) -> float:
    total = sum(breakdown.values())
    if total <= 0:
        return 0.0
    return float(sum(breakdown[k] for k in keys) / total)


def build_progression_frame(
    df_patients: pd.DataFrame, params: MarkovParams
) -> pd.DataFrame:
    """Apply the Markov rollout per patient and assemble the output frame."""
    rows = []
    for r in df_patients.itertuples(index=False):
        proj = project_patient(r.LBXGH, r.BMXBMI, params)
        rows.append(
            {
                "patient_idx": int(r.patient_idx),
                "cluster": int(r.cluster),
                "segment_short": getattr(r, "segment_short", None),
                "lbxgh_baseline": float(r.LBXGH),
                "bmxbmi_baseline": float(r.BMXBMI),
                "time_to_dropout_days": float(r.time_to_dropout),
                "event_occurred": int(r.event_occurred),
                **proj,
            }
        )
    return pd.DataFrame(rows)


def cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    """Per-cluster aggregate view used for the sanity check and the API."""
    g = df.groupby("cluster")
    summary = pd.DataFrame(
        {
            "n_patients": g.size(),
            "avg_downstream_cost_5yr": g["expected_downstream_cost_5yr"].mean(),
            "avg_downstream_cost_10yr": g["expected_downstream_cost_10yr"].mean(),
            "esrd_probability_5yr": g["esrd_probability_5yr"].mean(),
            "cv_event_probability_5yr": g["cv_event_probability_5yr"].mean(),
            "total_population_cost_5yr": g["expected_downstream_cost_5yr"].sum(),
        }
    ).reset_index()
    return summary


def main(payer_type: str = "medicare") -> Path:
    print(f"[load] parameter registry: {REGISTRY_PATH.relative_to(PROJECT_ROOT)}")
    reg = load_registry()
    params = build_params(reg, payer_type=payer_type)

    print(f"[load] patients:           {SURVIVAL_PATH.relative_to(PROJECT_ROOT)}")
    df_patients = load_patient_frame()
    print(f"       -> {len(df_patients):,} patients")

    print(f"[run]  5/10-year Markov rollout (payer={payer_type})...")
    df_out = build_progression_frame(df_patients, params)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUTPUT_PATH, index=False)
    print(f"[ok]   wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)} ({len(df_out):,} rows)")

    print("\n[check] per-cluster avg 5-yr downstream cost:")
    summary = cluster_summary(df_out)
    print(summary.to_string(index=False))

    drivers = df_out["primary_cost_driver"].value_counts(normalize=True).to_dict()
    print("\n        primary cost driver share (population):")
    for k, v in drivers.items():
        print(f"          {k:<20} {v:6.1%}")

    return OUTPUT_PATH


if __name__ == "__main__":
    main()
