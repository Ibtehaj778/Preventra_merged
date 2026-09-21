import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, Cell,
} from 'recharts';
import { ChartTooltip } from '../shared';
import { SEGMENT_SHORT } from '../../data/mockData';

const DRIVER_COLORS = {
  ESRD:             '#C62828',
  CV_event:         '#EF6C00',
  Uncontrolled_T2D: '#1E88E5',
};

const DRIVER_LABEL = {
  ESRD:             'ESRD / Dialysis',
  CV_event:         'CV Event',
  Uncontrolled_T2D: 'Uncontrolled T2D',
};

const fmtMoney = (n) => {
  if (!Number.isFinite(n)) return '—';
  if (Math.abs(n) >= 1e6) return `$${(n / 1e6).toFixed(2)}M`;
  if (Math.abs(n) >= 1e3) return `$${(n / 1e3).toFixed(1)}K`;
  return `$${Math.round(n)}`;
};

/**
 * Stacked bar: one bar per cluster, stacked by cost driver.
 *
 * Props:
 *   data: [{cluster_id, cluster_label, cost_by_driver_5yr: {ESRD, CV_event, Uncontrolled_T2D}}]
 *   height: chart height in px (default 300)
 */
export default function CostDriverStackedBar({ data, height = 300 }) {
  const chartData = (data ?? []).map(c => ({
    name:             SEGMENT_SHORT[c.cluster_id] ?? `Cluster ${c.cluster_id}`,
    ESRD:             c.cost_by_driver_5yr?.ESRD ?? 0,
    CV_event:         c.cost_by_driver_5yr?.CV_event ?? 0,
    Uncontrolled_T2D: c.cost_by_driver_5yr?.Uncontrolled_T2D ?? 0,
  }));

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 10, right: 20, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EDF2F7" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={fmtMoney} tick={{ fontSize: 11 }} />
        <Tooltip content={<ChartTooltip formatter={(v, name) => [fmtMoney(v), DRIVER_LABEL[name] ?? name]} />} />
        <Legend
          formatter={(v) => <span style={{ fontSize: 11, color: '#4A5568' }}>{DRIVER_LABEL[v] ?? v}</span>}
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ paddingTop: 8 }}
        />
        <Bar dataKey="Uncontrolled_T2D" stackId="a" fill={DRIVER_COLORS.Uncontrolled_T2D} />
        <Bar dataKey="CV_event"         stackId="a" fill={DRIVER_COLORS.CV_event} />
        <Bar dataKey="ESRD"             stackId="a" fill={DRIVER_COLORS.ESRD} />
      </BarChart>
    </ResponsiveContainer>
  );
}
