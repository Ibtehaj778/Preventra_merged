from pydantic import BaseModel
from typing import List, Dict, Any


class CEASegment(BaseModel):
    cluster:             int
    label:               str
    n:                   int
    annual_cost:         float
    weight_loss:         float
    hba1c_reduction:     float
    cost_per_weight:     float
    cost_per_hba1c:      float
    icer_insulin_weight: float
    icer_insulin_hba1c:  float
    icer_sglt2_weight:   float
    icer_sglt2_hba1c:    float


class CostEffectivenessResponse(BaseModel):
    cea:        List[CEASegment]
    benchmarks: Dict[str, Any]
