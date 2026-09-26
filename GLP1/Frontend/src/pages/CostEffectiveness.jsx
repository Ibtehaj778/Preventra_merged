import { useState, useMemo } from 'react';
import {
  ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip,
  ReferenceLine, ResponsiveContainer, BarChart, Bar, Cell,
} from 'recharts';
import { Link } from 'react-router-dom';
import { Stethoscope } from 'lucide-react';
import { SectionHeader } from '../components/shared';
import { SEGMENT_COLORS, SEGMENT_SHORT, SEGMENT_LABELS } from '../data/mockData';
import { useCostEffectiveness } from '../hooks/useCostEffectiveness';
import { useSegments } from '../hooks/useSegments';
import { useRole } from '../context/RoleContext';

const ICER_THRESHOLD = 50000;

export default function CostEffectiveness() {
  const { isCostView }      = useRole();
  const { data: costData } = useCostEffectiveness();
  const { segments }       = useSegments();
  const ceaData  = costData.cea;
  const ADHERENCE = segments.map(s => s.adherence);
  const [metric, setMetric]           = useState('hba1c');  // 'hba1c' | 'weight'
  const [comparator, setComparator]   = useState('insulin'); // 'insulin' | 'sglt2'
  const [visibleSegs, setVisibleSegs] = useState([0, 1, 2, 3]);

  const toggleSeg = (i) =>
    setVisibleSegs(v => v.includes(i) ? v.filter(x => x !== i) : [...v, i]);

  const filteredCEA = useMemo(() =>
    ceaData.filter((_, i) => visibleSegs.includes(i)), [visibleSegs]);

  const scatterData = useMemo(() =>
    filteredCEA.map(s => ({
      x:       metric === 'hba1c' ? s.hba1c_reduction : s.weight_loss,
      y:       s.annual_cost,
      n:       s.n,
      label:   s.label,
      color:   SEGMENT_COLORS[s.cluster],
      cluster: s.cluster,
    })), [filteredCEA, metric]);

  const icerData = useMemo(() =>
    filteredCEA.map(s => {
      const icer = metric === 'hba1c'
        ? (comparator === 'insulin' ? s.icer_insulin_hba1c : s.icer_sglt2_hba1c)
        : (comparator === 'insulin' ? s.icer_insulin_weight : s.icer_sglt2_weight);
      return {
        name:    SEGMENT_SHORT[s.cluster].split(' ').slice(0, 2).join(' '),
        icer,
        color:   SEGMENT_COLORS[s.cluster],
        cluster: s.cluster,
      };
    }), [filteredCEA, metric, comparator]);

  // Rankings sorted by cost_per_hba1c (ascending = better)
  const ranked = useMemo(() =>
    [...ceaData].sort((a, b) => a.cost_per_hba1c - b.cost_per_hba1c),
  []);

  // Quadrant averages for reference lines (all data, not filtered)
  const avgOutcome = ceaData.reduce((a, s) => a + (metric === 'hba1c' ? s.hba1c_reduction : s.weight_loss), 0) / ceaData.length;
  const avgCost    = ceaData.reduce((a, s) => a + s.annual_cost, 0) / ceaData.length;

  return (
    <div className="max-w-[1280px] mx-auto animate-fade-in space-y-5">
      {!isCostView && (
        <div className="flex items-center justify-between gap-3 px-4 py-3 rounded-xl text-sm font-medium animate-fade-up"
          style={{ background: '#F0FFF4', color: '#2E7D32', border: '1px solid #C8E6C9' }}>
          <span className="flex items-center gap-2.5">
            <Stethoscope size={15} />
            Care team view — This financial analysis is mainly for hospital administrators and insurers. All data is available for reference.
          </span>
          <div className="flex items-center gap-3 text-xs font-semibold flex-shrink-0">
            <Link to="/patients" className="hover:underline underline-offset-2" style={{ color: '#2E7D32' }}>Patient Risk Panel →</Link>
            <Link to="/"         className="hover:underline underline-offset-2" style={{ color: '#2E7D32' }}>Executive Summary →</Link>
          </div>
        </div>
      )}

      <div className="flex flex-col lg:flex-row gap-5 items-stretch lg:items-start">

        {/* ── Controls sidebar (35%) ──────────────────────────── */}
        <aside className="w-full lg:w-[300px] flex-shrink-0 space-y-4">

          {/* Segment selector */}
          <div className="card p-5">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-3">
              Segments to Compare
            </div>
            <div className="space-y-2">
              {ceaData.map((s, i) => (
                <label key={i} className="flex items-center gap-3 cursor-pointer py-1">
                  <input type="checkbox" checked={visibleSegs.includes(i)}
                    onChange={() => toggleSeg(i)}
                    className="w-3.5 h-3.5 rounded"
                    style={{ accentColor: SEGMENT_COLORS[i] }} />
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0"
                        style={{ background: SEGMENT_COLORS[i] }} />
                  <span className="text-xs text-gray-700">{SEGMENT_SHORT[i]}</span>
                </label>
              ))}
            </div>
          </div>

          {/* Outcome metric toggle */}
          <div className="card p-5">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-3">
              Outcome Metric
            </div>
            <div className="flex rounded-lg overflow-hidden border border-gray-200">
              {[['hba1c', 'HbA1c Reduction'], ['weight', 'Weight Loss']].map(([k, label]) => (
                <button key={k} onClick={() => setMetric(k)}
                  className="flex-1 px-3 py-2 text-xs font-medium transition-colors"
                  style={{
                    background: metric === k ? 'var(--color-primary)' : 'white',
                    color:      metric === k ? 'white' : '#4A5568',
                  }}>
                  {label}
                </button>
              ))}
            </div>
          </div>

          {/* Comparator toggle */}
          <div className="card p-5">
            <div className="text-[10px] font-bold text-gray-400 uppercase tracking-wider mb-3">
              vs Comparator
            </div>
            <div className="flex flex-col gap-2">
              {[['insulin', 'Insulin Glargine'], ['sglt2', 'SGLT2 Inhibitor']].map(([k, label]) => (
                <button key={k} onClick={() => setComparator(k)}
                  className="px-3 py-2 text-xs font-medium transition-colors rounded-lg border text-left"
                  style={{
                    borderColor: comparator === k ? 'var(--color-primary)' : '#E2E8F0',
                    background:  comparator === k ? '#EBF4FF' : 'white',
                    color:       comparator === k ? 'var(--color-primary)' : '#4A5568',
                  }}>
                  {label}
                </button>
              ))}
            </div>
            <p className="text-[10px] text-gray-400 mt-3 leading-relaxed">
              Benchmarks: STEP 1–4 (Semaglutide), SURMOUNT-1 (Tirzepatide), SCALE (Liraglutide).
              ICER threshold: $50,000.
            </p>
          </div>
        </aside>

        {/* ── Charts column (65%) ─────────────────────────────── */}
        <div className="flex-1 min-w-0 space-y-5">

          {/* Scatter: cost vs outcome */}
          <div className="card p-5">
            <SectionHeader
              title="Cost vs Clinical Outcome"
              sub="Bubble size = population size · Bottom-right = best value" />
            <ResponsiveContainer width="100%" height={300}>
              <ScatterChart margin={{ top: 24, right: 24, bottom: 28, left: 8 }}>
                <CartesianGrid stroke="#EDF2F7" />
                <XAxis dataKey="x"
                  label={{ value: metric === 'hba1c' ? 'HbA1c Reduction (pts)' : 'Weight Loss (%)', position: 'insideBottom', offset: -14, fontSize: 11 }}
                  tick={{ fontSize: 11 }} name={metric === 'hba1c' ? 'HbA1c Reduction' : 'Weight Loss'} />
                <YAxis dataKey="y" tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }}
                  label={{ value: 'Annual Drug Cost ($)', angle: -90, position: 'insideLeft', offset: 16, fontSize: 11 }}
                  name="Annual Drug Cost" />
                <Tooltip content={({ active, payload }) => {
                  if (!active || !payload?.[0]) return null;
                  const d = payload[0].payload;
                  return (
                    <div className="card px-3 py-2 text-xs shadow-md">
                      <b style={{ color: d.color }}>{d.label}</b><br />
                      {metric === 'hba1c' ? `HbA1c Δ: −${d.x} pts` : `Weight loss: ${d.x}%`}<br />
                      Annual cost: ${d.y.toLocaleString()}<br />
                      n = {d.n.toLocaleString()}
                    </div>
                  );
                }} />
                <ReferenceLine x={avgOutcome} stroke="#CBD5E0" strokeDasharray="4 2"
                  label={{ value: 'Avg outcome', fontSize: 9, fill: '#A0AEC0', position: 'insideTopLeft' }} />
                <ReferenceLine y={avgCost} stroke="#CBD5E0" strokeDasharray="4 2"
                  label={{ value: 'Avg cost', fontSize: 9, fill: '#A0AEC0', position: 'insideTopRight' }} />
                <Scatter data={scatterData} shape={(props) => {
                  const { cx, cy, payload } = props;
                  const r = Math.sqrt(payload.n / 2383) * 28;
                  return (
                    <g>
                      <circle cx={cx} cy={cy} r={r} fill={payload.color} fillOpacity={0.2}
                              stroke={payload.color} strokeWidth={2} />
                      <text x={cx} y={cy - r - 5} textAnchor="middle" fontSize={9}
                            fill={payload.color} fontWeight={600}>
                        {SEGMENT_SHORT[payload.cluster].split(' ')[0]}
                      </text>
                    </g>
                  );
                }} />
              </ScatterChart>
            </ResponsiveContainer>
          </div>

          {/* ICER bar chart */}
          <div className="card p-5">
            <SectionHeader
              title={`ICER vs ${comparator === 'insulin' ? 'Insulin Glargine' : 'SGLT2 Inhibitor'}`}
              sub={`Incremental cost per ${metric === 'hba1c' ? 'HbA1c point reduced' : '% body weight lost'} · $50k threshold`} />
            <ResponsiveContainer width="100%" height={230}>
              <BarChart data={icerData} margin={{ top: 16, right: 16, bottom: 0, left: 0 }}>
                <CartesianGrid vertical={false} stroke="#EDF2F7" />
                <XAxis dataKey="name" tick={{ fontSize: 11 }} />
                <YAxis tickFormatter={v => `$${(v / 1000).toFixed(0)}k`} tick={{ fontSize: 11 }} />
                <ReferenceLine y={ICER_THRESHOLD} stroke="#EF5350" strokeDasharray="5 3"
                  label={{ value: '$50k threshold', position: 'right', fontSize: 9, fill: '#EF5350' }} />
                <Tooltip formatter={v => [`$${v.toLocaleString()}`, 'ICER']} />
                <Bar dataKey="icer" radius={[4, 4, 0, 0]} name="ICER">
                  {icerData.map((d, i) => (
                    <Cell key={i}
                      fill={d.icer > ICER_THRESHOLD ? d.color : '#43A047'}
                      opacity={d.icer > ICER_THRESHOLD ? 1 : 0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
            <div className="mt-3 flex items-center gap-4 text-[11px] text-gray-500">
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded bg-green-600 inline-block" />
                Below $50k — cost-effective
              </span>
              <span className="flex items-center gap-1.5">
                <span className="w-3 h-3 rounded inline-block" style={{ background: '#E0E0E0' }} />
                Above $50k — review value
              </span>
            </div>
          </div>

          {/* Cost-efficiency ranking table */}
          <div className="card overflow-hidden">
            <div className="p-5 border-b border-gray-100">
              <SectionHeader
                title="Cost-Efficiency Ranking"
                sub="All segments ranked by cost per HbA1c point reduced (ascending)" />
            </div>
            <div className="overflow-x-auto">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Rank</th>
                    <th>Segment</th>
                    <th>Adherence</th>
                    <th>Annual Cost</th>
                    <th>Cost / HbA1c Pt</th>
                    <th>Cost / Weight%</th>
                    <th>ICER vs Insulin</th>
                    <th>ICER vs SGLT2</th>
                  </tr>
                </thead>
                <tbody>
                  {ranked.map((s, rank) => {
                    const clr = SEGMENT_COLORS[s.cluster];
                    const adh = ADHERENCE[s.cluster];
                    return (
                      <tr key={s.cluster}>
                        <td>
                          <span className="font-bold text-sm" style={{ color: clr }}>#{rank + 1}</span>
                        </td>
                        <td>
                          <div className="flex items-center gap-2">
                            <span className="w-2.5 h-2.5 rounded-full" style={{ background: clr }} />
                            <span className="text-xs">{s.label}</span>
                          </div>
                        </td>
                        <td>
                          <span className="text-xs font-semibold"
                                style={{ color: adh >= 0.5 ? '#2E7D32' : '#C62828' }}>
                            {(adh * 100).toFixed(1)}%
                          </span>
                        </td>
                        <td className="font-mono text-xs">${s.annual_cost.toLocaleString()}</td>
                        <td>
                          <span className="font-mono text-xs font-semibold"
                                style={{ color: rank === 0 ? '#2E7D32' : rank === ranked.length - 1 ? '#C62828' : 'inherit' }}>
                            ${s.cost_per_hba1c.toLocaleString()}
                          </span>
                        </td>
                        <td className="font-mono text-xs">${s.cost_per_weight.toLocaleString()}</td>
                        <td className="font-mono text-xs">${s.icer_insulin_hba1c.toLocaleString()}</td>
                        <td className="font-mono text-xs">${s.icer_sglt2_hba1c.toLocaleString()}</td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
