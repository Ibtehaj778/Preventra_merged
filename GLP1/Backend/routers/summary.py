"""
Executive Summary endpoint — live aggregation over the patients collection.

Combines:
  - patients collection ($group by cluster for adherence + counts)
  - cost_effectiveness collection (annual cost + total spend per segment)
"""

import asyncio

from fastapi import APIRouter

import core.model as model
from core.mongo import get_db

router = APIRouter()


@router.get("/summary")
async def get_summary():
    db = get_db()

    seg_agg, dropout_30, dropout_60, dropout_90, dropout_180, cea_docs, total_patients = await asyncio.gather(
        db.patients.aggregate([
            {"$group": {
                "_id": "$cluster",
                "adherence": {"$avg": "$is_adherent"},
                "n": {"$sum": 1},
            }},
            {"$sort": {"_id": 1}},
        ]).to_list(length=None),
        _dropouts_by_day(db, 30),
        _dropouts_by_day(db, 60),
        _dropouts_by_day(db, 90),
        _dropouts_by_day(db, 180),
        db.cost_effectiveness.find({}, {"_id": 0}).to_list(length=None),
        db.patients.count_documents({}),
    )

    cea_by_cluster = {d["cluster"]: d for d in cea_docs}
    seg_by_cluster = {int(r["_id"]): r for r in seg_agg}

    overall_adherence = sum(r["adherence"] * r["n"] for r in seg_agg) / max(total_patients, 1)
    avg_annual_cost = sum(d.get("annual_cost", 0) * d.get("n", 0) for d in cea_docs) / max(total_patients, 1)
    wasted_spend = sum(
        (d.get("wasted_spend_per_pt") or 0) * (d.get("n") or 0)
        for d in cea_docs
    )

    adherence_by_segment = []
    for i in range(4):
        seg = seg_by_cluster.get(i)
        if seg is None:
            continue
        adherence_by_segment.append({
            "cluster":   i,
            "segment":   model.SEGMENT_SHORT[i],
            "adherence": round(float(seg["adherence"] or 0), 4),
            "n":         int(seg["n"]),
            "color":     model.SEGMENT_COLORS[i],
        })

    dropout_by_window = []
    for window, counts in [("By Day 30", dropout_30), ("By Day 60", dropout_60),
                           ("By Day 90", dropout_90), ("By Day 180", dropout_180)]:
        dropout_by_window.append({
            "window": window,
            "seg0":   counts.get(0, 0),
            "seg1":   counts.get(1, 0),
            "seg2":   counts.get(2, 0),
            "seg3":   counts.get(3, 0),
        })

    return {
        "kpis": {
            "total_patients":      total_patients,
            "adherence_rate":      round(overall_adherence, 4),
            "dropout_rate":        round(1 - overall_adherence, 4),
            "avg_annual_cost":     round(avg_annual_cost),
            "wasted_spend_annual": round(wasted_spend),
        },
        "adherence_by_segment": adherence_by_segment,
        "dropout_by_window":    dropout_by_window,
    }


async def _dropouts_by_day(db, day: int) -> dict[int, int]:
    rows = await db.patients.aggregate([
        {"$match": {"event_occurred": 1, "time_to_dropout": {"$lte": day}}},
        {"$group": {"_id": "$cluster", "n": {"$sum": 1}}},
    ]).to_list(length=None)
    return {int(r["_id"]): int(r["n"]) for r in rows}
