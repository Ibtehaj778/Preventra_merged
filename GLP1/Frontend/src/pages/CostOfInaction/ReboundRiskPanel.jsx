import { useMemo, useState } from 'react';
import { Activity, AlertTriangle, TrendingUp } from 'lucide-react';
import { SectionHeader } from '../../components/shared';
import { SkeletonCard, SkeletonChart } from '../../components/shared/LoadingSkeleton';
import { SEGMENT_COLORS, SEGMENT_SHORT } from '../../data/mockData';
import ReboundTrajectoryChart from '../../components/charts/ReboundTrajectoryChart';
import { useReboundRisk } from '../../hooks/useReboundRisk';

const SCENARIOS = [
  { id: 'early',  label: 'Early (Day 30)',  sub: 'Minimal on-therapy exposure' },
  { id: 'median', label: 'Median',           sub: 'Cluster-empirical dropout timing' },
  { id: 'late',   label: 'Late (Day 150)',   sub: 'Reached steady state' },
];

const severityColor = (s) => {
  if (s == null) return { bg: '#F7FAFC', color: '#718096', label: '—' };
  if (s < 0.3)   return { bg: '#E8F5E9', color: '#2E7D32', label: 'Low' };
  if (s < 0.6)   return { bg: '#FFF3E0', color: '#EF6C00', label: 'Moderate' };
  return              { bg: '#FFEBEE', color: '#C62828', label: 'High' };
};

const fmtPct = (n) => Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : '—';

/** Radial-progress gauge for a severity score in [0,1]. */
function SeverityGauge({ value, size = 88 }) {
  const stroke = 8;
  const r = (size - stroke) / 2;
  const circ = 2 * Math.PI * r;
  const pct = Math.max(0, Math.min(1, value ?? 0));
  const dash = circ * pct;
  const { color } = severityColor(pct);
  return (
    <svg width={size} height={size} className="flex-shrink-0">
      <circle cx={size / 2} cy={size / 2} r={r} stroke="#EDF2F7" strokeWidth={stroke} fill="none" />
      <circle
        cx={size / 2} cy={size / 2} r={r}
        stroke={color} strokeWidth={stroke} fill="none"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform={`rotate(-90 ${size / 2} ${size / 2})`}
      />
      <text x="50%" y="50%" dominantBaseline="middle" textAnchor="middle"
            style={{ fontSize: 18, fontWeight: 700, fill: color, fontFamily: 'ui-monospace, monospace' }}>
        {pct.toFixed(2)}
      </text>
    </svg>
  );
}

export default function ReboundRiskPanel() {
  const { data, loading, error } = useReboundRisk();
  const [scenario, setScenario] = useState('median');

  const clusters       = data?.by_cluster ?? [];
  const trajectory     = data?.trajectory_by_cluster ?? [];
  const sensitivity    = data?.sensitivity ?? [];
  const populationT2D  = data?.population_t2d_incidence_12mo ?? null;

  // Sensitivity-based severity per cluster for the currently-selected scenario.
  const sensitivityByCluster = useMemo(() => {
    const map = new Map();
    sensitivity.forEach(entry => {
      const s = entry.scenarios?.find(x => x.scenario === scenario);
      if (s) map.set(entry.cluster_id, s);
    });
    return map;
  }, [sensitivity, scenario]);

  if (error) {
    return (
      <div className="card p-6">
        <SectionHeader title="Metabolic Rebound Risk" />
        <div className="text-sm text-red-600">Failed to load /api/consequence/rebound-risk. Check the backend is running and Mongo is populated.</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header + scenario toggle */}
      <div className="card p-5">
        <SectionHeader
          title="Metabolic Rebound Risk"
          sub="12-month HbA1c trajectory post-dropout, sourced from GLP-1 extension trials"
          action={
            <div className="flex items-center gap-2 text-xs">
              <Activity size={13} className="text-gray-400" />
              <span className="text-gray-500 font-medium">Dropout timing:</span>
              <div className="flex items-center gap-1 rounded-lg p-1" style={{ background: '#F7FAFC' }}>
                {SCENARIOS.map(s => (
                  <button key={s.id} onClick={() => setScenario(s.id)}
                    className="px-2.5 py-1 rounded-md text-xs font-semibold transition-all"
                    title={s.sub}
                    style={{
                      background: scenario === s.id ? 'var(--color-primary)' : 'transparent',
                      color:      scenario === s.id ? 'white' : 'var(--text-secondary)',
                    }}>
                    {s.label}
                  </button>
                ))}
              </div>
            </div>
          }
        />

        {/* Trajectory chart */}
        <div>
          {loading ? <SkeletonChart h={320} /> : <ReboundTrajectoryChart trajectoryByCluster={trajectory} scenario={scenario} height={320} />}
          <div className="text-[11px] text-gray-400 mt-2 leading-relaxed">
            One line per cluster. Reference lines mark the ADA T2D threshold (6.5) and the "uncontrolled" cutoff (8.0).
            The scenario toggle re-projects every patient at the selected dropout day.
          </div>
        </div>
      </div>

      {/* Severity gauge cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} h={200} />)
          : clusters.map((c, i) => {
              // Use sensitivity value for currently-selected scenario if available; otherwise fall back to overall.
              const s = sensitivityByCluster.get(c.cluster_id);
              const severity = s?.avg_severity_score ?? c.avg_severity_score;
              const p_t2d    = s?.p_new_t2d_12mo_mean ?? c.p_new_t2d_12mo_mean;
              const p_unc    = s?.p_uncontrolled_12mo_mean ?? c.p_uncontrolled_12mo_mean;
              const badge    = severityColor(severity);
              return (
                <div key={c.cluster_id} className="card p-4 animate-fade-up"
                     style={{ animationDelay: `${i * 0.05}s`, borderTop: `3px solid ${SEGMENT_COLORS[c.cluster_id]}` }}>
                  <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: SEGMENT_COLORS[c.cluster_id] }}>
                    Cluster {c.cluster_id}
                  </div>
                  <div className="text-xs text-gray-600 leading-tight mb-3">{c.cluster_label ?? SEGMENT_SHORT[c.cluster_id]}</div>

                  <div className="flex items-center gap-3">
                    <SeverityGauge value={severity} />
                    <div className="flex flex-col">
                      <span className="inline-block px-2 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider"
                            style={{ background: badge.bg, color: badge.color }}>
                        {badge.label} severity
                      </span>
                      <span className="text-[11px] text-gray-500 mt-1">at {scenario} dropout</span>
                    </div>
                  </div>

                  <div className="mt-3 grid grid-cols-1 gap-1.5 text-[11px]">
                    <div className="flex justify-between">
                      <span className="text-gray-400">New T2D @ 12mo</span>
                      <span className="font-mono font-semibold">{fmtPct(p_t2d)}</span>
                    </div>
                    <div className="flex justify-between">
                      <span className="text-gray-400">Uncontrolled @ 12mo</span>
                      <span className="font-mono font-semibold">{fmtPct(p_unc)}</span>
                    </div>
                  </div>
                </div>
              );
            })}
      </div>

      {/* Population-level T2D incidence banner */}
      {!loading && populationT2D != null && (
        <div className="card p-4 flex items-center justify-between"
             style={{ background: 'linear-gradient(135deg, #FFF9F0, #FFF3E0)', borderColor: '#FFE0B2' }}>
          <div className="flex items-center gap-3">
            <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: '#EF6C00' }}>
              <TrendingUp size={16} color="white" />
            </div>
            <div>
              <div className="text-xs font-bold uppercase tracking-wider" style={{ color: '#EF6C00' }}>Population projection</div>
              <div className="text-sm text-gray-700 mt-0.5">
                <span className="font-mono font-bold text-lg text-gray-900">{fmtPct(populationT2D)}</span>
                <span className="text-gray-500 ml-1">expected new-onset T2D incidence within 12 months among pre-DM dropouts</span>
              </div>
            </div>
          </div>
          <AlertTriangle size={16} className="text-orange-400 flex-shrink-0" />
        </div>
      )}
    </div>
  );
}
