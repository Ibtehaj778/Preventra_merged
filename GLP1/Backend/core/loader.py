"""
Startup loader for non-Mongo binary artifacts.

Mongo holds all tabular data — these two files (the SHAP test-set matrix and
the trained model pickle) stay on disk because they're opaque binaries
consumed by exactly one endpoint each.
"""

import pickle
from pathlib import Path
from typing import Optional

import numpy as np

from core.config import settings

shap_values: Optional[np.ndarray] = None
model_pkg:   Optional[dict]       = None


def load_binary_artifacts() -> None:
    global shap_values, model_pkg

    d = Path(settings.data_dir)
    d.mkdir(parents=True, exist_ok=True)
    print("\n📂  Loading binary artifacts…")

    npy_path = d / "shap_values_test.npy"
    try:
        shap_values = np.load(npy_path)
        print(f"  ✅  shap_values_test — shape {shap_values.shape}")
    except FileNotFoundError:
        print("  ⚠️   shap_values_test.npy not found — global SHAP will use fallback")
    except Exception as exc:
        print(f"  ❌  shap_values_test.npy failed: {exc}")

    pkl_path = d / "final_gb_model.pkl"
    try:
        with open(pkl_path, "rb") as fh:
            model_pkg = pickle.load(fh)
        threshold = model_pkg.get("threshold", "N/A") if isinstance(model_pkg, dict) else "N/A"
        print(f"  ✅  final_gb_model — threshold: {threshold}")
    except FileNotFoundError:
        print("  ⚠️   final_gb_model.pkl not found — model info will use defaults")
    except (ModuleNotFoundError, ImportError) as exc:
        print(f"  ⚠️   final_gb_model.pkl: scikit-learn version mismatch ({exc})")
    except Exception as exc:
        print(f"  ❌  final_gb_model.pkl failed: {exc}")
