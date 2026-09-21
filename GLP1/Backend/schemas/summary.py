from pydantic import BaseModel
from typing import List


class KPIs(BaseModel):
    total_patients:      int
    adherence_rate:      float
    dropout_rate:        float
    avg_annual_cost:     int
    wasted_spend_annual: int


class SegmentAdherence(BaseModel):
    cluster:   int
    segment:   str
    adherence: float
    n:         int
    color:     str


class DropoutWindow(BaseModel):
    window: str
    seg0:   int
    seg1:   int
    seg2:   int
    seg3:   int


class SummaryResponse(BaseModel):
    kpis:                 KPIs
    adherence_by_segment: List[SegmentAdherence]
    dropout_by_window:    List[DropoutWindow]
