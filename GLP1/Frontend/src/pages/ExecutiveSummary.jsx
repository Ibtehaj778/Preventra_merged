import { BarChart, Bar, Cell, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts';
import { Activity, DollarSign, Users, TrendingDown, AlertTriangle, BarChart2, ArrowRight, Bell } from 'lucide-react';
import { KPICard, SectionHeader, ChartTooltip } from '../components/shared';
import { SEGMENT_COLORS } from '../data/mockData';
import { useRole } from '../context/RoleContext';
import { Link } from 'react-router-dom';
import { useSummary } from '../hooks/useSummary';

const fmt = (n) => n >= 1e6 ? `$${(n/1e6).toFixed(1)}M` : n >= 1e3 ? `$${(n/1e3).toFixed(1)}K` : `$${n.toLocaleString()}`;

/* ── Adherence progress bar color ──────────────────────────────────── */
function getAdherenceBarColor(pct) {
  if (pct >= 70) return '#43A047';
  if (pct >= 40) return '#FF7043';
  return '#EF5350';
}

/* ── Segment Card Component ────────────────────────────────────────── */
function SegmentCard({ seg, delay }) {
  const barColor = getAdherenceBarColor(seg.adherencePct);
  return (
    <div
      className="card card-hover p-0 animate-fade-up flex flex-col"
      style={{
        animationDelay: `${delay}s`,
        borderTop: `3px solid ${seg.color}`,
        minWidth: 0,
      }}
    >
      {/* Header */}
      <div className="px-4 pt-4 pb-3">
        <div className="flex items-start justify-between gap-2 mb-1">
          <div>
            <h3 className="text-sm font-semibold text-gray-800 leading-snug">{seg.segment}</h3>
            <span className="text-xs text-gray-400">{seg.n.toLocaleString()} patients</span>
          </div>
          <span
            className="inline-flex items-center px-2 py-0.5 rounded-full text-[10px] font-semibold whitespace-nowrap flex-shrink-0"
            style={{
              background: seg.isHealthy ? '#E8F5E9' : '#FFEBEE',
              color: seg.isHealthy ? '#2E7D32' : '#C62828',
            }}
          >
            {seg.isHealthy ? 'healthy' : 'at risk'}
          </span>
        </div>

        {/* Adherence Percentage */}
        <div className="mt-3 mb-2">
          <span className="text-2xl font-bold" style={{ color: barColor, fontFamily: 'DM Serif Display, serif' }}>
            {seg.adherencePct}%
          </span>
          <span className="text-xs text-gray-400 ml-1.5">adherent</span>
        </div>

        {/* Progress bar */}
        <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#EDF2F7' }}>
          <div
            className="h-full rounded-full transition-all duration-700"
            style={{ width: `${seg.adherencePct}%`, background: barColor }}
          />
        </div>
      </div>

      {/* Divider */}
      <div style={{ borderTop: '1px solid var(--border)' }} />

      {/* Stats */}
      <div className="px-4 py-3 space-y-2">
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">Dropouts</span>
          <span className="text-sm font-semibold text-gray-700 font-mono">{seg.dropouts.toLocaleString()}</span>
        </div>
        <div className="flex items-center justify-between">
          <span className="text-xs text-gray-400">$ at risk</span>
          <span className="text-sm font-semibold text-gray-700 font-mono">{fmt(seg.atRisk)}</span>
        </div>
      </div>
    </div>
  );
}

/* ── Population Bar Component ──────────────────────────────────────── */
function PopulationBar({ totalN, segmentCards }) {
  return (
    <div className="mb-5">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-2">
          <span className="text-xs font-semibold uppercase tracking-wider text-gray-500">
            Patient Population
          </span>
          <span className="text-xs font-mono font-semibold text-gray-400">
            — {totalN.toLocaleString()} total
          </span>
        </div>
        <span className="hidden sm:block text-xs font-semibold uppercase tracking-wider text-gray-400">
          Share of Total
        </span>
      </div>

      {/* Stacked bar */}
      <div className="flex rounded-lg overflow-hidden h-3 shadow-sm">
        {segmentCards.map((seg, i) => (
          <div
            key={i}
            style={{
              width: `${seg.shareOfTotal * 100}%`,
              background: seg.color,
              transition: 'width 0.5s ease',
            }}
            title={`${seg.segment}: ${Math.round(seg.shareOfTotal * 100)}%`}
          />
        ))}
      </div>

      {/* Percentage labels */}
      <div className="flex mt-1.5">
        {segmentCards.map((seg, i) => (
          <div
            key={i}
            style={{ width: `${seg.shareOfTotal * 100}%` }}
            className="text-[11px] text-gray-400 font-mono overflow-hidden whitespace-nowrap"
          >
            {Math.round(seg.shareOfTotal * 100)}%
          </div>
        ))}
      </div>
    </div>
  );
}

/* ── Main Page ─────────────────────────────────────────────────────── */
export default function ExecutiveSummary() {
  const { isInsurer } = useRole();
  const { data: summaryData } = useSummary();

  const summaryKPIs        = summaryData.kpis;
  const adherenceBySegment = summaryData.adherence_by_segment;
  const globalSHAPDrivers  = summaryData.global_shap_drivers;
  const dropoutByWindow    = summaryData.dropout_by_window;

  const totalN = adherenceBySegment.reduce((s, seg) => s + seg.n, 0);
  const segmentCards = adherenceBySegment.map(seg => {
    const dropouts    = Math.round((1 - seg.adherence) * seg.n);
    const atRisk      = Math.round(dropouts * (summaryKPIs.avgAnnualCost ?? summaryKPIs.avg_annual_cost ?? 10603));
    const shareOfTotal = seg.n / (totalN || 1);
    const adherencePct = Math.round(seg.adherence * 100);
    const isHealthy    = adherencePct >= 70;
    return { ...seg, dropouts, atRisk, shareOfTotal, adherencePct, isHealthy };
  });

  return (
    <div className="exec-summary-page">
      {isInsurer && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium animate-fade-up"
          style={{ background: '#EBF4FF', color: '#1B4F8A', border: '1px solid #BFDBFE' }}>
          <AlertTriangle size={15} /> Insurer View — Financial metrics and ROI analysis are foregrounded
        </div>
      )}

      {!isInsurer && (() => {
        const dropouts = Math.round(
          (summaryKPIs.dropoutRate ?? summaryKPIs.dropout_rate ?? 0) *
          (summaryKPIs.totalPatients ?? summaryKPIs.total_patients ?? 0)
        );
        return dropouts > 0 ? (
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3 px-4 py-3 rounded-xl text-sm font-medium animate-fade-up"
            style={{ background: '#FFEBEE', color: '#C62828', border: '1px solid #FFCDD2' }}>
            <span className="flex items-center gap-2.5">
              <Bell size={15} />
              <b>{dropouts.toLocaleString()}</b> patients are currently non-adherent and at dropout risk.
            </span>
            <Link to="/patients"
              className="flex items-center gap-1 text-xs font-semibold whitespace-nowrap underline-offset-2 hover:underline"
              style={{ color: '#C62828' }}>
              Review Patient Risk Panel <ArrowRight size={12} />
            </Link>
          </div>
        ) : null;
      })()}

      {/* ── Zone A — KPI Cards ─────────────────────────────────────────── */}
      <div className="exec-kpi-grid">
        <KPICard label="Total Patients" value={(summaryKPIs.totalPatients ?? summaryKPIs.total_patients ?? 0).toLocaleString()} icon={Users} color="#1B4F8A" delay={0} />
        <KPICard label="Overall Adherence" value={`${((summaryKPIs.adherenceRate ?? summaryKPIs.adherence_rate ?? 0)*100).toFixed(0)}%`} icon={Activity}
          sub="vs 47% published benchmark" trend={0} trendLabel="Aligned with benchmark" color="#2E7D32" delay={0.05} />
        <KPICard label="Population Dropout" value={`${((summaryKPIs.dropoutRate ?? summaryKPIs.dropout_rate ?? 0)*100).toFixed(0)}%`} icon={TrendingDown}
          sub="Patients discontinuing therapy" trend={-1} trendLabel="Above ideal" color="#C62828" delay={0.10} />
        <KPICard label="Avg Annual Drug Cost" value={`$${(summaryKPIs.avgAnnualCost ?? summaryKPIs.avg_annual_cost ?? 0).toLocaleString()}`} icon={DollarSign}
          sub="Per patient per year" color="#EF6C00" delay={0.15} />
        <KPICard label="Est. Wasted Spend" value={fmt(summaryKPIs.wastedSpendAnnual ?? summaryKPIs.wasted_spend_annual ?? 0)} icon={BarChart2}
          sub="Paid for patients who dropout" trend={-1} trendLabel="Opportunity for reduction" color="#C62828" delay={0.20} />
      </div>

      {/* ── Zone B — Who's Dropping Out (Unified Section) ────────────── */}
      <div className="card p-5 md:p-6 animate-fade-up stagger-3">
        <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-2 mb-5">
          <div>
            <h2 className="font-display text-lg font-semibold text-gray-800" style={{ fontFamily: 'DM Serif Display, serif' }}>
              Who's dropping out, and why
            </h2>
            <p className="text-xs text-gray-400 mt-0.5">
              Four behavior segments identified from {totalN.toLocaleString()} patients · click a segment to drill down
            </p>
          </div>
          <Link
            to="/segments"
            className="inline-flex items-center gap-1 text-xs font-semibold whitespace-nowrap"
            style={{ color: 'var(--color-primary)' }}
          >
            Open Segment Explorer <ArrowRight size={13} />
          </Link>
        </div>

        <PopulationBar totalN={totalN} segmentCards={segmentCards} />

        {/* Segment Cards Grid */}
        <div className="exec-segment-grid">
          {segmentCards.map((seg, i) => (
            <SegmentCard key={i} seg={seg} delay={0.15 + i * 0.05} />
          ))}
        </div>
      </div>

      {/* ── Zone C — Dropout Timeline + Drivers / Wasted Spend ──────── */}
      <div className="exec-bottom-grid">
        {/* Zone C left — role-based */}
        <div className="card p-5 animate-fade-up stagger-5">
          {isInsurer ? (() => {
            const avgCost = summaryKPIs.avgAnnualCost ?? summaryKPIs.avg_annual_cost ?? 10603;
            const ranked = adherenceBySegment
              .map(s => ({
                name:      s.segment.split(' ').slice(0, 2).join(' '),
                value:     Math.round(avgCost / Math.max(s.adherence, 0.01)),
                color:     s.color,
                n:         s.n,
                adherence: s.adherence,
              }))
              .sort((a, b) => a.value - b.value);
            const best  = ranked[0].value;
            const worst = ranked[ranked.length - 1].value;
            return (
              <>
                <SectionHeader
                  title="Cost per Adherent Patient-Year"
                  sub="Ranked by payer value — annual drug spend ÷ adherence rate" />
                <div className="space-y-2 mt-1">
                  {ranked.map((d, i) => {
                    const isBest  = i === 0;
                    const isWorst = i === ranked.length - 1;
                    const tier =
                      isBest  ? { label: 'Best value',     bg: '#F0FFF4', tint: '#E8F5E9' } :
                      isWorst ? { label: 'Critical waste', bg: '#FFF8F8', tint: '#FFEBEE' } :
                      i === 1 ? { label: 'Strong value',   bg: 'white',   tint: '#F7FAFC' } :
                                { label: 'Inefficient',    bg: 'white',   tint: '#FFF3E0' };
                    return (
                      <div key={i}
                        className="flex items-center justify-between rounded-xl px-3 py-2.5 transition-all"
                        style={{
                          background: tier.bg,
                          border: `1px solid ${isBest ? '#C8E6C9' : isWorst ? '#FFCDD2' : '#E2E8F0'}`,
                          borderLeft: `4px solid ${d.color}`,
                        }}>
                        <div className="flex items-center gap-3 min-w-0">
                          <span className="font-display text-lg font-bold w-6 flex-shrink-0 text-center"
                                style={{ color: isBest ? '#2E7D32' : isWorst ? '#C62828' : '#CBD5E0' }}>
                            {i + 1}
                          </span>
                          <div className="min-w-0">
                            <div className="text-sm font-semibold text-gray-800 leading-tight truncate">{d.name}</div>
                            <div className="flex items-center gap-1.5 mt-0.5">
                              <span className="text-[9px] font-bold uppercase tracking-wider px-1.5 py-0.5 rounded"
                                    style={{ background: tier.tint, color: d.color }}>
                                {tier.label}
                              </span>
                              <span className="text-[10px] text-gray-400">
                                {Math.round(d.adherence * 100)}% adherent
                              </span>
                            </div>
                          </div>
                        </div>
                        <div className="text-right flex-shrink-0 ml-3">
                          <div className="font-display text-xl font-bold leading-none" style={{ color: d.color }}>
                            ${(d.value / 1000).toFixed(1)}<span className="text-sm">K</span>
                          </div>
                          <div className="text-[10px] text-gray-400 mt-1 font-mono">
                            {isBest ? 'baseline' : `${(d.value / best).toFixed(1)}× best`}
                          </div>
                        </div>
                      </div>
                    );
                  })}
                </div>
                <div className="mt-3 pt-3 border-t border-gray-100 flex items-center justify-between text-[10px] text-gray-400">
                  <span>Spread: <b className="text-gray-600 font-mono">${best.toLocaleString()}</b> → <b className="text-gray-600 font-mono">${worst.toLocaleString()}</b></span>
                  <span><b className="text-gray-600">{(worst / best).toFixed(1)}×</b> gap between best and worst</span>
                </div>
              </>
            );
          })() : (
            <>
              <SectionHeader title="Dropout Volume by Time Window" sub="Estimated patients discontinuing at each checkpoint" />
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={dropoutByWindow} margin={{ top: 4, right: 16, bottom: 0, left: 0 }}>
                  <CartesianGrid vertical={false} strokeDasharray="3 3" stroke="#EDF2F7" />
                  <XAxis dataKey="window" tick={{ fontSize: 11, fill: '#718096' }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} />
                  <YAxis tick={{ fontSize: 11, fill: '#718096' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTooltip />} />
                  <Bar dataKey="seg0" name="Low Urgency" fill={SEGMENT_COLORS[0]} stackId="a" />
                  <Bar dataKey="seg1" name="Financial Barrier" fill={SEGMENT_COLORS[1]} stackId="a" />
                  <Bar dataKey="seg2" name="Low Friction" fill={SEGMENT_COLORS[2]} stackId="a" />
                  <Bar dataKey="seg3" name="Moderate Risk" fill={SEGMENT_COLORS[3]} stackId="a" radius={[4,4,0,0]} />
                  <Legend iconType="circle" iconSize={8} formatter={v => <span style={{ fontSize: 10, color: '#718096' }}>{v}</span>} />
                </BarChart>
              </ResponsiveContainer>
            </>
          )}
        </div>

        {/* Global SHAP drivers or wasted spend (role-based) */}
        <div className="card p-5 animate-fade-up stagger-6">
          {isInsurer ? (
            <>
              <SectionHeader title="Wasted Spend by Segment" sub="Annual drug spend on patients who discontinue" />
              <ResponsiveContainer width="100%" height={240}>
                <BarChart data={adherenceBySegment.map(s => ({
                  name: s.segment.split(' ').slice(0,2).join(' '),
                  spend: Math.round((1-s.adherence) * s.n * 10603),
                }))} layout="vertical" margin={{ left: 0, right: 24, top: 4, bottom: 0 }}>
                  <CartesianGrid horizontal={false} strokeDasharray="3 3" stroke="#EDF2F7" />
                  <XAxis type="number" tickFormatter={v => `$${(v/1e6).toFixed(1)}M`} tick={{ fontSize: 10, fill: '#718096' }} axisLine={{ stroke: '#E2E8F0' }} tickLine={false} />
                  <YAxis type="category" dataKey="name" width={90} tick={{ fontSize: 10, fill: '#718096' }} axisLine={false} tickLine={false} />
                  <Tooltip content={<ChartTooltip formatter={v => `$${v.toLocaleString()}`} />} />
                  <Bar dataKey="spend" name="Wasted Spend" radius={[0,4,4,0]}>
                    {adherenceBySegment.map((s, i) => <Cell key={i} fill={s.color} />)}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </>
          ) : (
            <>
              <SectionHeader title="Top Population Dropout Drivers" sub="Mean absolute SHAP impact across all patients" />
              <div className="space-y-2.5 mt-1">
                {globalSHAPDrivers.slice(0, 6).map((d, i) => (
                  <div key={i} className="flex items-center gap-3">
                    <span
                      className="text-[10px] font-bold rounded-full flex items-center justify-center flex-shrink-0"
                      style={{
                        width: 22, height: 22, minWidth: 22,
                        background: i === 0 ? '#FFEBEE' : '#F7FAFC',
                        color: i === 0 ? '#C62828' : '#718096',
                      }}
                    >
                      {i+1}
                    </span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center justify-between mb-1">
                        <span className="text-xs text-gray-700 truncate font-medium">{d.feature}</span>
                        <span className="text-xs font-mono font-semibold ml-2 flex-shrink-0" style={{ color: '#4A5568' }}>
                          {d.importance.toFixed(3)}
                        </span>
                      </div>
                      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#EDF2F7' }}>
                        <div
                          className="h-full rounded-full transition-all duration-700"
                          style={{
                            width: `${(d.importance / 0.55) * 100}%`,
                            background: `hsl(${220 - i * 20}, 65%, ${45 + i * 3}%)`,
                          }}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
