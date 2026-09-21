from pydantic import BaseModel
from typing import List, Optional


class SurvivalPoint(BaseModel):
    day:      int
    survival: float


class KMCurve(BaseModel):
    cluster:   int
    label:     str
    color:     str
    adherence: float
    data:      List[SurvivalPoint]


class Checkpoint(BaseModel):
    segment: str
    cluster: int
    day30:   float
    day60:   float
    day90:   float
    day180:  float


class LogRank(BaseModel):
    test_statistic: float
    p_value:        float
    significant:    bool


class SurvivalResponse(BaseModel):
    curves:          List[KMCurve]
    checkpoints:     List[Checkpoint]
    median_survival: List[int]
    logrank:         LogRank
