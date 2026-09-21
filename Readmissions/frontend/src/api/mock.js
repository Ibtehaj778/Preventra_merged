const delay = (ms) => new Promise((resolve) => setTimeout(resolve, ms));

const MOCK_DELAY_MS = 600;

export const getSummary = async () => {
  await delay(MOCK_DELAY_MS);
  return {
    batch_date: new Date().toISOString().split('T')[0],
    total_patients: 1250,
    high_count: 142,
    medium_count: 315,
    low_count: 793,
    high_delta: 12
  };
};

const MOCK_DRIVER_LABELS = ['HbA1c > 9.0%', 'Prior Admissions', 'Emergency Visits', 'Insulin Dosage Change', 'Age > 65', 'Comorbidities (HTN)'];

function bandForMockScore(score) {
  if (score > 80) return 'High';
  if (score > 50) return 'Medium';
  return 'Low';
}

// Single source of truth for the 50 demo patients, so the worklist
// (getPatients) and a single patient's detail (getPatientById) always agree
// on risk_score/risk_band/discharge_date for the same id instead of each
// deriving its own value from a different formula.
function buildMockPatientList() {
  const patients = [];
  for (let i = 1; i <= 50; i++) {
    // Generate some deterministic but varied pseudorandom distributions
    const r = ((i * 17) % 100);

    // Create IDs like PT-1045
    const id = `PT-${1000 + i * 3}`;

    // Last discharge date ranging from 1 to 30 days ago
    const dDate = new Date();
    dDate.setDate(dDate.getDate() - (i % 30) - 1);

    patients.push({
      id,
      risk_score: r,
      risk_band: bandForMockScore(r),
      primary_diagnosis: 'Congestive heart failure, unspecified',
      primary_icd_code: 'I5090',
      primary_driver_label: MOCK_DRIVER_LABELS[i % MOCK_DRIVER_LABELS.length],
      discharge_date: dDate.toISOString().split('T')[0],
    });
  }
  return patients;
}

const MOCK_PATIENTS = buildMockPatientList();

export const getPatients = async () => {
  await delay(MOCK_DELAY_MS);

  // Weekly trend is derived from the same generator getPatientTrend uses, so a
  // patient's dashboard badge always matches their trend page. Computed here
  // rather than at module init because the TREND_* consts are declared below.
  const withTrend = MOCK_PATIENTS.map((p) => {
    const numId = parseInt(String(p.id).replace('PT-', '')) || 0;
    const scores = buildWeeklyScores(numId);
    const dischargeScore = scores[0];
    const currentScore = scores[scores.length - 1];

    return {
      ...p,
      // risk_score is the primary triage number, now the CURRENT score.
      risk_score: currentScore,
      risk_band: bandForScore(currentScore),
      discharge_score: dischargeScore,
      discharge_band: p.risk_band,
      current_score: currentScore,
      trend_delta: Math.round((currentScore - dischargeScore) * 10) / 10,
      monitoring_status: classifyTrendStatus(scores),
      weeks_tracked: scores.length,
    };
  });

  // Sort by current risk_score descending
  return withTrend.sort((a, b) => b.risk_score - a.risk_score);
};

export const getPatientById = async (id) => {
  await delay(MOCK_DELAY_MS);

  // Prefer the exact row from the worklist generator so the score/band/date
  // shown here always match what the dashboard listed for this same id. The
  // score shown is the CURRENT (latest weekly) score, matching the worklist.
  const listed = MOCK_PATIENTS.find((p) => p.id === id);
  const numId = parseInt(String(id).replace('PT-', '')) || 0;

  let score, riskBand, dischargeDate, dischargeScore, history;
  if (listed) {
    const series = weeklySeriesWithDates(numId);
    dischargeScore = series[0].score;
    score = series[series.length - 1].score;
    riskBand = bandForScore(score);
    dischargeDate = listed.discharge_date;
    // Matches the real backend's shape: [{ week, score }] oldest first.
    history = series.map((pt) => ({ week: pt.label, score: pt.score }));
  } else {
    // Fallback for ids outside the standard 50 (e.g. manually-entered or
    // updated patients) — deterministic from the id itself, no weekly history.
    score = (numId * 13) % 100;
    if (score === 0) score = 88;
    dischargeScore = score;
    riskBand = bandForMockScore(score);
    dischargeDate = new Date().toISOString().split('T')[0];
    history = [{ week: 'Current', score }];
  }

  return {
    id: id,
    risk_score: score,
    risk_band: riskBand,
    discharge_score: dischargeScore,
    discharge_date: dischargeDate,
    history,
    drivers: [
      {
        category: 'history',
        label: 'Prior Inpatient Admissions',
        value: `${(numId % 4) + 1}`,
        explanation: 'Frequent inpatient stays over the past 12 months dramatically elevate readmission risk.'
      },
      {
        category: 'lab',
        label: 'HbA1c %',
        value: `${8.0 + (numId % 30) / 10}%`,
        explanation: 'Elevated HbA1c indicates suboptimal glycemic control, impairing healing and immune response.'
      },
      {
        category: 'medication',
        label: 'Diabetes Med Changes',
        value: 'Yes',
        explanation: 'Recent changes to prescribed insulin dosages indicate an unstable management phase.'
      }
    ]
  };
};

export const getSummaryHistory = async () => {
  await delay(MOCK_DELAY_MS);
  const data = [];
  const startCount = 120;
  
  for (let i = 7; i >= 0; i--) {
    const d = new Date();
    d.setDate(d.getDate() - (i * 7));
    data.push({
      week_label: `${d.getMonth() + 1}/${d.getDate()}`,
      high_count: startCount + (i % 2 === 0 ? 5 : -2) + i * 3
    });
  }
  return data;
};

export const getModelMetrics = async () => {
  await delay(MOCK_DELAY_MS);
  return {
    auc_roc: 0.842,
    precision: 0.76,
    recall: 0.81,
    threshold: 0.52
  };
};

export const getPipelineRuns = async () => {
  await delay(MOCK_DELAY_MS);
  return [
    { id: 'RUN-5912', filename: 'diabetic_data.csv', run_date: '2026-04-14 02:00:00', patient_count: 1250, status: 'Completed' },
    { id: 'RUN-5911', filename: 'diabetic_data_w2.csv', run_date: '2026-04-07 02:00:00', patient_count: 1248, status: 'Completed' },
    { id: 'RUN-5910', filename: 'diabetic_data_w1.csv', run_date: '2026-03-31 02:00:00', patient_count: 1242, status: 'Failed' },
    { id: 'RUN-5909', filename: 'diabetic_data_w1_b.csv', run_date: '2026-03-31 04:30:00', patient_count: 1240, status: 'Completed' },
    { id: 'RUN-5908', filename: 'diabetic_data_prev.csv', run_date: '2026-03-24 02:00:00', patient_count: 1235, status: 'Completed' }
  ];
};

export const uploadFile = async (_file) => {
  await delay(MOCK_DELAY_MS);
  return { run_id: 'MOCK-RUN', status: 'Running' };
};

export const getPipelineStatus = async (_runId) => {
  await delay(MOCK_DELAY_MS * 2);
  return { id: 'MOCK-RUN', status: 'Completed', current_step: 'registry_updated', patient_count: 50 };
};

// ---------------------------------------------------------------------------
// Phase 2 — weekly post-discharge trend monitoring
// ---------------------------------------------------------------------------

const TREND_NOISE_BAND = 5;
const TREND_SHARP_JUMP = 15;

const TREND_STATUS_LABELS = {
  action_required:    'Action Required',
  deteriorating:       'Deterioration',
  improving:            'Improving',
  stable:               'Stable',
  insufficient_data:    'Insufficient Data',
};

const TREND_STATUS_ACTIONS = {
  action_required: 'Sharp single-week increase detected. Escalate immediately, the same urgency tier as an in-hospital high-risk alert. Prioritize outreach and review recent adherence/appointment data for a root cause.',
  deteriorating: 'Risk has trended upward over recent weeks. Auto-generate an alert to the assigned care coordinator, prioritize outreach/follow-up, and review recent adherence and appointment data.',
  improving: 'Score is falling week over week and recovery is on track. No urgent action; log the positive trend and consider reducing check-in frequency as recovery stabilizes.',
  stable: 'No meaningful week-to-week change. Continue routine weekly monitoring; no new action needed.',
  insufficient_data: 'Not enough weekly history yet to assess a trend. Continue routine monitoring as more weekly scores are collected.',
};

const bandForScore = (score) => {
  if (score >= 80) return 'High';
  if (score >= 50) return 'Medium';
  return 'Low';
};

const DRIVER_POOL = [
  {
    label: 'Prior Inpatient Admissions',
    category: 'history',
    unit: '',
    explanation: 'Frequent admissions over the past year signal ongoing clinical instability.',
  },
  {
    label: 'Emergency Department Visits (90d)',
    category: 'history',
    unit: '',
    explanation: 'Repeated ED visits in a short window suggest unmanaged acute episodes.',
  },
  {
    label: 'Medications at Discharge',
    category: 'medication',
    unit: '',
    explanation: 'A high medication count increases adherence complexity and adverse-event risk.',
  },
  {
    label: 'HbA1c Result',
    category: 'lab',
    unit: '%',
    explanation: 'Elevated readings indicate suboptimal glycemic control, slowing recovery.',
  },
  {
    label: 'Follow-up Appointment Attendance',
    category: 'history',
    unit: '',
    explanation: 'Missed or inconsistent follow-up visits delay detection of complications.',
  },
  {
    label: 'Insulin Dosage Stability',
    category: 'medication',
    unit: '',
    explanation: 'Frequent insulin dosage changes indicate an unstable management phase.',
  },
];

function weekDrivers(seed, weekIdx) {
  const picks = [0, 1, 2].map((k) => DRIVER_POOL[(seed + weekIdx + k) % DRIVER_POOL.length]);
  return picks.map((d, k) => ({
    category: d.category,
    label: d.label,
    value: `${((seed + weekIdx * (k + 1)) % 9) + 1}${d.unit}`,
    explanation: d.explanation,
  }));
}

// Mirrors _classify_trend_status in api/main.py. Shared by getPatients and
// getPatientTrend so the dashboard badge and the trend page always agree.
function classifyTrendStatus(scores) {
  if (!scores || scores.length < 2) return 'insufficient_data';

  const latest = scores[scores.length - 1];
  const lastDelta = latest - scores[scores.length - 2];
  const trailing = scores.slice(Math.max(0, scores.length - 4), scores.length - 1);
  const vsTrailing = latest - trailing.reduce((s, v) => s + v, 0) / trailing.length;

  if (lastDelta >= TREND_SHARP_JUMP) return 'action_required';
  if (vsTrailing >= TREND_NOISE_BAND) return 'deteriorating';
  if (vsTrailing <= -TREND_NOISE_BAND) return 'improving';
  return 'stable';
}

// Deterministic per-patient weekly score series so the same patient always
// renders the same trend shape (mirrors getPatientById's approach below).
function buildWeeklyScores(numId) {
  const bucket = numId % 4;
  const base = 30 + (numId % 40); // 30-69 starting score
  const weeks = 6;
  const scores = [];

  for (let w = 0; w < weeks; w++) {
    let score;
    if (bucket === 0) {
      // stable: small wiggle around base
      score = base + (((numId + w) * 7) % 7) - 3;
    } else if (bucket === 1) {
      // deteriorating: steady climb
      score = base + w * 6 + (w % 2);
    } else if (bucket === 2) {
      // action required: flat, then a sharp jump on the last week
      score = w < weeks - 1 ? base + (w % 3) : base + 22;
    } else {
      // improving: steady decline
      score = Math.max(5, base + 20 - w * 6);
    }
    scores.push(Math.max(1, Math.min(99, Math.round(score))));
  }
  return scores;
}

// Stamps a weekly score series with dates (one week apart, ending today) and
// the short labels the charts axis on. Shared by getPatientTrend and
// getPatientById's score history so both plot the same curve.
function weeklySeriesWithDates(numId) {
  const scores = buildWeeklyScores(numId);
  const today = new Date();
  return scores.map((score, idx) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (scores.length - 1 - idx) * 7);
    return {
      score,
      date: d.toISOString().split('T')[0],
      label: `${d.getMonth() + 1}/${d.getDate()}`,
    };
  });
}

export const getPatientTrend = async (id) => {
  await delay(MOCK_DELAY_MS);
  const numId = parseInt(String(id).replace('PT-', '')) || 0;
  const scores = buildWeeklyScores(numId);

  const today = new Date();
  const weeks = scores.map((score, idx) => {
    const d = new Date(today);
    d.setDate(d.getDate() - (scores.length - 1 - idx) * 7);
    const prevScore = idx === 0 ? null : scores[idx - 1];
    const delta = prevScore === null ? null : Math.round((score - prevScore) * 10) / 10;
    let week_trend = 'stable';
    if (delta !== null) {
      if (delta >= TREND_NOISE_BAND) week_trend = 'increasing';
      else if (delta <= -TREND_NOISE_BAND) week_trend = 'decreasing';
    }
    return {
      week_number: idx + 1,
      batch_date: d.toISOString().split('T')[0],
      week_label: `${d.getMonth() + 1}/${d.getDate()}`,
      risk_score: score,
      risk_band: bandForScore(score),
      delta,
      week_trend,
      // The mock generator really does step 7 days at a time, so unlike the
      // MIMIC-backed real API these points are genuinely a week apart.
      admit_date: d.toISOString().split('T')[0],
      discharge_date: d.toISOString().split('T')[0],
      los_days: null,
      days_since_prev: idx === 0 ? null : 7,
      interval_label: idx === 0 ? 'first scored admission' : '7 days later',
      rapid_return: idx !== 0,
      drivers: weekDrivers(numId, idx),
    };
  });

  const monitoring_status = classifyTrendStatus(scores);

  const first_score = weeks[0]?.risk_score ?? 0;
  const latest_score = weeks[weeks.length - 1]?.risk_score ?? 0;

  return {
    patient_id: id,
    monitoring_status,
    status_label: TREND_STATUS_LABELS[monitoring_status],
    recommended_action: TREND_STATUS_ACTIONS[monitoring_status],
    weeks_tracked: weeks.length,
    first_score,
    latest_score,
    net_change: Math.round((latest_score - first_score) * 10) / 10,
    median_gap_days: 7,
    span_days: (weeks.length - 1) * 7,
    weeks,
  };
};

// ---------------------------------------------------------------------------
// AI insights — ROI estimate + counterfactual explanation
// ---------------------------------------------------------------------------

export const getAiInsights = async (payload) => {
  await delay(MOCK_DELAY_MS * 2);
  const score = parseFloat(payload?.risk_score) || 0;
  const probability = score / 100;
  const readmissionCost = 13000 + Math.round(score * 30);
  const interventionCost = 200 + Math.round(score * 1.5);
  const expectedCostAvoided = Math.round(probability * readmissionCost);
  const netRoi = expectedCostAvoided - interventionCost;
  const roiRatio = Math.round((expectedCostAvoided / interventionCost) * 100) / 100;
  const topDriver = payload?.drivers?.[0]?.label || 'the leading clinical risk driver';
  const targetBand = score >= 80 ? 'Medium' : 'Low';

  return {
    estimated_readmission_cost_usd: readmissionCost,
    estimated_intervention_cost_usd: interventionCost,
    expected_cost_avoided_usd: expectedCostAvoided,
    net_roi_usd: netRoi,
    roi_ratio: roiRatio,
    roi_rationale: [
      `At a ${score.toFixed(1)}% predicted readmission probability, this outreach is projected to avoid about $${expectedCostAvoided.toLocaleString()} in expected readmission costs.`,
      `The intervention itself costs roughly $${interventionCost.toLocaleString()}, for a net benefit of $${netRoi.toLocaleString()}.`,
    ],
    counterfactual_explanation: [
      `${topDriver} is the most modifiable driver identified for this patient.`,
      `Addressing it through targeted follow-up would plausibly shift risk down toward the ${targetBand} band, meaningfully reducing the 30 day readmission probability.`,
    ],
  };
};

// ---------------------------------------------------------------------------
// Per-week narrative — why one week's score moved the way it did
// ---------------------------------------------------------------------------

export const getWeekNarrative = async (payload) => {
  await delay(MOCK_DELAY_MS * 2);
  const score = parseFloat(payload?.risk_score) || 0;
  const band = payload?.risk_band || 'Low';
  const delta = payload?.delta;
  const topDriver = payload?.drivers?.[0];

  const bullets = [];

  if (delta === null || delta === undefined) {
    bullets.push(`This is the first tracked week, establishing a ${band.toLowerCase()} band baseline of ${score.toFixed(1)}%.`);
  } else if (delta > 0.4) {
    bullets.push(`The score rose ${delta.toFixed(1)} points to ${score.toFixed(1)}%, placing this patient in the ${band} band.`);
  } else if (delta < -0.4) {
    bullets.push(`The score fell ${Math.abs(delta).toFixed(1)} points to ${score.toFixed(1)}%, remaining in the ${band} band.`);
  } else {
    bullets.push(`The score held roughly steady at ${score.toFixed(1)}% in the ${band} band.`);
  }

  if (topDriver) {
    bullets.push(`${topDriver.label} was ${topDriver.value} this week, the most notable factor tracked.`);
    if (topDriver.explanation) {
      bullets.push(topDriver.explanation);
    }
  } else {
    bullets.push('No single dominant driver stood out in the tracked data this week.');
  }

  bullets.push('Continue tracking this alongside routine weekly monitoring.');

  return { narrative: bullets };
};

export const getTopDrivers = async (_riskBand = 'High') => {
  await delay(MOCK_DELAY_MS);
  return [
    { name: 'Predicted likelihood of missing follow-up appointments', count: 18, percent: '75%' },
    { name: 'Prior hospital admissions in the past year', count: 16, percent: '67%' },
    { name: 'Emergency department visits in the past 90 days', count: 14, percent: '58%' },
    { name: 'Low engagement with outpatient care (proxy score)', count: 9,  percent: '38%' },
    { name: 'Comorbidity burden score', count: 6, percent: '25%' },
  ];
};
