"""
Cost-Effectiveness Studio — live read from cost_effectiveness collection,
plus static benchmark constants from the notebook.
"""

from fastapi import APIRouter

from core.mongo import get_db

router = APIRouter()

_BENCHMARKS = {
    "glp1": {
        "SEMAGLUTIDE": {"weight_loss_pct": 14.9, "hba1c_reduction": 1.6, "annual_cost": 13000},
        "TIRZEPATIDE": {"weight_loss_pct": 20.9, "hba1c_reduction": 2.1, "annual_cost": 16000},
        "LIRAGLUTIDE": {"weight_loss_pct": 8.0,  "hba1c_reduction": 1.1, "annual_cost": 7800},
        "DULAGLUTIDE": {"weight_loss_pct": 4.5,  "hba1c_reduction": 1.4, "annual_cost": 7200},
    },
    "comparators": {
        "insulin_glargine": {"weight_loss_pct": -1.5, "hba1c_reduction": 1.5, "annual_cost": 3500},
        "sglt2_inhibitor":  {"weight_loss_pct":  3.0, "hba1c_reduction": 0.8, "annual_cost": 5800},
    },
    "icer_threshold": 50000,
}


@router.get("/cost-effectiveness")
async def get_cost_effectiveness():
    db = get_db()
    cea = await db.cost_effectiveness.find({}, {"_id": 0}).sort("cluster", 1).to_list(length=None)
    return {"cea": cea, "benchmarks": _BENCHMARKS}
