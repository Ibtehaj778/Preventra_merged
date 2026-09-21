"""
Segment Explorer endpoints — live Mongo queries.

GET /segments        → segment_profiles collection (precomputed in migration)
GET /segments/{id}   → profile + live distribution stats from patients collection
"""

import numpy as np
from fastapi import APIRouter, HTTPException

from core.mongo import get_db

router = APIRouter()

_DIST_COLS = [("BMXBMI", "bmi"), ("RIDAGEYR", "age"), ("LBXGH", "hba1c")]


@router.get("/segments")
async def get_segments():
    db = get_db()
    docs = await db.segment_profiles.find({}, {"_id": 0}).sort("cluster", 1).to_list(length=None)
    return {"segments": docs}


@router.get("/segments/{cluster_id}")
async def get_segment(cluster_id: int):
    if cluster_id not in range(4):
        raise HTTPException(status_code=404, detail=f"Segment {cluster_id} not found. Valid: 0–3")

    db = get_db()
    profile = await db.segment_profiles.find_one({"cluster": cluster_id}, {"_id": 0})
    if profile is None:
        raise HTTPException(status_code=404, detail=f"Segment {cluster_id} data not available")

    distributions = await _get_distributions(db, cluster_id)
    return {"cluster": cluster_id, "profile": profile, "distributions": distributions}


async def _get_distributions(db, cluster_id: int):
    projection = {"_id": 0, **{col: 1 for col, _ in _DIST_COLS}}
    docs = await db.patients.find({"cluster": cluster_id}, projection).to_list(length=None)
    if not docs:
        return None

    dist = {}
    for col, key in _DIST_COLS:
        vals = np.array([d[col] for d in docs if d.get(col) is not None], dtype=float)
        if vals.size == 0:
            continue
        dist[key] = {
            "mean": round(float(vals.mean()), 2),
            "std":  round(float(vals.std(ddof=1)), 2) if vals.size > 1 else 0.0,
            "min":  round(float(vals.min()), 2),
            "p25":  round(float(np.percentile(vals, 25)), 2),
            "p75":  round(float(np.percentile(vals, 75)), 2),
            "max":  round(float(vals.max()), 2),
        }
    return dist or None
