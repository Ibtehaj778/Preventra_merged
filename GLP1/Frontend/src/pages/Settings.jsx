import { useState } from 'react';
import { Activity, Database, AlertTriangle, ChevronDown, ChevronUp, Stethoscope, Building2 } from 'lucide-react';
import { dataSources } from '../data/mockData';
import { useModelInfo } from '../hooks/useModelInfo';
import { ProgressBar } from '../components/shared';
import { useRole } from '../context/RoleContext';

const LIMITATIONS = [
  {
    title: 'Synthetic Survival Times',
    body: 'Time-to-dropout was approximated from cluster adherence rates using an exponential model — not derived from observed longitudinal timestamps. When real claims data with prescription fill dates becomes available, this module should be rebuilt.',
  },
  {
    title: 'system_refill_score Direction Anomaly',
    body: 'Pearson correlation with is_adherent is −0.44, meaning higher refill reliability shows lower adherence. This is counterintuitive and may indicate a compression or inversion artifact in the CMS mapping layer. Requires investigation before external presentation.',
  },
  {
    title: 'has_hypertension Dead Column',
    body: 'All patients have has_hypertension = 0, causing comorbidity_score to max at 2 instead of 3. The NHANES blood pressure eligibility filter may have been set too strictly or the column mapping was not applied correctly.',
  },
  {
    title: 'Soft Cluster Boundaries',
    body: 'All k-values returned silhouette scores in the 0.22–0.26 range. Cluster boundaries are soft and should not be presented as hard biological subgroups. They are analytically useful for stratification but overlap significantly at the margins.',
  },
  {
    title: 'Class Imbalance Correction via Upsampling',
    body: 'Raw dataset showed 33.5% adherence vs the expected ~47%. Upsampling was applied to the minority class before model training. Absolute adherence counts in training data are synthetic.',
  },
];

function Collapsible({ title, children }) {
  const [open, setOpen] = useState(false);
  return (
    <div className="border border-gray-200 rounded-xl overflow-hidden">
      <button onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-4 py-3 text-left hover:bg-gray-50 transition-colors">
        <span className="text-sm font-medium text-gray-700 flex items-center gap-2">
          <AlertTriangle size={13} className="text-orange-400 flex-shrink-0" />
          {title}
        </span>
        {open ? <ChevronUp size={14} className="text-gray-400" /> : <ChevronDown size={14} className="text-gray-400" />}
      </button>
      {open && (
        <div className="px-4 py-3 text-xs text-gray-600 leading-relaxed border-t border-gray-100 bg-orange-50">
          {children}
        </div>
      )}
    </div>
  );
}

export default function Settings() {
  const { roleLabel, isCostView } = useRole();
  const { data: modelInfo } = useModelInfo();

  const PERF_METRICS = [
    ['Accuracy',  modelInfo.accuracy,  'Primary classification accuracy on held-out test set'],
    ['Precision', modelInfo.precision, 'True positive rate among all predicted positives'],
    ['Recall',    modelInfo.recall,    'Fraction of true dropout patients correctly identified'],
    ['F1 Score',  modelInfo.f1,        'Harmonic mean of precision and recall'],
    ['AUC-ROC',   modelInfo.auc,       'Discrimination ability across all thresholds'],
  ];

  return (
    <div className="max-w-[900px] mx-auto space-y-6 animate-fade-in">

      {/* ── Model performance ─────────────────────────────────── */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: '#EBF4FF' }}>
            <Activity size={17} style={{ color: 'var(--color-primary)' }} />
          </div>
          <div>
            <div className="font-semibold text-gray-800">Model Performance</div>
            <div className="text-xs text-gray-400">{modelInfo.name}</div>
          </div>
        </div>

        <div className="text-xs text-gray-500 font-mono bg-gray-50 px-3 py-2 rounded-lg mb-5 leading-relaxed">
          {modelInfo.params}
        </div>

        <div className="space-y-3">
          {PERF_METRICS.map(([label, val, hint]) => (
            <div key={label} className="flex items-center gap-4">
              <span className="text-xs text-gray-500 w-20 flex-shrink-0">{label}</span>
              <div className="flex-1">
                <ProgressBar value={val} color="var(--color-primary)" height={6} />
              </div>
              <span className="text-xs font-semibold font-mono text-gray-800 w-12 text-right">
                {(val * 100).toFixed(1)}%
              </span>
              {val >= 0.75 && (
                <span className="text-[10px] text-green-600 font-semibold w-12 flex-shrink-0">Target</span>
              )}
            </div>
          ))}
        </div>

        <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4 pt-5 border-t border-gray-100">
          {[
            ['Decision Threshold', modelInfo.threshold.toFixed(2)],
            ['Training Set',       `${modelInfo.trainSize.toLocaleString()} pts`],
            ['Test Set',           `${modelInfo.testSize.toLocaleString()} pts`],
            ['Last Trained',       modelInfo.lastTrained],
          ].map(([k, v]) => (
            <div key={k} className="text-center">
              <div className="font-display text-xl text-gray-800">{v}</div>
              <div className="text-[10px] text-gray-400 uppercase tracking-wider mt-0.5">{k}</div>
            </div>
          ))}
        </div>
      </div>

      {/* ── Data sources ─────────────────────────────────────── */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: '#E8F5E9' }}>
            <Database size={17} style={{ color: '#2E7D32' }} />
          </div>
          <div>
            <div className="font-semibold text-gray-800">Data Sources</div>
            <div className="text-xs text-gray-400">
              5 real-world public health datasets fused in the data pipeline
            </div>
          </div>
        </div>
        <table className="data-table">
          <thead>
            <tr>
              <th>Dataset</th>
              <th>Creator</th>
              <th>Records Used</th>
              <th>Role in Pipeline</th>
            </tr>
          </thead>
          <tbody>
            {dataSources.map((ds, i) => (
              <tr key={i}>
                <td className="font-semibold text-sm">{ds.name}</td>
                <td>
                  <span className="text-xs font-mono bg-gray-100 px-1.5 py-0.5 rounded">
                    {ds.creator}
                  </span>
                </td>
                <td><span className="text-xs text-gray-600">{ds.records}</span></td>
                <td className="text-xs text-gray-500 leading-relaxed">{ds.description}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* ── Known limitations ────────────────────────────────── */}
      <div className="card p-6">
        <div className="flex items-center gap-3 mb-5">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center bg-orange-50">
            <AlertTriangle size={17} className="text-orange-500" />
          </div>
          <div>
            <div className="font-semibold text-gray-800">Known Limitations</div>
            <div className="text-xs text-gray-400">
              Documented flags for clinical and payer audiences — expand each for details
            </div>
          </div>
        </div>
        <div className="space-y-2">
          {LIMITATIONS.map((lim, i) => (
            <Collapsible key={i} title={lim.title}>{lim.body}</Collapsible>
          ))}
        </div>
      </div>

      {/* ── Role ─────────────────────────────────────────────── */}
      <div className="card p-6">
        <div className="font-semibold text-gray-800 mb-1">Role</div>
        <div className="text-xs text-gray-400 mb-5">
          Assigned by your administrator. It decides which panels are foregrounded
          and which data you can open; ask them if it needs to change.
        </div>
        <div className="flex items-center gap-2 text-sm font-medium text-gray-700">
          {isCostView ? <Building2 size={14} /> : <Stethoscope size={14} />}
          {roleLabel}
        </div>
      </div>
    </div>
  );
}
