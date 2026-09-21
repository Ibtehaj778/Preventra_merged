import { useState, useMemo } from 'react';
import { DollarSign, TrendingUp, Users } from 'lucide-react';
import { SectionHeader, KPICard } from '../../components/shared';
import { SkeletonCard, SkeletonChart } from '../../components/shared/LoadingSkeleton';
import { SEGMENT_COLORS, SEGMENT_SHORT } from '../../data/mockData';
import CostDriverStackedBar from '../../components/charts/CostDriverStackedBar';
import { useDownstreamCost } from '../../hooks/useDownstreamCost';

const fmtMoney = (n) => {
  if (!Number.isFinite(n)) return '—';
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(1)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${Math.round(n)}`;
};

const fmtPct = (n) => Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : '—';

export default function DownstreamCostPanel() {
  const { data, loading, error } = useDownstreamCost();
  const [horizon, setHorizon] = useState(5); // 5 or 10

  const clusters = data?.by_cluster ?? [];
  const total = horizon === 5 ? data?.population_total_5yr : data?.population_total_10yr;
  const n = data?.n_patients_total ?? 0;
  const avgPerPatient = n ? total / n : 0;
  const driverDist = data?.primary_cost_driver_distribution ?? {};
  const topDriver = Object.entries(driverDist).sort((a, b) => b[1] - a[1])[0];

  const clusterCards = useMemo(() =>
    clusters.map((c, i) => {
      const cost = horizon === 5 ? c.avg_downstream_cost_5yr : c.avg_downstream_cost_10yr;
      return (
        <div key={c.cluster_id} className="card p-4 animate-fade-up"
             style={{ animationDelay: `${i * 0.05}s`, borderTop: `3px solid ${SEGMENT_COLORS[c.cluster_id]}` }}>
          <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: SEGMENT_COLORS[c.cluster_id] }}>
            Cluster {c.cluster_id}
          </div>
          <div className="text-xs text-gray-600 mt-0.5 leading-tight">{c.cluster_label ?? SEGMENT_SHORT[c.cluster_id]}</div>
          <div className="font-display text-xl font-semibold text-gray-800 mt-3">{fmtMoney(cost)}</div>
          <div className="text-[11px] text-gray-400 mt-0.5">avg per patient / {horizon}-yr</div>
          <div className="mt-3 grid grid-cols-2 gap-2 text-[11px]">
            <div>
              <div className="text-gray-400">ESRD @ 5yr</div>
              <div className="font-mono font-semibold">{fmtPct(c.esrd_probability_5yr)}</div>
            </div>
            <div>
              <div className="text-gray-400">CV @ 5yr</div>
              <div className="font-mono font-semibold">{fmtPct(c.cv_event_probability_5yr)}</div>
            </div>
          </div>
        </div>
      );
    }), [clusters, horizon]);

  if (error) {
    return (
      <div className="card p-6">
        <SectionHeader title="Downstream Cost by Cluster" />
        <div className="text-sm text-red-600">Failed to load /api/consequence/downstream-cost. Check the backend is running and Mongo is populated.</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Header with horizon toggle */}
      <div className="card p-5">
        <SectionHeader
          title="Downstream Cost by Cluster"
          sub="Projected 5- and 10-year per-patient spend after dropout, from the Markov consequence model"
          action={
            <div className="flex items-center gap-1 rounded-lg p-1" style={{ background: '#F7FAFC' }}>
              {[5, 10].map(h => (
                <button key={h} onClick={() => setHorizon(h)}
                  className="px-3 py-1.5 rounded-md text-xs font-semibold transition-all"
                  style={{
                    background: horizon === h ? 'var(--color-primary)' : 'transparent',
                    color:      horizon === h ? 'white' : 'var(--text-secondary)',
                  }}>
                  {h}-year
                </button>
              ))}
            </div>
          }
        />

        {/* KPI cards */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-6">
          {loading ? (
            <>
              <SkeletonCard h={110} /><SkeletonCard h={110} /><SkeletonCard h={110} />
            </>
          ) : (
            <>
              <KPICard label={`Population ${horizon}-yr exposure`} value={fmtMoney(total)}
                sub={`${n.toLocaleString()} patients, off-therapy projection`}
                icon={DollarSign} color="#C62828" />
              <KPICard label="Avg cost per patient"                 value={fmtMoney(avgPerPatient)}
                sub={`Population mean at ${horizon}-yr horizon`}
                icon={Users} color="#EF6C00" />
              <KPICard label="Top cost driver"                       value={topDriver ? topDriver[0].replace('_', ' ') : '—'}
                sub={topDriver ? `${fmtPct(topDriver[1])} of patients` : ''}
                icon={TrendingUp} color="#1E88E5" />
            </>
          )}
        </div>

        {/* Stacked bar chart */}
        <div>
          <div className="text-sm font-semibold text-gray-700 mb-2">Cost breakdown by driver (5-year, per-patient avg)</div>
          {loading ? <SkeletonChart h={300} /> : <CostDriverStackedBar data={clusters} height={300} />}
          <div className="text-[11px] text-gray-400 mt-2 leading-relaxed">
            Uncontrolled T2D includes both S1 (Uncontrolled) and S2 (CKD/nephropathy) cost buckets per the scope decision.
            CV event captures both acute-episode cost and follow-up years. ESRD is dialysis PPPY.
          </div>
        </div>
      </div>

      {/* Per-cluster cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {loading
          ? Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} h={180} />)
          : clusterCards}
      </div>
    </div>
  );
}
