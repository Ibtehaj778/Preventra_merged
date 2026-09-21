import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { ChartTooltip } from '../shared';
import { SEGMENT_COLORS, SEGMENT_SHORT } from '../../data/mockData';

const fmtROI = (v) => (v == null || !Number.isFinite(v) ? '—' : v.toFixed(2));

/**
 * ROI trajectory line chart — one line per cluster over years 1..10.
 *
 * Props:
 *   data:     PayerROIResponse.by_cluster — each cluster has a yearly_roi_series
 *   height:   chart height in px
 *   roiField: which ROI variant to plot — "roi" (drug economics, default),
 *             "intervention_roi_medical", or "intervention_roi_net".
 */
export default function ROITrajectoryChart({ data, height = 320, roiField = "roi" }) {
  const years = Array.from({ length: 10 }, (_, i) => i + 1);

  // Pivot: rows = years, cols = clusters (c0..c3)
  const chartData = years.map(y => {
    const row = { year: y };
    (data ?? []).forEach(c => {
      const pt = c.yearly_roi_series?.find(p => p.year === y);
      row[`c${c.cluster_id}`] = pt?.[roiField] ?? null;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={chartData} margin={{ top: 12, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EDF2F7" />
        <XAxis dataKey="year" tickFormatter={(v) => `Y${v}`} tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={fmtROI} tick={{ fontSize: 11 }}
          label={{ value: 'ROI', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#718096' } }} />
        <Tooltip content={<ChartTooltip formatter={(v) => fmtROI(v)} />} />
        <Legend
          formatter={(k) => {
            const idx = parseInt(String(k).slice(1), 10);
            return <span style={{ fontSize: 11, color: '#4A5568' }}>{SEGMENT_SHORT[idx] ?? k}</span>;
          }}
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ paddingTop: 6 }}
        />
        <ReferenceLine y={0} stroke="#2E7D32" strokeDasharray="5 3"
          label={{ value: 'Break-even (ROI = 0)', position: 'right', fontSize: 10, fill: '#2E7D32' }} />
        {(data ?? []).map(c => (
          <Line key={c.cluster_id}
            type="monotone"
            dataKey={`c${c.cluster_id}`}
            name={`c${c.cluster_id}`}
            stroke={SEGMENT_COLORS[c.cluster_id]}
            strokeWidth={2}
            dot={{ r: 3 }}
            activeDot={{ r: 5 }}
            connectNulls
          />
        ))}
      </LineChart>
    </ResponsiveContainer>
  );
}
