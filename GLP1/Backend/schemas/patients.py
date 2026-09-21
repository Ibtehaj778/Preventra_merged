from pydantic import BaseModel
from typing import Optional, List


class PatientRow(BaseModel):
    patient_idx:         int
    dropout_prob:        float
    prediction:          str
    cluster:             int
    segment:             str
    assigned_molecule:   str
    avg_oop_cost:        float
    driver_1:            str
    driver_1_direction:  str
    driver_1_shap:       Optional[float] = None
    driver_2:            Optional[str]   = None
    driver_2_direction:  Optional[str]   = None
    driver_2_shap:       Optional[float] = None
    driver_3:            Optional[str]   = None
    driver_3_direction:  Optional[str]   = None
    driver_3_shap:       Optional[float] = None
    BMXBMI:              Optional[float] = None
    RIDAGEYR:            Optional[int]   = None
    LBXGH:               Optional[float] = None
    comorbidity_score:   Optional[int]   = None
    bio_friction:        Optional[float] = None
    income_cost_pressure:Optional[float] = None
    system_refill_score: Optional[float] = None
    drug_generation:     Optional[int]   = None
    time_to_dropout:     Optional[int]   = None


class PatientSummary(BaseModel):
    high_risk_count:       int
    financial_barrier_count: int


class PatientsResponse(BaseModel):
    total:     int
    page:      int
    page_size: int
    patients:  List[PatientRow]
    summary:   PatientSummary


class SHAPDriver(BaseModel):
    rank:       int
    feature:    str
    direction:  str
    shap_value: float


class SegmentSurvival(BaseModel):
    day30:  float
    day60:  float
    day90:  float
    day180: float


class PatientDetailResponse(BaseModel):
    patient:          PatientRow
    shap_drivers:     Optional[List[SHAPDriver]] = None
    segment_survival: Optional[SegmentSurvival]  = None
