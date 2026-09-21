import { TrendingUp, TrendingDown, Minus, AlertTriangle, CheckCircle } from 'lucide-react';
import { SEGMENT_COLORS, SEGMENT_SHORT } from '../../data/mockData';

// ── KPI Card ─────────────────────────────────────────────────────────────────
export function KPICard({ label, value, sub, trend, trendLabel, color, icon: Icon, delay = 0 }) {
  const trendColor = trend > 0 ? '#2E7D32' : trend < 0 ? '#C62828' : '#718096';
  const TrendIcon = trend > 0 ? TrendingUp : trend < 0 ? TrendingDown : Minus;
  return (
    <div className="card card-hover p-5 animate-fade-up flex flex-col gap-3" style={{ animationDelay: `${delay}s` }}>
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">{label}</span>
        {Icon && (
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
               style={{ background: color ? `${color}18` : '#EBF4FF' }}>
            <Icon size={15} style={{ color: color ?? 'var(--color-primary)' }} />
          </div>
        )}
      </div>
      <div>
        <div className="font-display text-2xl font-semibold text-gray-800 leading-none">{value}</div>
        {sub && <div className="text-xs text-gray-400 mt-1">{sub}</div>}
      </div>
      {trendLabel && (
        <div className="flex items-center gap-1 text-xs font-medium" style={{ color: trendColor }}>
          <TrendIcon size={12} />
          {trendLabel}
        </div>
      )}
    </div>
  );
}

// ── Risk Badge ────────────────────────────────────────────────────────────────
export function RiskBadge({ prob }) {
  const pct = Math.round(prob * 100);
  const cls = pct >= 75 ? 'risk-critical' : pct >= 50 ? 'risk-high' : pct >= 25 ? 'risk-medium' : 'risk-low';
  return (
    <span className={`inline-flex items-center px-2 py-0.5 rounded-full text-xs font-mono font-semibold ${cls}`}>
      {pct}%
    </span>
  );
}

// ── Prediction Pill ───────────────────────────────────────────────────────────
export function PredictionPill({ prediction }) {
  const isDropout = prediction === 'Dropout Risk';
  return (
    <span className="inline-flex items-center gap-1 px-2.5 py-1 rounded-full text-xs font-semibold"
          style={{ background: isDropout ? '#FFEBEE' : '#E8F5E9', color: isDropout ? '#C62828' : '#2E7D32' }}>
      {isDropout ? <AlertTriangle size={10} /> : <CheckCircle size={10} />}
      {prediction}
    </span>
  );
}

// ── Segment Dot ───────────────────────────────────────────────────────────────
export function SegmentDot({ cluster, label, size = 'md' }) {
  const color = SEGMENT_COLORS[cluster];
  const sz = size === 'sm' ? 8 : 10;
  return (
    <span className="inline-flex items-center gap-1.5">
      <span className="inline-block rounded-full flex-shrink-0" style={{ width: sz, height: sz, background: color }} />
      <span className={size === 'sm' ? 'text-xs' : 'text-sm'} style={{ color: 'var(--text-primary)' }}>
        {label ?? SEGMENT_SHORT[cluster]}
      </span>
    </span>
  );
}

// ── SHAP Driver Card ──────────────────────────────────────────────────────────
export function SHAPDriverCard({ rank, driver, direction, shap, delay = 0 }) {
  const isRisk = direction?.includes('increases');
  const color = isRisk ? 'var(--risk-high)' : 'var(--color-positive)';
  const barWidth = Math.min(100, Math.abs(shap ?? 0) * 300);
  return (
    <div className="flex flex-col gap-1.5 p-3 rounded-lg animate-fade-up"
         style={{ background: '#F7FAFC', animationDelay: `${delay}s` }}>
      <div className="flex items-start justify-between gap-2">
        <div className="flex items-start gap-2">
          <span className="text-[10px] font-bold rounded-full w-5 h-5 flex items-center justify-center flex-shrink-0 mt-0.5"
                style={{ background: isRisk ? '#FFEBEE' : '#E8F5E9', color }}>
            {rank}
          </span>
          <span className="text-xs font-medium text-gray-700 leading-snug">{driver}</span>
        </div>
        <span className="text-[10px] font-semibold whitespace-nowrap px-2 py-0.5 rounded-full flex-shrink-0"
              style={{ background: isRisk ? '#FFEBEE' : '#E8F5E9', color }}>
          {isRisk ? '↑ risk' : '↓ risk'}
        </span>
      </div>
      <div className="h-1.5 rounded-full overflow-hidden" style={{ background: '#E2E8F0' }}>
        <div className="h-full rounded-full transition-all duration-500" style={{ width: `${barWidth}%`, background: color }} />
      </div>
    </div>
  );
}

// ── Section Header ────────────────────────────────────────────────────────────
export function SectionHeader({ title, sub, action }) {
  return (
    <div className="flex items-start justify-between gap-3 flex-wrap mb-4">
      <div>
        <h2 className="font-display text-base font-semibold text-gray-800">{title}</h2>
        {sub && <p className="text-xs text-gray-400 mt-0.5">{sub}</p>}
      </div>
      {action}
    </div>
  );
}

// ── Tooltip (chart) ───────────────────────────────────────────────────────────
export function ChartTooltip({ active, payload, label, formatter }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="card px-3 py-2 text-xs shadow-lg" style={{ minWidth: 140 }}>
      {label && <div className="font-semibold text-gray-600 mb-1.5">{label}</div>}
      {payload.map((p, i) => (
        <div key={i} className="flex items-center justify-between gap-4">
          <span className="flex items-center gap-1.5">
            <span className="w-2 h-2 rounded-full flex-shrink-0" style={{ background: p.color }} />
            <span className="text-gray-500">{p.name}</span>
          </span>
          <span className="font-semibold font-mono text-gray-800">
            {formatter ? formatter(p.value, p.name) : p.value}
          </span>
        </div>
      ))}
    </div>
  );
}

// ── Empty State ───────────────────────────────────────────────────────────────
export function EmptyState({ message = 'No data available' }) {
  return (
    <div className="flex items-center justify-center h-40 text-sm text-gray-400">{message}</div>
  );
}

// ── Stat Badge ────────────────────────────────────────────────────────────────
export function StatBadge({ value, color = 'blue' }) {
  const colors = {
    blue: { bg: '#EBF4FF', text: '#1B4F8A' },
    green: { bg: '#E8F5E9', text: '#2E7D32' },
    red: { bg: '#FFEBEE', text: '#C62828' },
    orange: { bg: '#FFF3E0', text: '#EF6C00' },
    gray: { bg: '#F7FAFC', text: '#718096' },
  };
  const c = colors[color] || colors.blue;
  return (
    <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-semibold"
          style={{ background: c.bg, color: c.text }}>
      {value}
    </span>
  );
}

// ── Progress Bar ──────────────────────────────────────────────────────────────
export function ProgressBar({ value, max = 1, color = 'var(--color-primary)', height = 6 }) {
  const pct = Math.min(100, (value / max) * 100);
  return (
    <div className="rounded-full overflow-hidden" style={{ height, background: 'var(--border)' }}>
      <div className="h-full rounded-full transition-all duration-700" style={{ width: `${pct}%`, background: color }} />
    </div>
  );
}

// ── Checkpoint Table ──────────────────────────────────────────────────────────
export function CheckpointTable({ data }) {
  const getColor = (v) => {
    const pct = v * 100;
    if (pct >= 60) return { bg: '#FFEBEE', color: '#C62828' };
    if (pct >= 35) return { bg: '#FFF3E0', color: '#EF6C00' };
    if (pct >= 15) return { bg: '#FFFDE7', color: '#92400E' };
    return { bg: '#E8F5E9', color: '#2E7D32' };
  };
  return (
    <table className="data-table">
      <thead>
        <tr>
          <th>Segment</th>
          <th>By Day 30</th>
          <th>By Day 60</th>
          <th>By Day 90</th>
          <th>By Day 180</th>
        </tr>
      </thead>
      <tbody>
        {data.map((row) => {
          const c = SEGMENT_COLORS[row.cluster];
          return (
            <tr key={row.cluster}>
              <td>
                <div className="flex items-center gap-2">
                  <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ background: c }} />
                  <span className="text-sm font-medium text-gray-700">{row.segment}</span>
                </div>
              </td>
              {[row.day30, row.day60, row.day90, row.day180].map((v, i) => {
                const { bg, color } = getColor(v);
                return (
                  <td key={i}>
                    <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold font-mono"
                          style={{ background: bg, color }}>
                      {(v * 100).toFixed(1)}%
                    </span>
                  </td>
                );
              })}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
