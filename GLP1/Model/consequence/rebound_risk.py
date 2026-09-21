"""
Rebound Risk Engine — Phase 2 of the Consequence Model layer.

Reads:
    Backend/data/GLP1_FINAL_WITH_SURVIVAL.csv   (LBXGH, BMXBMI, assigned_molecule, time_to_dropout)
    docs/evidence/parameter_registry.csv        (rebound rates, plateaus, molecule efficacy)

Writes:
    Backend/data/rebound_risk.csv               (per-patient rebound projection)

Run from project root:
    python -m Model.consequence.rebound_risk
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, Optional

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
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


def cluster_median_dropout(df_patients: pd.DataFrame) -> Dict[int, float]:
    """Median time_to_dropout among observed dropouts (event_occurred == 1) per cluster.

    For clusters with too few observed dropouts, falls back to the cluster's
    overall median time_to_dropout. The value is clipped to [30, 150] so that
    the 'median' scenario stays strictly between the early/late bookends.
    """
    out: Dict[int, float] = {}
    for cluster, sub in df_patients.groupby("cluster"):
        dropouts = sub[sub["event_occurred"] == 1]
        if len(dropouts) >= 20:
            med = float(dropouts["time_to_dropout"].median())
        else:
            med = float(sub["time_to_dropout"].median())
        out[int(cluster)] = float(np.clip(med, SENSITIVITY_EARLY_DAY + 1, SENSITIVITY_LATE_DAY - 1))
    return out

REGISTRY_PATH = PROJECT_ROOT / "docs" / "evidence" / "parameter_registry.csv"
DATA_DIR = PROJECT_ROOT / "Backend" / "data"
SURVIVAL_PATH = DATA_DIR / "GLP1_FINAL_WITH_SURVIVAL.csv"
OUTPUT_PATH = DATA_DIR / "rebound_risk.csv"
TRAJECTORY_PATH = DATA_DIR / "rebound_trajectory.csv"
SENSITIVITY_PATH = DATA_DIR / "rebound_sensitivity.csv"

TRAJECTORY_MONTHS = (0.0, 3.0, 6.0, 9.0, 12.0)
SENSITIVITY_SCENARIOS = ("early", "median", "late")
SENSITIVITY_EARLY_DAY = 30.0
SENSITIVITY_LATE_DAY = 150.0


def load_registry(path: Path = REGISTRY_PATH) -> Dict[str, float]:
    df = pd.read_csv(path)
    return {row.parameter_name: float(row.value) for row in df.itertuples()}


def build_params(reg: Dict[str, float]) -> ReboundParams:
    return ReboundParams(
        hba1c_rate_per_month=reg["hba1c_rebound_rate_per_month"],
        hba1c_plateau_pct=reg["hba1c_rebound_plateau_pct_of_loss"],
        bmi_rate_per_month=reg["bmi_rebound_rate_per_month"],
        bmi_plateau_pct=reg["bmi_rebound_plateau_pct_of_loss"],
        steady_state_days=reg["glp1_steady_state_days"],
        t2d_threshold_hba1c=reg["t2d_threshold_hba1c"],
        uncontrolled_threshold_hba1c=reg["uncontrolled_t2d_threshold_hba1c"],
        t2d_incidence_low_per_year=reg["t2d_incidence_pre_dm_low_per_year"],
        t2d_incidence_high_per_year=reg["t2d_incidence_pre_dm_high_per_year"],
        uncontrolled_progression_per_year=reg["trans_s0_to_s1_per_year_mid_hba1c"],
    )


def load_molecule_efficacy(reg: Dict[str, float]) -> Dict[str, Dict[str, float]]:
    """Build {MOLECULE: {hba1c_reduction, weight_loss_pct}} from the registry."""
    molecules = ["semaglutide", "tirzepatide", "liraglutide", "dulaglutide"]
    return {
        m.upper(): {
            "hba1c_reduction": reg[f"glp1_efficacy_hba1c_reduction_{m}"],
            "weight_loss_pct": reg[f"glp1_efficacy_weight_loss_pct_{m}"],
        }
        for m in molecules
    }


def project_patient(
    lbxgh: float,
    bmxbmi: float,
    molecule: str,
    time_to_dropout_days: float,
    efficacy: Dict[str, Dict[str, float]],
    params: ReboundParams,
) -> dict:
    """Run the 12-month rebound projection for one patient."""
    mol_data = efficacy.get(molecule.upper())
    if mol_data is None:
        # Fallback to semaglutide if unknown molecule — should not happen with cleaned data
        mol_data = efficacy["SEMAGLUTIDE"]

    trial_hba1c_reduction = mol_data["hba1c_reduction"]
    trial_weight_loss_pct = mol_data["weight_loss_pct"]

    attained = reduction_attained(
        trial_hba1c_reduction,
        time_to_dropout_days,
        params.steady_state_days,
        baseline_hba1c=lbxgh,
        floor=params.hba1c_floor,
    )
    hba1c_at_dropout = lbxgh - attained
    bmi_at_dropout = bmxbmi - bmxbmi * (trial_weight_loss_pct / 100.0) * min(
        time_to_dropout_days / params.steady_state_days, 1.0
    )

    months = np.array([6.0, 12.0])
    hba1c_traj = hba1c_trajectory(lbxgh, trial_hba1c_reduction, time_to_dropout_days, months, params)
    bmi_traj = bmi_trajectory(bmxbmi, trial_weight_loss_pct, time_to_dropout_days, months, params)
    expected_hba1c_6mo = float(hba1c_traj[0])
    expected_hba1c_12mo = float(hba1c_traj[1])
    expected_bmi_6mo = float(bmi_traj[0])
    expected_bmi_12mo = float(bmi_traj[1])

    status = dm_status_at_dropout(hba1c_at_dropout, params)

    p_t2d = p_new_t2d_12mo(hba1c_at_dropout, expected_hba1c_12mo, params)
    p_unc = p_uncontrolled_12mo(hba1c_at_dropout, expected_hba1c_12mo, params)

    if status in ("normal", "pre_dm"):
        asymptote = attained * params.hba1c_plateau_pct
        m_to_thr = months_to_threshold(
            hba1c_at_dropout, asymptote, params.t2d_threshold_hba1c, params.hba1c_rate_per_month
        )
    else:
        m_to_thr = None

    p_crossing: Optional[float] = p_t2d if p_t2d is not None else p_unc
    severity = rebound_severity_score(
        hba1c_at_dropout,
        expected_hba1c_12mo,
        bmi_at_dropout,
        expected_bmi_12mo,
        p_crossing,
    )

    return {
        "dm_status_at_dropout": status,
        "hba1c_at_dropout": round(hba1c_at_dropout, 3),
        "bmi_at_dropout": round(bmi_at_dropout, 2),
        "expected_hba1c_6mo": round(expected_hba1c_6mo, 3),
        "expected_hba1c_12mo": round(expected_hba1c_12mo, 3),
        "expected_bmi_6mo": round(expected_bmi_6mo, 2),
        "expected_bmi_12mo": round(expected_bmi_12mo, 2),
        "p_new_t2d_12mo": p_t2d,
        "p_uncontrolled_12mo": p_unc,
        "months_to_t2d_threshold": m_to_thr,
        "rebound_severity_score": round(severity, 4),
    }


def load_patient_frame() -> pd.DataFrame:
    df = pd.read_csv(SURVIVAL_PATH).reset_index(drop=True)
    df.insert(0, "patient_idx", df.index)
    return df


def build_rebound_frame(
    df_patients: pd.DataFrame,
    efficacy: Dict[str, Dict[str, float]],
    params: ReboundParams,
) -> pd.DataFrame:
    rows = []
    for r in df_patients.itertuples(index=False):
        proj = project_patient(
            lbxgh=float(r.LBXGH),
            bmxbmi=float(r.BMXBMI),
            molecule=str(r.assigned_molecule),
            time_to_dropout_days=float(r.time_to_dropout),
            efficacy=efficacy,
            params=params,
        )
        rows.append(
            {
                "patient_idx": int(r.patient_idx),
                "cluster": int(r.cluster),
                "segment_short": getattr(r, "segment_short", None),
                "assigned_molecule": str(r.assigned_molecule),
                "lbxgh_baseline": float(r.LBXGH),
                "bmxbmi_baseline": float(r.BMXBMI),
                "time_to_dropout_days": float(r.time_to_dropout),
                **proj,
            }
        )
    return pd.DataFrame(rows)


def cluster_summary(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby("cluster")
    return pd.DataFrame(
        {
            "n_patients": g.size(),
            "avg_hba1c_at_dropout": g["hba1c_at_dropout"].mean(),
            "avg_expected_hba1c_12mo": g["expected_hba1c_12mo"].mean(),
            "avg_bmi_at_dropout": g["bmi_at_dropout"].mean(),
            "avg_expected_bmi_12mo": g["expected_bmi_12mo"].mean(),
            "avg_severity_score": g["rebound_severity_score"].mean(),
            "p_new_t2d_12mo_mean": g["p_new_t2d_12mo"].mean(),
            "p_uncontrolled_12mo_mean": g["p_uncontrolled_12mo"].mean(),
        }
    ).reset_index()


def build_trajectory_frame(
    df_patients: pd.DataFrame,
    efficacy: Dict[str, Dict[str, float]],
    params: ReboundParams,
    medians: Dict[int, float],
) -> pd.DataFrame:
    """Per-cluster × scenario × month trajectory used by the dashboard line chart.

    Three scenarios per cluster: early dropout (day 30), median (cluster-specific),
    late (day 150). For each, every patient in the cluster has their
    time_to_dropout overwritten by the scenario value and the trajectory
    averaged across patients in that cluster.
    """
    months = np.array(TRAJECTORY_MONTHS)
    rows = []
    for cluster, sub in df_patients.groupby("cluster"):
        scenario_days = {
            "early":  SENSITIVITY_EARLY_DAY,
            "median": medians[int(cluster)],
            "late":   SENSITIVITY_LATE_DAY,
        }
        for scenario, day in scenario_days.items():
            hba1c_acc = np.zeros_like(months)
            bmi_acc = np.zeros_like(months)
            n = 0
            for r in sub.itertuples(index=False):
                mol = efficacy.get(str(r.assigned_molecule).upper(), efficacy["SEMAGLUTIDE"])
                hba1c_traj = hba1c_trajectory(
                    float(r.LBXGH), mol["hba1c_reduction"], day, months, params
                )
                bmi_traj = bmi_trajectory(
                    float(r.BMXBMI), mol["weight_loss_pct"], day, months, params
                )
                hba1c_acc += hba1c_traj
                bmi_acc += bmi_traj
                n += 1
            hba1c_avg = hba1c_acc / max(n, 1)
            bmi_avg = bmi_acc / max(n, 1)
            for m, h, b in zip(months, hba1c_avg, bmi_avg):
                rows.append({
                    "cluster":     int(cluster),
                    "scenario":    scenario,
                    "dropout_day": float(day),
                    "month":       float(m),
                    "avg_hba1c":   round(float(h), 4),
                    "avg_bmi":     round(float(b), 3),
                    "n_patients":  int(n),
                })
    return pd.DataFrame(rows)


def build_sensitivity_frame(
    df_patients: pd.DataFrame,
    efficacy: Dict[str, Dict[str, float]],
    params: ReboundParams,
    medians: Dict[int, float],
) -> pd.DataFrame:
    """Per-cluster × scenario summary at the 12-month horizon.

    Re-projects every patient at the scenario's dropout day, then aggregates.
    """
    rows = []
    for cluster, sub in df_patients.groupby("cluster"):
        scenario_days = {
            "early":  SENSITIVITY_EARLY_DAY,
            "median": medians[int(cluster)],
            "late":   SENSITIVITY_LATE_DAY,
        }
        for scenario, day in scenario_days.items():
            severities, p_t2ds, p_uncs, hba1c_drops, hba1c_12s = [], [], [], [], []
            for r in sub.itertuples(index=False):
                proj = project_patient(
                    lbxgh=float(r.LBXGH),
                    bmxbmi=float(r.BMXBMI),
                    molecule=str(r.assigned_molecule),
                    time_to_dropout_days=day,
                    efficacy=efficacy,
                    params=params,
                )
                severities.append(proj["rebound_severity_score"])
                hba1c_drops.append(proj["hba1c_at_dropout"])
                hba1c_12s.append(proj["expected_hba1c_12mo"])
                if proj["p_new_t2d_12mo"] is not None:
                    p_t2ds.append(proj["p_new_t2d_12mo"])
                if proj["p_uncontrolled_12mo"] is not None:
                    p_uncs.append(proj["p_uncontrolled_12mo"])

            rows.append({
                "cluster":                  int(cluster),
                "scenario":                 scenario,
                "dropout_day":              float(day),
                "n_patients":               len(sub),
                "avg_hba1c_at_dropout":     round(float(np.mean(hba1c_drops)), 3),
                "avg_expected_hba1c_12mo":  round(float(np.mean(hba1c_12s)), 3),
                "avg_severity_score":       round(float(np.mean(severities)), 4),
                "p_new_t2d_12mo_mean":      round(float(np.mean(p_t2ds)), 4) if p_t2ds else None,
                "p_uncontrolled_12mo_mean": round(float(np.mean(p_uncs)), 4) if p_uncs else None,
                "n_pre_dm":                 len(p_t2ds),
                "n_t2d":                    len(p_uncs),
            })
    return pd.DataFrame(rows)


def main() -> Path:
    print(f"[load] parameter registry: {REGISTRY_PATH.relative_to(PROJECT_ROOT)}")
    reg = load_registry()
    params = build_params(reg)
    efficacy = load_molecule_efficacy(reg)

    print(f"[load] patients:           {SURVIVAL_PATH.relative_to(PROJECT_ROOT)}")
    df_patients = load_patient_frame()
    print(f"       -> {len(df_patients):,} patients")

    print("[run]  12-month rebound projection (rate-to-plateau, linear)...")
    df_out = build_rebound_frame(df_patients, efficacy, params)

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df_out.to_csv(OUTPUT_PATH, index=False)
    print(f"[ok]   wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)} ({len(df_out):,} rows)")

    print("\n[check] per-cluster rebound summary:")
    summary = cluster_summary(df_out)
    print(summary.round(3).to_string(index=False))

    status_dist = df_out["dm_status_at_dropout"].value_counts(normalize=True).to_dict()
    print("\n        DM status at dropout (population share):")
    for k, v in status_dist.items():
        print(f"          {k:<18} {v:6.1%}")

    medians = cluster_median_dropout(df_patients)
    print("\n[run]  per-cluster trajectory (5 monthly points, 3 scenarios)...")
    df_traj = build_trajectory_frame(df_patients, efficacy, params, medians)
    df_traj.to_csv(TRAJECTORY_PATH, index=False)
    print(f"[ok]   wrote {TRAJECTORY_PATH.relative_to(PROJECT_ROOT)} ({len(df_traj):,} rows)")

    print("[run]  sensitivity analysis: early(30) / median / late(150) per cluster...")
    df_sens = build_sensitivity_frame(df_patients, efficacy, params, medians)
    df_sens.to_csv(SENSITIVITY_PATH, index=False)
    print(f"[ok]   wrote {SENSITIVITY_PATH.relative_to(PROJECT_ROOT)} ({len(df_sens):,} rows)")

    print("\n[check] sensitivity — 12-month severity by cluster x scenario:")
    pivot = df_sens.pivot(
        index="cluster",
        columns="scenario",
        values="avg_severity_score",
    )[list(SENSITIVITY_SCENARIOS)]
    print(pivot.round(3).to_string())

    return OUTPUT_PATH


if __name__ == "__main__":
    main()
