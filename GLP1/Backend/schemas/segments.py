from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class SegmentProfile(BaseModel):
    cluster:       int
    label:         str
    short:         str
    n:             int
    adherence:     float
    age:           Optional[float] = None
    bmi:           Optional[float] = None
    hba1c:         Optional[float] = None
    oop_cost:      Optional[float] = None
    cost_pressure: Optional[float] = None
    bio_friction:  Optional[float] = None
    refill_score:  Optional[float] = None
    comorbidity:   Optional[float] = None
    wasted_per_pt: Optional[int]   = None
    cost_per_hba1c:Optional[int]   = None
    cost_per_weight:Optional[int]  = None


class DistributionStats(BaseModel):
    mean:  float
    std:   float
    min:   float
    p25:   float
    p75:   float
    max:   float


class SegmentDetailResponse(BaseModel):
    cluster:       int
    profile:       SegmentProfile
    distributions: Optional[Dict[str, DistributionStats]] = None


class SegmentsResponse(BaseModel):
    segments: List[SegmentProfile]
