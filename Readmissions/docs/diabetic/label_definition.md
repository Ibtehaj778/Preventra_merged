# NeuroShield — Label Definition (Week 2)

## Binary Label: `readmission_30d`

### Source Column
`readmitted` in the Diabetes 130-US Hospitals dataset.

### Encoding

| Source Value | Meaning | Binary Label |
|-------------|---------|--------------|
| `<30` | Patient readmitted within 30 days of discharge | **1** (positive) |
| `>30` | Patient readmitted after 30 days | **0** (negative) |
| `NO` | Patient not readmitted | **0** (negative) |

### Pandas Implementation

```python
df['label'] = (df['readmitted'] == '<30').astype(int)
```

### Class Balance

Approximately **11% positive** rate (~11,000 out of ~101,766 records).

This is a class-imbalanced binary classification problem. The imbalance
is **not resampled** at the feature engineering stage. It is addressed in
Week 3 model training by setting `class_weight='balanced'` in
`DecisionTreeClassifier`, which internally adjusts sample weights
inversely proportional to class frequency.

### Exclusion Decisions

- `>30` readmissions are mapped to **0** (negative) because the NeuroShield
  risk model is specifically designed to flag patients at risk of early
  (within 30 days) readmission — a longer-term readmission does not
  trigger the same clinical intervention pathway.
- No rows are excluded from the dataset based on label value.