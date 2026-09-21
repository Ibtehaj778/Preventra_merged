import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer, Cell,
} from 'recharts';
import { ChartTooltip } from '../shared';
import { SEGMENT_SHORT } from '../../data/mockData';

const HORIZON_COLORS = {
  1:  '#BFDBFE',   // very light blue = shortest horizon
  3:  '#60A5FA',
  5:  '#2563EB',
  10: '#1E3A8A',   // darkest = longest horizon
};

const fmtROI = (v) => (v == null || !Number.isFinite(v) ? '—' : v.toFixed(2));

/**
 * Grouped bar chart: 4 clusters × 4 horizons (1/3/5/10yr).
 *
 * Props:
 *   data:     PayerROIResponse.by_cluster
 *   roiField: which ROI variant to plot — "roi" (drug economics, default),
 *             "intervention_roi_medical", or "intervention_roi_net".
 */
export default function ROIBarChart({ data, height = 320, roiField = "roi" }) {
  const chartData = (data ?? []).map(c => {
    const byH = Object.fromEntries(
      (c.horizons ?? []).map(h => [`roi_${h.horizon_years}yr`, h[roiField]])
    );
    return {
      name: SEGMENT_SHORT[c.cluster_id] ?? `Cluster ${c.cluster_id}`,
      ...byH,
    };
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <BarChart data={chartData} margin={{ top: 12, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EDF2F7" />
        <XAxis dataKey="name" tick={{ fontSize: 11 }} />
        <YAxis tickFormatter={fmtROI} tick={{ fontSize: 11 }}
          label={{ value: 'ROI', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#718096' } }} />
        <Tooltip content={<ChartTooltip formatter={(v) => fmtROI(v)} />} />
        <Legend
          formatter={(k) => {
            const yr = String(k).match(/roi_(\d+)yr/)?.[1];
            return <span style={{ fontSize: 11, color: '#4A5568' }}>{yr}-year ROI</span>;
          }}
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ paddingTop: 6 }}
        />
        <ReferenceLine y={0} stroke="#2E7D32" strokeDasharray="5 3"
          label={{ value: 'Break-even (ROI = 0)', position: 'right', fontSize: 10, fill: '#2E7D32' }} />
        <Bar dataKey="roi_1yr"  fill={HORIZON_COLORS[1]}  radius={[3, 3, 0, 0]} />
        <Bar dataKey="roi_3yr"  fill={HORIZON_COLORS[3]}  radius={[3, 3, 0, 0]} />
        <Bar dataKey="roi_5yr"  fill={HORIZON_COLORS[5]}  radius={[3, 3, 0, 0]} />
        <Bar dataKey="roi_10yr" fill={HORIZON_COLORS[10]} radius={[3, 3, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
