from fastapi import APIRouter
import core.model as model

router = APIRouter()


@router.get("/shap/global")
def get_global_shap():
    return {"drivers": model.shap_cache}
