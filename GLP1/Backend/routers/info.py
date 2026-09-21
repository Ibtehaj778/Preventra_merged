from fastapi import APIRouter
import core.loader as loader

router = APIRouter()

# Static metrics from the trained model notebook
_STATIC_METRICS = {
    "name":       "GradientBoostingClassifier v2",
    "params":     "n_estimators=200, lr=0.05, max_depth=4, max_features=sqrt",
    "accuracy":   0.791,
    "precision":  0.876,
    "recall":     0.646,
    "f1":         0.744,
    "auc_roc":    0.879,
    "threshold":  0.48,
    "train_size": 6052,
    "test_size":  1514,
    "last_trained": "May 2026",
    "feature_count": 17,
}


@router.get("/model/info")
def get_model_info():
    model = loader.model_pkg
    if model is None:
        return _STATIC_METRICS

    info = dict(_STATIC_METRICS)
    if isinstance(model, dict):
        info["threshold"] = model.get("threshold", _STATIC_METRICS["threshold"])
        if "feature_names" in model:
            info["features"] = model["feature_names"]
            info["feature_count"] = len(model["feature_names"])
        if "metrics" in model:
            m = model["metrics"]
            info.update({
                "accuracy":  m.get("accuracy",  info["accuracy"]),
                "precision": m.get("precision", info["precision"]),
                "recall":    m.get("recall",    info["recall"]),
                "f1":        m.get("f1",        info["f1"]),
                "auc_roc":   m.get("auc_roc",   info["auc_roc"]),
            })
    return info
