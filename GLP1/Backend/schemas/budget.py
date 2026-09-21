from pydantic import BaseModel, Field
from typing import List, Optional


class BudgetRequest(BaseModel):
    dropout_reduction_pct:         float = Field(15, ge=1, le=100)
    intervention_cost_per_patient: float = Field(500, ge=0)
    population_scope_pct:          float = Field(100, ge=1, le=100)


class SegmentImpact(BaseModel):
    cluster:               int
    label:                 str
    n_in_scope:            int
    baseline_dropout_rate: float
    new_dropout_rate:      float
    baseline_wasted_spend: int
    waste_recovered:       int
    intervention_cost:     int
    net_saving:            int
    roi_positive:          bool


class BudgetResponse(BaseModel):
    total_net_saving:       int
    total_waste_recovered:  int
    total_intervention_cost:int
    break_even_month:       Optional[int]
    segments:               List[SegmentImpact]
