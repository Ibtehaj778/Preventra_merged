import { useState, useMemo } from 'react';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { Link } from 'react-router-dom';
import { SectionHeader } from '../components/shared';
import { SkeletonCard, SkeletonChart } from '../components/shared/LoadingSkeleton';
import { SEGMENT_COLORS, SEGMENT_SHORT } from '../data/mockData';
import { useBudgetImpact } from '../hooks/useBudgetImpact';
import { TrendingDown, DollarSign, CheckCircle, XCircle, Download, Stethoscope } from 'lucide-react';
import { useRole } from '../context/RoleContext';

function ScenarioSlider({ label, sub, value, min, max, step, onChange, format }) {
  return (
    <div>
      <div className="flex justify-between items-baseline mb-1">
        <div>
          <label className="text-sm font-semibold text-gray-700">{label}</label>
          {sub && <div className="text-[11px] text-gray-400 mt-0.5">{sub}</div>}
        </div>
        <span className="font-mono font-bold text-xl" style={{ color: 'var(--color-primary)' }}>
          {format(value)}
        </span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(+e.target.value)} />
      <div className="flex justify-between text-[10px] text-gray-400 mt-1">
        <span>{format(min)}</span><span>{format(max)}</span>
      </div>
    </div>
  );
}

const fmtMoney = n =>
  n >= 1e6 ? `$${(n / 1e6).toFixed(2)}M` :
  n >= 1e3 ? `$${(n / 1e3).toFixed(0)}K` :
  `$${n}`;

export default function BudgetSimulator() {
  const { isInsurer } = useRole();
  const [dropoutReduction, setDropoutReduction] = useState(15);
  const [interventionCost, setInterventionCost] = useState(500);
  const [scope, setScope]                       = useState(100);
  const [exported, setExported]                 = useState(false);
  const { result: apiResult, loading, calculate } = useBudgetImpact();

  const isLoading = loading || !apiResult;
  const results   = apiResult ?? [];

  // Fire API call whenever sliders change (debounced via useMemo trigger)
  useMemo(() => {
    calculate(dropoutReduction, interventionCost, scope);
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [dropoutReduction, interventionCost, scope]);

  const totalNet              = results.reduce((a, r) => a + r.netSaving, 0);
  const totalWasteRecovered   = results.reduce((a, r) => a + r.wasteRecovered, 0);
  const totalInterventionCost = results.reduce((a, r) => a + r.interventionCost, 0);

  // 12-month cumulative savings trajectory
  const monthlyData = Array.from({ length: 13 }, (_, i) => ({
    month:            i,
    withIntervention: Math.round((totalNet / 12) * i),
    baseline:         0,
  }));

  const breakEvenMonth =
    totalNet > 0
      ? Math.ceil(totalInterventionCost / (totalWasteRecovered / 12))
      : null;

  const segmentCards = isLoading
    ? Array.from({ length: 4 }, (_, i) => <SkeletonCard key={i} h={240} />)
    : results.map((r, i) => (
        <div key={i} className="card p-4 animate-fade-up"
             style={{
               animationDelay: `${i * 0.06}s`,
               borderTop:      `3px solid ${SEGMENT_COLORS[i]}`,
               opacity:        !r.roiPositive ? 0.85 : 1,
             }}>
          <div className="flex items-start justify-between mb-3">
            <div>
              <div className="text-[10px] font-bold uppercase tracking-wider" style={{ color: SEGMENT_COLORS[i] }}>
                Cluster {i}
              </div>
              <div className="text-xs text-gray-600 mt-0.5 leading-tight">{r.label}</div>
            </div>
            {r.roiPositive
              ? <CheckCircle size={16} style={{ color: '#2E7D32' }} />
              : <XCircle    size={16} style={{ color: '#C62828' }} />}
          </div>
          <div className="space-y-2 text-xs">
            <div className="flex justify-between">
              <span className="text-gray-400">Patients</span>
              <span className="font-semibold">{r.n.toLocaleString()}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Dropout Rate</span>
              <span className="font-mono">
                {(r.baselineDropout * 100).toFixed(1)}%
                <span className="text-gray-400"> → </span>
                {(r.newDropout * 100).toFixed(1)}%
              </span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Waste Recovered</span>
              <span className="font-semibold text-green-700">{fmtMoney(r.wasteRecovered)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-gray-400">Intervention Cost</span>
              <span className="font-semibold text-orange-600">−{fmtMoney(r.interventionCost)}</span>
            </div>
            <div className="border-t border-gray-100 pt-2 flex justify-between">
              <span className="font-semibold text-gray-700">Net Saving</span>
              <span className="font-semibold font-mono"
                    style={{ color: r.roiPositive ? '#2E7D32' : '#C62828' }}>
                {r.roiPositive ? '+' : ''}{fmtMoney(r.netSaving)}
              </span>
            </div>
          </div>
          {!r.roiPositive && (
            <div className="mt-3 text-[10px] text-orange-700 bg-orange-50 rounded-lg p-2 leading-relaxed border border-orange-100">
              ROI negative — dropout rate too low to justify this intervention cost for this segment.
            </div>
          )}
        </div>
      ));

  const handleExport = () => {
    const lines = [
      'GLP-1 Adherence Platform — Budget Impact Scenario Report',
      `Generated: ${new Date().toLocaleDateString()}`,
      '',
      'SCENARIO PARAMETERS',
      `  Dropout Reduction Assumed: ${dropoutReduction}%`,
      `  Intervention Cost per Patient: $${interventionCost}`,
      `  Population in Program: ${scope}%`,
      '',
      'TOTAL RESULTS',
      `  Net Annual Saving: ${fmtMoney(totalNet)}`,
      `  Waste Recovered: ${fmtMoney(totalWasteRecovered)}`,
      `  Total Intervention Cost: ${fmtMoney(totalInterventionCost)}`,
      breakEvenMonth ? `  Break-even: Month ${breakEvenMonth}` : '  Break-even: Not achieved in 12 months',
      '',
      'PER-SEGMENT RESULTS',
      ...results.map(r =>
        `  ${r.label}: ${r.roiPositive ? '+' : ''}${fmtMoney(r.netSaving)} net saving (${r.n.toLocaleString()} patients)`
      ),
    ];
    const blob = new Blob([lines.join('\n')], { type: 'text/plain' });
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = 'glp1_budget_scenario.txt';
    a.click();
    URL.revokeObjectURL(url);
    setExported(true);
    setTimeout(() => setExported(false), 2500);
  };

  return (
    <div className="max-w-[1200px] mx-auto space-y-5 animate-fade-in">

      {/* ── Clinician context banner ─────────────────────────────── */}
      {!isInsurer && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3 px-4 py-3 rounded-xl text-sm font-medium animate-fade-up"
          style={{ background: '#F0FFF4', color: '#2E7D32', border: '1px solid #C8E6C9' }}>
          <span className="flex items-center gap-2.5">
            <Stethoscope size={15} />
            Clinician View — This simulator is designed for Insurer/Payer financial planning. All tools remain accessible.
          </span>
          <div className="flex flex-wrap items-center gap-3 text-xs font-semibold flex-shrink-0">
            <Link to="/patients" className="hover:underline underline-offset-2" style={{ color: '#2E7D32' }}>Patient Risk Panel →</Link>
            <Link to="/"         className="hover:underline underline-offset-2" style={{ color: '#2E7D32' }}>Executive Summary →</Link>
          </div>
        </div>
      )}

      {/* ── Sliders ────────────────────────────────────────────── */}
      <div className="card p-5 md:p-6">
        <SectionHeader
          title="Scenario Parameters"
          sub="Adjust assumptions to model different intervention strategies"
          action={
            <button onClick={handleExport}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors"
              style={{
                background: exported ? '#E8F5E9' : 'var(--color-primary)',
                color:      exported ? '#2E7D32' : 'white',
              }}>
              <Download size={13} />
              {exported ? 'Exported!' : 'Export Scenario'}
            </button>
          } />
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 md:gap-10">
          <ScenarioSlider
            label="Dropout Reduction Assumed"
            sub="From intervention program"
            value={dropoutReduction} min={5} max={50} step={5}
            onChange={setDropoutReduction} format={v => `${v}%`} />
          <ScenarioSlider
            label="Intervention Cost per Patient"
            sub="Annual cost of program"
            value={interventionCost} min={100} max={2000} step={100}
            onChange={setInterventionCost} format={v => `$${v}`} />
          <ScenarioSlider
            label="Population in Program"
            sub="% of patients enrolled"
            value={scope} min={10} max={100} step={10}
            onChange={setScope} format={v => `${v}%`} />
        </div>
      </div>

      {/* ── Total banner ────────────────────────────────────────── */}
      {isLoading ? (
        <SkeletonCard h={140} />
      ) : (
      <div className="card p-5 md:p-6 flex flex-col md:flex-row md:items-center md:justify-between gap-6"
           style={{
             background:   totalNet > 0 ? 'linear-gradient(135deg, #E8F5E9, #F1F8E9)' : 'linear-gradient(135deg, #FFEBEE, #FFF3F3)',
             borderColor:  totalNet > 0 ? '#C8E6C9' : '#FFCDD2',
           }}>
        <div>
          <div className="text-xs font-bold uppercase tracking-wider mb-1.5"
               style={{ color: totalNet > 0 ? '#2E7D32' : '#C62828' }}>
            {totalNet > 0 ? 'Positive ROI Scenario' : 'Negative ROI — Adjust Parameters'}
          </div>
          <div className="font-display text-4xl font-semibold"
               style={{ color: totalNet > 0 ? '#1B5E20' : '#B71C1C' }}>
            {totalNet > 0 ? '+' : ''}{fmtMoney(totalNet)}
          </div>
          <div className="text-sm mt-1" style={{ color: totalNet > 0 ? '#388E3C' : '#C62828' }}>
            Estimated annual net saving
          </div>
          <div className="text-xs text-gray-500 mt-1">
            {scope}% of population · ${interventionCost}/pt · {dropoutReduction}% dropout reduction
          </div>
        </div>
        <div className="grid grid-cols-3 gap-4 md:gap-8 text-center flex-shrink-0">
          {[
            ['Waste Recovered',   fmtMoney(totalWasteRecovered),   DollarSign,   '#2E7D32'],
            ['Intervention Cost', fmtMoney(totalInterventionCost), TrendingDown, '#EF6C00'],
            ['Break-even',        breakEvenMonth ? `Month ${breakEvenMonth}` : 'N/A', CheckCircle, '#1B4F8A'],
          ].map(([label, val, Icon, color]) => (
            <div key={label}>
              <Icon size={18} className="mx-auto mb-1.5" style={{ color }} />
              <div className="font-display text-xl font-semibold" style={{ color }}>{val}</div>
              <div className="text-[11px] text-gray-400 mt-0.5">{label}</div>
            </div>
          ))}
        </div>
      </div>
      )}

      {/* ── Per-segment cards ───────────────────────────────────── */}
      <div className="grid grid-cols-1 sm:grid-cols-2 xl:grid-cols-4 gap-4">
        {segmentCards}
      </div>

      {/* ── Cumulative impact chart ─────────────────────────────── */}
      {isLoading ? (
        <SkeletonChart h={280} />
      ) : (
      <div className="card p-5">
        <SectionHeader
          title="12-Month Cumulative Net Impact"
          sub="Projected savings trajectory — with intervention vs no-intervention baseline" />
        <ResponsiveContainer width="100%" height={240}>
          <AreaChart data={monthlyData} margin={{ top: 8, right: 24, bottom: 8, left: 8 }}>
            <defs>
              <linearGradient id="savingGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={totalNet > 0 ? '#43A047' : '#EF5350'} stopOpacity={0.25} />
                <stop offset="95%" stopColor={totalNet > 0 ? '#43A047' : '#EF5350'} stopOpacity={0} />
              </linearGradient>
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="#EDF2F7" />
            <XAxis dataKey="month" tickFormatter={v => v === 0 ? 'Start' : `M${v}`} tick={{ fontSize: 11 }} />
            <YAxis tickFormatter={v => fmtMoney(v)} tick={{ fontSize: 11 }} />
            {breakEvenMonth && breakEvenMonth <= 12 && (
              <ReferenceLine x={breakEvenMonth} stroke="var(--color-primary)" strokeDasharray="5 3"
                label={{ value: `Break-even M${breakEvenMonth}`, position: 'top', fontSize: 9, fill: 'var(--color-primary)' }} />
            )}
            <ReferenceLine y={0} stroke="#CBD5E0" />
            <Tooltip
              formatter={v => [fmtMoney(v), '']}
              labelFormatter={v => v === 0 ? 'Start' : `Month ${v}`} />
            <Area type="monotone" dataKey="withIntervention" name="With Intervention"
              stroke={totalNet > 0 ? '#43A047' : '#EF5350'}
              fill="url(#savingGrad)" strokeWidth={2.5} />
            <Area type="monotone" dataKey="baseline" name="No Intervention"
              stroke="#CBD5E0" fill="none" strokeDasharray="5 3" strokeWidth={1.5} />
          </AreaChart>
        </ResponsiveContainer>
        <div className="mt-3 text-[11px] text-gray-400 leading-relaxed">
          Savings assumed to accrue linearly over 12 months. Intervention cost is applied upfront.
          {breakEvenMonth && breakEvenMonth <= 12
            ? ` Break-even achieved at month ${breakEvenMonth}.`
            : ' Adjust parameters to reach positive ROI.'}
        </div>
      </div>
      )}
    </div>
  );
}
