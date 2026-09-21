"""
Payer ROI Synthesizer — Phase 3 of the Consequence Model layer.

Combines the model-derived adherence probability, the Phase-1 Markov projection
(dropout-side and on-therapy-side), and the per-molecule drug cost into a
per-cluster ROI with break-even adherence rate, intervention cost threshold,
and time-to-positive ROI.

Reads:
    Backend/data/GLP1_FINAL_WITH_SURVIVAL.csv   (patients, time_to_dropout, molecule)
    docs/evidence/parameter_registry.csv             (transitions, costs, efficacy)

Writes:
    Backend/data/payer_roi.csv                  (per-cluster ROI, 4 rows)
    Backend/data/payer_roi_yearly.csv           (per-cluster x year, 20 rows)

Run from project root:
    python -m Model.consequence.payer_roi
"""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Dict, List

import numpy as np
import pandas as pd

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from Model.consequence.downstream_cost import (  # noqa: E402
    build_params as build_markov_params,
)
from Model.consequence.markov import entry_state, run_markov  # noqa: E402
from Model.consequence.registry import (  # noqa: E402
    DEFAULT_PAYER_TYPE,
    available_payer_types,
    load_registry,
)
from Model.consequence.roi import (  # noqa: E402
    ROIInputs,
    annuity_factor,
    break_even_adherence,
    compute_roi,
    expected_drug_cost,
    time_to_positive_roi,
)


DATA_DIR = PROJECT_ROOT / "Backend" / "data"
SURVIVAL_PATH = DATA_DIR / "GLP1_FINAL_WITH_SURVIVAL.csv"
OUTPUT_PATH = DATA_DIR / "payer_roi.csv"
YEARLY_PATH = DATA_DIR / "payer_roi_yearly.csv"

PRIMARY_HORIZONS = (1, 3, 5, 10)
YEARLY_HORIZONS = tuple(range(1, 11))   # 1..10 — enables time-to-positive interpolation
DEFAULT_INTERVENTION_COST = 500.0  # placeholder; surfaced as a slider input on the dashboard


_MOLECULE_TO_REG_KEY = {
    "SEMAGLUTIDE": "glp1_wac_semaglutide_annual_usd",
    "TIRZEPATIDE": "glp1_wac_tirzepatide_annual_usd",
    "LIRAGLUTIDE": "glp1_wac_liraglutide_annual_usd",
    "DULAGLUTIDE": "glp1_wac_dulaglutide_annual_usd",
}


def load_patient_frame() -> pd.DataFrame:
    df = pd.read_csv(SURVIVAL_PATH).reset_index(drop=True)
    df.insert(0, "patient_idx", df.index)
    return df


def patient_drug_cost_annual(molecule: str, reg: Dict[str, float]) -> float:
    """Return the per-patient net annual GLP-1 cost.

    Applies the registry rebate fraction to convert list-price WAC → net cost
    (what a commercial payer actually pays). Use `glp1_payer_net_rebate_fraction=0`
    to run a WAC-based upper-bound sensitivity.
    """
    key = _MOLECULE_TO_REG_KEY.get(str(molecule).upper())
    wac = float(reg[key]) if (key and key in reg) else float(
        reg.get("glp1_wac_semaglutide_annual_usd", 13800.0)
    )
    rebate = float(reg.get("glp1_payer_net_rebate_fraction", 0.0))
    return wac * (1.0 - rebate)


def _on_therapy_effective_hba1c(
    lbxgh: float, molecule: str, reg: Dict[str, float], floor: float = 5.0
) -> float:
    """Estimate the patient's steady-state on-therapy HbA1c.

    Applies the same clinical floor used by the rebound model — trial
    reductions were measured in T2D cohorts (baseline ~8) and would overshoot
    biology if applied unclipped to pre-DM baselines.
    """
    key = f"glp1_efficacy_hba1c_reduction_{molecule.lower()}"
    trial_reduction = float(reg.get(key, reg.get("glp1_efficacy_hba1c_reduction_semaglutide", 1.6)))
    attained = min(trial_reduction, max(0.0, lbxgh - floor))
    return lbxgh - attained


def build_per_patient_costs(
    df: pd.DataFrame, params, horizons: tuple[int, ...], reg: Dict[str, float]
) -> pd.DataFrame:
    """For every patient, run the Markov chain twice (off-therapy, on-therapy)
    and record the cumulative discounted cost at each horizon.
    """
    longest = max(horizons)
    rows = []
    for r in df.itertuples(index=False):
        # Off-therapy: patient's actual baseline HbA1c drives entry state and S0→S1 stratum.
        lbxgh = float(r.LBXGH)
        entry_off = entry_state(lbxgh)
        traj_off = run_markov(entry_off, lbxgh, longest, params, on_therapy=False)

        # On-therapy: use the patient's effective on-therapy HbA1c (baseline − attained
        # reduction, floored at 5.0). This lets the Markov correctly credit GLP-1 for
        # keeping patients out of S1 (Uncontrolled T2D), which is where most of the
        # 5-year cost lives.
        effective = _on_therapy_effective_hba1c(lbxgh, str(r.assigned_molecule), reg)
        entry_on = entry_state(effective)
        traj_on = run_markov(entry_on, effective, longest, params, on_therapy=True)

        row = {
            "patient_idx": int(r.patient_idx),
            "cluster":     int(r.cluster),
            "time_to_dropout_days": float(r.time_to_dropout),
            "assigned_molecule": str(r.assigned_molecule),
            "lbxgh_baseline": lbxgh,
            "on_therapy_hba1c": effective,
        }
        for h in horizons:
            row[f"downstream_dropout_{h}yr"] = float(traj_off.discounted_cost[:h].sum())
            row[f"downstream_adherent_{h}yr"] = float(traj_on.discounted_cost[:h].sum())
        rows.append(row)
    return pd.DataFrame(rows)


def aggregate_cluster(
    df_patients: pd.DataFrame,
    df_costs: pd.DataFrame,
    reg: Dict[str, float],
) -> List[dict]:
    """Per-cluster aggregates of all inputs needed by the ROI formula."""
    df = df_costs.merge(
        df_patients[["patient_idx", "is_adherent"]],
        on="patient_idx",
        how="left",
    )
    # Per-patient annual GLP-1 cost (WAC) from registry
    df["annual_drug_cost"] = df["assigned_molecule"].apply(
        lambda m: patient_drug_cost_annual(m, reg)
    )

    out = []
    for cluster, sub in df.groupby("cluster"):
        record = {
            "cluster": int(cluster),
            "n_patients": int(len(sub)),
            "adherence_probability": float(sub["is_adherent"].mean()),
            "avg_annual_drug_cost": float(sub["annual_drug_cost"].mean()),
            "avg_time_to_dropout_days": float(sub["time_to_dropout_days"].mean()),
        }
        for h in YEARLY_HORIZONS:
            record[f"downstream_dropout_{h}yr"] = float(sub[f"downstream_dropout_{h}yr"].mean())
            record[f"downstream_adherent_{h}yr"] = float(sub[f"downstream_adherent_{h}yr"].mean())
        out.append(record)
    return out


def cluster_roi_row(
    record: dict,
    intervention_cost: float,
    discount_rate: float,
) -> dict:
    """Apply the ROI formula across all horizons for one cluster.

    Adds suffix-keyed columns for every horizon in YEARLY_HORIZONS and chooses
    the 5-year horizon as the primary surface for break-even and threshold.
    """
    out = dict(record)
    yearly: list = []

    for h in YEARLY_HORIZONS:
        inputs = ROIInputs(
            adherence_probability=record["adherence_probability"],
            annual_drug_cost=record["avg_annual_drug_cost"],
            avg_time_to_dropout_days=record["avg_time_to_dropout_days"],
            downstream_dropout=record[f"downstream_dropout_{h}yr"],
            downstream_adherent=record[f"downstream_adherent_{h}yr"],
            horizon_years=h,
            discount_rate=discount_rate,
            intervention_cost_per_patient=intervention_cost,
        )
        roi = compute_roi(inputs)
        yearly.append(roi)
        out[f"expected_drug_cost_{h}yr"] = round(roi.expected_drug_cost, 2)
        out[f"gross_benefit_{h}yr"] = round(roi.gross_benefit, 2)
        out[f"intervention_cost_{h}yr"] = round(roi.intervention_cost, 2)
        out[f"net_benefit_{h}yr"] = round(roi.net_benefit, 2)
        out[f"roi_{h}yr"] = round(roi.roi, 4)

    primary = next(r for r in yearly if r.horizon_years == 5)
    out["break_even_adherence_rate"] = (
        round(primary.break_even_adherence, 4)
        if primary.break_even_adherence is not None
        else None
    )
    out["intervention_cost_threshold_5yr"] = round(primary.intervention_threshold, 2)
    out["time_to_positive_roi_years"] = (
        round(t, 3) if (t := time_to_positive_roi(yearly)) is not None else None
    )
    return out


def run_for_payer(
    payer_type: str,
    df_patients: pd.DataFrame,
    intervention_cost: float = DEFAULT_INTERVENTION_COST,
) -> tuple[pd.DataFrame, list[dict]]:
    """Run the full ROI pipeline for a single payer_type. Returns (wide_df, yearly_rows)."""
    reg = load_registry(payer_type)
    params = build_markov_params(reg)

    df_costs = build_per_patient_costs(df_patients, params, YEARLY_HORIZONS, reg)
    cluster_records = aggregate_cluster(df_patients, df_costs, reg)

    wide_rows = [
        cluster_roi_row(rec, intervention_cost, params.discount_rate)
        for rec in cluster_records
    ]
    for r in wide_rows:
        r["payer_type"] = payer_type
    df_roi = pd.DataFrame(wide_rows)

    yearly_rows = []
    for rec, row_full in zip(cluster_records, wide_rows):
        for h in YEARLY_HORIZONS:
            yearly_rows.append({
                "cluster":            int(rec["cluster"]),
                "payer_type":         payer_type,
                "horizon_years":      h,
                "gross_benefit":      row_full[f"gross_benefit_{h}yr"],
                "expected_drug_cost": row_full[f"expected_drug_cost_{h}yr"],
                "intervention_cost":  row_full[f"intervention_cost_{h}yr"],
                "net_benefit":        row_full[f"net_benefit_{h}yr"],
                "roi":                row_full[f"roi_{h}yr"],
            })
    return df_roi, yearly_rows


def _population_roi(df_roi: pd.DataFrame, horizon: int) -> float:
    net = (df_roi["n_patients"] *
           (df_roi[f"gross_benefit_{horizon}yr"]
            - df_roi[f"expected_drug_cost_{horizon}yr"]
            - df_roi[f"intervention_cost_{horizon}yr"])).sum()
    drug = (df_roi["n_patients"] * df_roi[f"expected_drug_cost_{horizon}yr"]).sum()
    return float(net / drug) if drug > 0 else 0.0


def main(
    intervention_cost: float = DEFAULT_INTERVENTION_COST,
    payer_types: list[str] | None = None,
) -> Path:
    """Run the ROI pipeline for every payer_type and write tagged CSVs.

    If `payer_types` is None, iterates all scenarios discovered by
    `available_payer_types()` — the default (`current`) plus every CSV in
    `docs/evidence/overrides/`.
    """
    if payer_types is None:
        payer_types = available_payer_types()

    print(f"[load] patients:           {SURVIVAL_PATH.relative_to(PROJECT_ROOT)}")
    df_patients = load_patient_frame()
    print(f"       -> {len(df_patients):,} patients")
    print(f"[plan] payer scenarios:    {', '.join(payer_types)}")

    all_wide: list[pd.DataFrame] = []
    all_yearly: list[dict] = []

    for pt in payer_types:
        print(f"\n[run]  scenario '{pt}' — off/on-therapy Markov + ROI...")
        df_roi, yearly_rows = run_for_payer(pt, df_patients, intervention_cost)
        all_wide.append(df_roi)
        all_yearly.extend(yearly_rows)
        pop5 = _population_roi(df_roi, 5)
        pop10 = _population_roi(df_roi, 10)
        print(f"       pop 5-yr ROI = {pop5:+.3f}  ·  pop 10-yr ROI = {pop10:+.3f}")

    combined = pd.concat(all_wide, ignore_index=True)
    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    combined.to_csv(OUTPUT_PATH, index=False)
    print(f"\n[ok]   wrote {OUTPUT_PATH.relative_to(PROJECT_ROOT)} ({len(combined):,} rows across {len(payer_types)} scenarios)")

    pd.DataFrame(all_yearly).to_csv(YEARLY_PATH, index=False)
    print(f"[ok]   wrote {YEARLY_PATH.relative_to(PROJECT_ROOT)} ({len(all_yearly):,} rows)")

    return OUTPUT_PATH


if __name__ == "__main__":
    main()
