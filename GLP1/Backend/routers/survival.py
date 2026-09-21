from fastapi import APIRouter
import core.model as model

router = APIRouter()


@router.get("/survival")
def get_survival():
    return model.survival_cache
