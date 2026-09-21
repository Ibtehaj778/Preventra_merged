// ── Mock data mirroring FastAPI response shapes ──────────────────────────────
// Replace fetch calls with real API when backend is ready

export const SEGMENT_COLORS = ['#EF5350', '#FF7043', '#43A047', '#1E88E5'];
export const SEGMENT_LABELS = [
  'Low Urgency Dropout Risk',
  'Financial Barrier Dropout Risk',
  'Low Friction Strong Adherer',
  'Moderate Risk Moderate Adherer',
];
export const SEGMENT_SHORT = [
  'Low Urgency Dropout',
  'Financial Barrier Dropout',
  'Low Friction Adherer',
  'Moderate Risk Adherer',
];

// ── Screen 1: Executive Summary KPIs ─────────────────────────────────────────
export const summaryKPIs = {
  totalPatients: 7566,
  adherenceRate: 0.47,
  dropoutRate: 0.53,
  avgAnnualCost: 10603,
  wastedSpendAnnual: 40069863,
  benchmarkAdherence: 0.47,
};

export const adherenceBySegment = [
  { segment: 'Low Urgency Dropout', cluster: 0, adherence: 0.208, n: 1902, color: '#EF5350' },
  { segment: 'Financial Barrier', cluster: 1, adherence: 0.309, n: 2104, color: '#FF7043' },
  { segment: 'Low Friction Adherer', cluster: 2, adherence: 0.854, n: 2383, color: '#43A047' },
  { segment: 'Moderate Risk', cluster: 3, adherence: 0.406, n: 1177, color: '#1E88E5' },
];

export const globalSHAPDrivers = [
  { feature: 'Provider & Pharmacy Refill Reliability', importance: 0.541 },
  { feature: 'Financial Pressure Relative to Income', importance: 0.162 },
  { feature: 'Blood Sugar Control (HbA1c)', importance: 0.081 },
  { feature: 'Body Weight / BMI Severity', importance: 0.058 },
  { feature: 'Overall Disease Burden', importance: 0.051 },
  { feature: 'Drug Generation (Newer = Higher Barriers)', importance: 0.031 },
  { feature: 'Patient Age', importance: 0.029 },
  { feature: 'Side Effect Intensity (GI Friction)', importance: 0.021 },
  { feature: 'Out-of-Pocket Medication Cost', importance: 0.019 },
];

export const dropoutByWindow = [
  { window: 'By Day 30',  seg0: 356, seg1: 303, seg2: 11,  seg3: 100 },
  { window: 'By Day 60',  seg0: 645, seg1: 490, seg2: 18,  seg3: 179 },
  { window: 'By Day 90',  seg0: 827, seg1: 655, seg2: 26,  seg3: 246 },
  { window: 'By Day 180', seg0: 1507, seg1: 1455, seg2: 349, seg3: 699 },
];

// ── Screen 2: Patient Risk Panel ─────────────────────────────────────────────
const molecules = ['SEMAGLUTIDE', 'TIRZEPATIDE', 'LIRAGLUTIDE', 'DULAGLUTIDE'];
const drivers = [
  'Financial pressure relative to income',
  'Provider & pharmacy refill reliability',
  'Blood sugar control (HbA1c)',
  'Side effect intensity (GI friction)',
  'Body weight / BMI severity',
  'Out-of-pocket medication cost',
  'Overall disease burden',
];
const directions = ['increases dropout risk', 'reduces dropout risk'];

function seededRand(seed) {
  let s = seed;
  return () => { s = (s * 9301 + 49297) % 233280; return s / 233280; };
}

export const patients = Array.from({ length: 200 }, (_, i) => {
  const rng = seededRand(i * 31 + 7);
  const cluster = i % 4 === 2 ? (rng() > 0.15 ? 2 : Math.floor(rng() * 4)) : Math.floor(rng() * 4);
  const baseProb = cluster === 0 ? 0.65 + rng() * 0.30 : cluster === 1 ? 0.50 + rng() * 0.35 : cluster === 2 ? 0.05 + rng() * 0.20 : 0.35 + rng() * 0.30;
  const dropoutProb = Math.min(0.99, Math.max(0.01, baseProb));
  return {
    patient_idx: i,
    dropout_prob: +dropoutProb.toFixed(4),
    prediction: dropoutProb >= 0.5 ? 'Dropout Risk' : 'Likely Adherent',
    cluster,
    segment: SEGMENT_SHORT[cluster],
    assigned_molecule: molecules[Math.floor(rng() * 4)],
    avg_oop_cost: +(20 + rng() * 180).toFixed(2),
    driver_1: drivers[Math.floor(rng() * drivers.length)],
    driver_1_direction: rng() > 0.4 ? directions[0] : directions[1],
    driver_2: drivers[Math.floor(rng() * drivers.length)],
    driver_2_direction: rng() > 0.5 ? directions[0] : directions[1],
    driver_3: drivers[Math.floor(rng() * drivers.length)],
    driver_3_direction: rng() > 0.5 ? directions[0] : directions[1],
    driver_1_shap: +(-0.3 - rng() * 0.4).toFixed(4),
    driver_2_shap: +(-0.1 - rng() * 0.2).toFixed(4),
    driver_3_shap: +(rng() > 0.5 ? 0.05 + rng() * 0.15 : -0.05 - rng() * 0.15).toFixed(4),
    RIDAGEYR: Math.floor(28 + rng() * 52),
    BMXBMI: +(24 + rng() * 30).toFixed(1),
    LBXGH: +(5.0 + rng() * 7).toFixed(2),
    comorbidity_score: Math.floor(rng() * 3),
    bio_friction: +(0.23 + rng() * 0.33).toFixed(3),
    income_cost_pressure: +(5 + rng() * 120).toFixed(2),
    system_refill_score: +(0.92 + rng() * 0.42).toFixed(4),
    drug_generation: Math.floor(1 + rng() * 3),
    time_to_dropout: Math.floor(1 + rng() * 179),
  };
}).sort((a, b) => b.dropout_prob - a.dropout_prob);

// ── Screen 4: Segment Profiles ────────────────────────────────────────────────
export const segmentProfiles = [
  { cluster: 0, label: SEGMENT_LABELS[0], short: SEGMENT_SHORT[0], n: 1902, adherence: 0.208,
    age: 45.0, bmi: 35.9, hba1c: 5.35, oop_cost: 40.51, cost_pressure: 25.4, bio_friction: 0.566,
    refill_score: 1.19, comorbidity: 0.30, wasted_per_pt: 8412, cost_per_hba1c: 25311, cost_per_weight: 2806 },
  { cluster: 1, label: SEGMENT_LABELS[1], short: SEGMENT_SHORT[1], n: 2104, adherence: 0.309,
    age: 58.8, bmi: 33.6, hba1c: 6.77, oop_cost: 50.90, cost_pressure: 31.3, bio_friction: 0.566,
    refill_score: 1.21, comorbidity: 1.34, wasted_per_pt: 7246, cost_per_hba1c: 16970, cost_per_weight: 1901 },
  { cluster: 2, label: SEGMENT_LABELS[2], short: SEGMENT_SHORT[2], n: 2383, adherence: 0.854,
    age: 55.3, bmi: 34.7, hba1c: 6.20, oop_cost: 83.01, cost_pressure: 47.7, bio_friction: 0.244,
    refill_score: 0.97, comorbidity: 0.92, wasted_per_pt: 1574, cost_per_hba1c: 8827, cost_per_weight: 914 },
  { cluster: 3, label: SEGMENT_LABELS[3], short: SEGMENT_SHORT[3], n: 1177, adherence: 0.406,
    age: 59.5, bmi: 34.2, hba1c: 6.55, oop_cost: 41.06, cost_pressure: 23.7, bio_friction: 0.566,
    refill_score: 1.16, comorbidity: 1.31, wasted_per_pt: 6260, cost_per_hba1c: 13643, cost_per_weight: 1573 },
];

// ── Screen 5: Survival Analysis ──────────────────────────────────────────────
function kmCurve(adherenceRate, points = 36) {
  const lam = -Math.log(adherenceRate) / 180;
  return Array.from({ length: points }, (_, i) => {
    const day = Math.round((i / (points - 1)) * 180);
    return { day, survival: +Math.exp(-lam * day).toFixed(4) };
  });
}

export const survivalCurves = [
  { cluster: 0, label: SEGMENT_LABELS[0], color: '#EF5350', adherence: 0.208, data: kmCurve(0.208) },
  { cluster: 1, label: SEGMENT_LABELS[1], color: '#FF7043', adherence: 0.309, data: kmCurve(0.309) },
  { cluster: 2, label: SEGMENT_LABELS[2], color: '#43A047', adherence: 0.854, data: kmCurve(0.854) },
  { cluster: 3, label: SEGMENT_LABELS[3], color: '#1E88E5', adherence: 0.406, data: kmCurve(0.406) },
];

export const survivalCheckpoints = [
  { segment: 'Low Urgency Dropout Risk',     cluster: 0, day30: 0.187, day60: 0.339, day90: 0.434, day180: 0.792 },
  { segment: 'Financial Barrier Dropout Risk', cluster: 1, day30: 0.144, day60: 0.233, day90: 0.312, day180: 0.692 },
  { segment: 'Low Friction Strong Adherer',  cluster: 2, day30: 0.005, day60: 0.008, day90: 0.011, day180: 0.146 },
  { segment: 'Moderate Risk Moderate Adherer', cluster: 3, day30: 0.085, day60: 0.152, day90: 0.209, day180: 0.594 },
];

export const medianSurvival = [112, 179, 999, 179]; // 999 = >180

// ── Screen 6: Cost-Effectiveness ─────────────────────────────────────────────
export const ceaData = [
  { cluster: 0, label: SEGMENT_SHORT[0], n: 1902, annual_cost: 10622, weight_loss: 3.8, hba1c_reduction: 0.42,
    cost_per_weight: 2806, cost_per_hba1c: 25311, icer_insulin_weight: 5622, icer_insulin_hba1c: 149477,
    icer_sglt2_weight: 1487, icer_sglt2_hba1c: 30145 },
  { cluster: 1, label: SEGMENT_SHORT[1], n: 2104, annual_cost: 10474, weight_loss: 5.5, hba1c_reduction: 0.62,
    cost_per_weight: 1901, cost_per_hba1c: 16970, icer_insulin_weight: 3801, icer_insulin_hba1c: 97612,
    icer_sglt2_weight: 1006, icer_sglt2_hba1c: 20425 },
  { cluster: 2, label: SEGMENT_SHORT[2], n: 2383, annual_cost: 10779, weight_loss: 11.8, hba1c_reduction: 1.22,
    cost_per_weight: 914, cost_per_hba1c: 8827, icer_insulin_weight: 679, icer_insulin_hba1c: 30507,
    icer_sglt2_weight: 397, icer_sglt2_hba1c: 8576 },
  { cluster: 3, label: SEGMENT_SHORT[3], n: 1177, annual_cost: 10540, weight_loss: 6.7, hba1c_reduction: 0.77,
    cost_per_weight: 1573, cost_per_hba1c: 13643, icer_insulin_weight: 2805, icer_insulin_hba1c: 74907,
    icer_sglt2_weight: 743, icer_sglt2_hba1c: 16440 },
];

// ── Screen 7: Budget Impact ───────────────────────────────────────────────────
export function calcBudgetImpact(dropoutReductionPct, interventionCostPerPt, populationScopePct) {
  const reduction = dropoutReductionPct / 100;
  const scopeFraction = populationScopePct / 100;
  const annualCosts = [10622, 10474, 10779, 10540];
  const dropoutRates = [0.792, 0.692, 0.146, 0.594];
  const ns = [1902, 2104, 2383, 1177];

  return ns.map((n, i) => {
    const nInScope = Math.round(n * scopeFraction);
    const baselineWasted = annualCosts[i] * dropoutRates[i] * nInScope;
    const newDropout = dropoutRates[i] * (1 - reduction);
    const newWasted = annualCosts[i] * newDropout * nInScope;
    const wasteRecovered = baselineWasted - newWasted;
    const interventionCost = interventionCostPerPt * nInScope;
    const netSaving = wasteRecovered - interventionCost;
    return {
      cluster: i, label: SEGMENT_SHORT[i], n: nInScope,
      baselineDropout: dropoutRates[i], newDropout,
      baselineWasted: Math.round(baselineWasted),
      wasteRecovered: Math.round(wasteRecovered),
      interventionCost: Math.round(interventionCost),
      netSaving: Math.round(netSaving),
      roiPositive: netSaving > 0,
    };
  });
}

// ── Model info (Screen 8) ────────────────────────────────────────────────────
export const modelInfo = {
  name: 'GradientBoostingClassifier v2',
  params: 'n_estimators=200, lr=0.05, max_depth=4, max_features=sqrt',
  accuracy: 0.791, precision: 0.876, recall: 0.646, f1: 0.744, auc: 0.879,
  threshold: 0.48,
  trainSize: 6052, testSize: 1514,
  lastTrained: 'May 2026',
};

export const dataSources = [
  { name: 'CMS Medicare Part D 2023', creator: 'CMS', records: '351,240', description: 'GLP-1 prescriber-drug records, 172K unique prescribers' },
  { name: 'NHANES 2017–18 + 2021–23', creator: 'CDC / NCHS', records: '5,000+', description: 'Patient baselines: age, BMI, HbA1c, comorbidities' },
  { name: 'MEPS', creator: 'AHRQ', records: '2,933', description: 'GLP-1 prescription fills with out-of-pocket cost data' },
  { name: 'FAERS', creator: 'FDA', records: 'Post-market', description: 'Real-world adverse event frequencies by molecule' },
  { name: 'ClinicalTrials.gov', creator: 'NIH', records: '19 trials', description: 'STEP, SUSTAIN, SURMOUNT adverse event rates' },
];
