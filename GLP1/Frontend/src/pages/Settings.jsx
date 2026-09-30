import { Activity, Info, Stethoscope, Building2 } from 'lucide-react';
import { useModelInfo } from '../hooks/useModelInfo';
import { ProgressBar } from '../components/shared';
import { useRole } from '../context/RoleContext';
import { useAuth } from '../context/AuthContext';
import { AUTH_BASE } from '../data/api';
import UserManagement from '../components/shared/UserManagement';
import PageState from '../components/shared/PageState';

// Stable, module-level: UserManagement reloads whenever this function changes.
const getToken = () => localStorage.getItem('glp1_token');

// Talha's goal for each metric when the model was trained (Model/model.ipynb).
const METRIC_TARGET = 0.75;

/**
 * Settings: who can use this hospital's account, and what the model is.
 *
 *   superadmin      User Management, About the model, full Model performance
 *   hospital_admin  User Management, About the model
 *   everyone else   their role
 *
 * The model's technical details (metrics, parameters, data pipeline notes) are
 * for our own team; hospitals get a plain-language summary instead.
 */
export default function Settings() {
  const { roleLabel, isCostView, isSuperadmin, isManager } = useRole();
  const { user } = useAuth();
  const { data: modelInfo, error: modelError } = useModelInfo();

  return (
    <div className="max-w-[900px] mx-auto space-y-6 animate-fade-in">

      {/* ── User Management (superadmin, hospital admin) ─────── */}
      {isManager && (
        <div className="card p-6">
          <UserManagement authBaseUrl={AUTH_BASE} getToken={getToken} me={user} />
        </div>
      )}

      {/* ── About the model (superadmin, hospital admin) ─────── */}
      {isManager && (!modelInfo
        ? <PageState error={modelError} label="the model details" />
        : <AboutModel info={modelInfo} />)}

      {/* ── Model performance (superadmin only) ──────────────── */}
      {isSuperadmin && modelInfo && <ModelPerformance info={modelInfo} />}

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

/* What a hospital needs to know about the model, in plain words. */
function AboutModel({ info }) {
  const rows = [
    ['What it does',
      'Estimates each patient’s chance of stopping their GLP-1 therapy within 6 months, and names the main reasons behind that estimate.'],
    ['What it learned from',
      'Patient profiles built from US public health data: the NHANES health survey, MEPS drug costs, CMS Medicare Part D prescribing, FDA side-effect reports and published GLP-1 trials.'],
    ['How reliable it is',
      `Tested on ${info.testSize.toLocaleString()} patients it had not seen during training: given one patient who stopped and one who stayed, it ranks the one who stopped as higher risk ${Math.round(info.auc * 100)}% of the time.`],
    ['Last updated', info.lastTrained],
  ];
  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-4">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: '#EBF4FF' }}>
          <Info size={17} style={{ color: 'var(--color-primary)' }} />
        </div>
        <div>
          <div className="font-semibold text-gray-800">About the dropout-risk model</div>
          <div className="text-xs text-gray-400">What the risk scores on these pages are, and where they come from</div>
        </div>
      </div>
      <dl className="divide-y divide-gray-100">
        {rows.map(([k, v]) => (
          <div key={k} className="grid gap-1 py-3 sm:grid-cols-[180px_1fr] sm:gap-4">
            <dt className="text-xs font-semibold uppercase tracking-wider text-gray-400">{k}</dt>
            <dd className="text-sm text-gray-700 leading-relaxed">{v}</dd>
          </div>
        ))}
      </dl>
      <p className="mt-3 rounded-lg px-3 py-2 text-xs leading-relaxed" style={{ background: '#FFF8E1', color: '#8D6E00' }}>
        <b>Demonstration data.</b> The patients shown today are a simulated dataset, not real patients.
        Before live use, the model is checked against your own patients&rsquo; refill history.
      </p>
    </div>
  );
}

/* The technical numbers, for our own team. The model predicts "will stay on
   therapy", so precision and recall are about the patients who stay. */
function ModelPerformance({ info }) {
  const metrics = [
    ['Accuracy',  info.accuracy,  'Share of test patients classified correctly'],
    ['Precision', info.precision, 'Of the patients predicted to stay, the share who did'],
    ['Recall',    info.recall,    'Of the patients who stayed, the share the model identified'],
    ['F1 Score',  info.f1,        'Balance of precision and recall'],
    ['AUC-ROC',   info.auc,       'How well it ranks a patient who stops above one who stays, across all thresholds'],
  ];
  return (
    <div className="card p-6">
      <div className="flex items-center gap-3 mb-5">
        <div className="w-9 h-9 rounded-xl flex items-center justify-center" style={{ background: '#EBF4FF' }}>
          <Activity size={17} style={{ color: 'var(--color-primary)' }} />
        </div>
        <div>
          <div className="font-semibold text-gray-800">Model performance</div>
          <div className="text-xs text-gray-400">{info.name} · visible to superadmins only</div>
        </div>
      </div>

      <div className="text-xs text-gray-500 font-mono bg-gray-50 px-3 py-2 rounded-lg mb-5 leading-relaxed">
        {info.params}
      </div>

      <div className="space-y-3">
        {metrics.map(([label, val, hint]) => (
          <div key={label} className="flex items-center gap-4" title={hint}>
            <span className="text-xs text-gray-500 w-20 flex-shrink-0">{label}</span>
            <div className="flex-1">
              <ProgressBar value={val} color="var(--color-primary)" height={6} />
            </div>
            <span className="text-xs font-semibold font-mono text-gray-800 w-12 text-right">
              {(val * 100).toFixed(1)}%
            </span>
            <span className="text-[10px] font-semibold w-20 flex-shrink-0"
                  style={{ color: val >= METRIC_TARGET ? '#2E7D32' : '#A0AEC0' }}>
              {val >= METRIC_TARGET ? 'Meets 75% goal' : 'Below 75% goal'}
            </span>
          </div>
        ))}
      </div>

      <div className="mt-5 grid grid-cols-2 md:grid-cols-4 gap-4 pt-5 border-t border-gray-100">
        {[
          ['Decision threshold', info.threshold.toFixed(2)],
          ['Training set',       `${info.trainSize.toLocaleString()} pts`],
          ['Test set',           `${info.testSize.toLocaleString()} pts`],
          ['Last trained',       info.lastTrained],
        ].map(([k, v]) => (
          <div key={k} className="text-center">
            <div className="font-display text-xl text-gray-800">{v}</div>
            <div className="text-[10px] text-gray-400 uppercase tracking-wider mt-0.5">{k}</div>
          </div>
        ))}
      </div>
    </div>
  );
}