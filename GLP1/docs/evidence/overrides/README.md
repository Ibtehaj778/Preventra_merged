# Registry Overrides

Layered parameter registry. Each CSV in this directory represents a **pricing
environment** — a scenario for the drug and complication cost side of the ROI
calculation. Clinical parameters (Markov transitions, GLP-1 relative risks,
rebound rates) do not vary by payer type and are not duplicated here.

## Load pattern

```
Base:      evidence/parameter_registry.csv           (default = "current")
Override:  evidence/overrides/{payer_type}.csv       (partial — only diffs)
Merge:     for each row in override, replace matching parameter_name in base.
```

Only rows that differ from the base need to appear in an override file.

## Scenarios shipped in v1

| File | Scenario name | What it represents |
|---|---|---|
| _(none)_ | `current` | Base registry, unchanged. US commercial WAC × (1 − 0.35 rebate), Medicare ESRD cost. Reflects the market as of 2025. |
| `medicare_2028.csv` | `medicare_2028` | Projected Medicare Part D–negotiated GLP-1 pricing after the 2028 negotiation window. Based on the ~65% average discount observed in the 2026 negotiation results. |
| `post_generic.csv` | `post_generic` | Post-patent-expiry pricing (~2032+). Semaglutide + tirzepatide biosimilars available; prices reflect typical post-generic decline in the diabetes-drug class. |

## Adding a new scenario

1. Copy `medicare_2028.csv` as a starting template.
2. Change the parameter values. Only include rows that differ from base.
3. Rerun `Model/consequence/payer_roi.py` — it iterates all files in this directory automatically.
4. Add the scenario ID to the frontend segmented control in `PayerROIPanel.jsx`.

## Column format

Same as [../parameter_registry.csv](../parameter_registry.csv): `parameter_name, value, unit, source, source_url, year, notes`.
