"""Pydantic schemas for the Consequence Model endpoints."""

from typing import Dict, List, Optional

from pydantic import BaseModel


class DownstreamCostCluster(BaseModel):
    cluster_id:                int
    cluster_label:             Optional[str] = None
    n_patients:                int
    avg_downstream_cost_5yr:   float
    avg_downstream_cost_10yr:  float
    esrd_probability_5yr:      float
    cv_event_probability_5yr:  float
    total_population_cost_5yr: float
    # Cost decomposition by primary driver, per-patient avg USD at 5-yr horizon.
    cost_by_driver_5yr:        Dict[str, float]


class DownstreamCostResponse(BaseModel):
    by_cluster:                       List[DownstreamCostCluster]
    population_total_5yr:             float
    population_total_10yr:            float
    primary_cost_driver_distribution: Dict[str, float]
    n_patients_total:                 int


# ── Rebound Risk (Phase 2) ──────────────────────────────────────────────────

class ReboundCluster(BaseModel):
    cluster_id:                int
    cluster_label:             Optional[str] = None
    n_patients:                int
    avg_hba1c_at_dropout:      float
    avg_expected_hba1c_6mo:    float
    avg_expected_hba1c_12mo:   float
    avg_bmi_at_dropout:        float
    avg_expected_bmi_12mo:     float
    avg_severity_score:        float
    p_new_t2d_12mo_mean:       Optional[float] = None
    p_uncontrolled_12mo_mean:  Optional[float] = None
    dm_status_distribution:    Dict[str, float]


class ReboundTrajectoryPoint(BaseModel):
    month:     float
    avg_hba1c: float
    avg_bmi:   float


class ReboundTrajectoryScenario(BaseModel):
    scenario:    str            # "early" | "median" | "late"
    dropout_day: float
    points:      List[ReboundTrajectoryPoint]


class ReboundTrajectoryCluster(BaseModel):
    cluster_id: int
    scenarios:  List[ReboundTrajectoryScenario]


class ReboundSensitivityScenario(BaseModel):
    scenario:                  str
    dropout_day:               float
    avg_hba1c_at_dropout:      float
    avg_expected_hba1c_12mo:   float
    avg_severity_score:        float
    p_new_t2d_12mo_mean:       Optional[float] = None
    p_uncontrolled_12mo_mean:  Optional[float] = None


class ReboundSensitivityCluster(BaseModel):
    cluster_id: int
    scenarios:  List[ReboundSensitivityScenario]


class ReboundRiskResponse(BaseModel):
    by_cluster:                  List[ReboundCluster]
    trajectory_by_cluster:       List[ReboundTrajectoryCluster]
    sensitivity:                 List[ReboundSensitivityCluster]
    population_t2d_incidence_12mo: float
    n_patients_total:             int


# ── Payer ROI (Phase 3) ────────────────────────────────────────────────────

class PayerROIHorizon(BaseModel):
    horizon_years:      int
    expected_drug_cost: float
    gross_benefit:      float
    intervention_cost:  float
    net_benefit:        float
    roi:                float
    # Intervention-only ROI (adherence-program business case).
    # medical: (Δα·(C_d − C_a) − intervention_cost) / intervention_cost
    #          Standard payer framing — treats drug spend as an already-committed
    #          formulary decision and asks "how much medical cost avoidance per $ of program spend?"
    # net:     also subtracts Δα·D·(annuity − drop_days/365), i.e. the extra drug
    #          spend a payer incurs when adherence rises.
    delta_benefit_medical:    float
    delta_drug_cost:          float
    intervention_roi_medical: float
    intervention_roi_net:     float


class PayerROIYearlyPoint(BaseModel):
    year:                     int
    roi:                      float
    intervention_roi_medical: float
    intervention_roi_net:     float


class PayerROICluster(BaseModel):
    cluster_id:                       int
    cluster_label:                    Optional[str] = None
    n_patients:                       int
    adherence_probability:            float
    adherence_with_program:           float
    effective_adherence_uplift:       float
    avg_annual_drug_cost:             float
    avg_time_to_dropout_days:         float
    horizons:                         List[PayerROIHorizon]
    yearly_roi_series:                List[PayerROIYearlyPoint]
    break_even_adherence_rate:        Optional[float] = None
    intervention_cost_threshold_5yr:  float
    time_to_positive_roi_years:       Optional[float] = None


class PayerROIResponse(BaseModel):
    by_cluster:                       List[PayerROICluster]
    population_roi_1yr:               float
    population_roi_3yr:               float
    population_roi_5yr:               float
    population_roi_10yr:              float
    population_intervention_roi_medical_1yr:  float
    population_intervention_roi_medical_5yr:  float
    population_intervention_roi_medical_10yr: float
    population_intervention_roi_net_1yr:      float
    population_intervention_roi_net_5yr:      float
    population_intervention_roi_net_10yr:     float
    intervention_cost_per_patient:    float
    adherence_uplift_applied:         float
    n_patients_total:                 int
