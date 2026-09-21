"""
Layered parameter-registry loader for the Consequence Model.

Design:
    Base:      docs/evidence/parameter_registry.csv       (default = "current" scenario)
    Override:  docs/evidence/overrides/{payer_type}.csv   (sparse — only rows that differ)
    Merge:     for each row in override, replace matching parameter_name in base.

This keeps clinical parameters (Markov transitions, GLP-1 relative risks, rebound
rates) in a single place and pushes the pricing-environment dimension into
sparse override files. Adding a new payer scenario = adding one CSV; no code
changes required by consumers of `load_registry`.
"""

from __future__ import annotations

from pathlib import Path
from typing import Dict, List

import pandas as pd


PROJECT_ROOT = Path(__file__).resolve().parents[2]
BASE_REGISTRY_PATH = PROJECT_ROOT / "docs" / "evidence" / "parameter_registry.csv"
OVERRIDES_DIR = PROJECT_ROOT / "docs" / "evidence" / "overrides"

DEFAULT_PAYER_TYPE = "current"


def load_registry(payer_type: str = DEFAULT_PAYER_TYPE) -> Dict[str, float]:
    """Load the parameter registry, optionally applying a payer-type override.

    Args:
        payer_type: `"current"` (base only) or the stem of a CSV in
            `docs/evidence/overrides/`. Unknown payer types fall back to base with
            a warning printed to stdout — this fails soft in dashboards but
            loud in dev.

    Returns:
        `{parameter_name: value}` dict of all clinical + economic parameters
        with any override rows applied on top of the base.
    """
    base = pd.read_csv(BASE_REGISTRY_PATH)
    reg = {row.parameter_name: float(row.value) for row in base.itertuples()}

    if payer_type == DEFAULT_PAYER_TYPE:
        return reg

    override_path = OVERRIDES_DIR / f"{payer_type}.csv"
    if not override_path.exists():
        print(f"[registry] warning: unknown payer_type '{payer_type}' — "
              f"no override at {override_path}. Falling back to base.")
        return reg

    override_df = pd.read_csv(override_path)
    for row in override_df.itertuples():
        reg[row.parameter_name] = float(row.value)
    return reg


def available_payer_types() -> List[str]:
    """List all scenario IDs: the default plus every CSV in overrides/."""
    scenarios = [DEFAULT_PAYER_TYPE]
    if OVERRIDES_DIR.exists():
        scenarios.extend(sorted(p.stem for p in OVERRIDES_DIR.glob("*.csv")))
    return scenarios
