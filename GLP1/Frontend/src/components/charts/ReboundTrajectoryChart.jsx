import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ReferenceLine, ResponsiveContainer,
} from 'recharts';
import { ChartTooltip } from '../shared';
import { SEGMENT_COLORS, SEGMENT_SHORT } from '../../data/mockData';

/**
 * Line chart: HbA1c trajectory over 0-12 months post-dropout.
 *
 * Props:
 *   trajectoryByCluster: [{cluster_id, scenarios: [{scenario, dropout_day, points: [{month, avg_hba1c}]}]}]
 *   scenario: 'early' | 'median' | 'late' — which scenario to render
 *   height: chart height
 *
 * Renders one line per cluster.
 */
export default function ReboundTrajectoryChart({ trajectoryByCluster, scenario = 'median', height = 320 }) {
  const months = [0, 3, 6, 9, 12];

  // Pivot: rows are months, cols are clusters (c0..c3).
  const data = months.map(m => {
    const row = { month: m };
    (trajectoryByCluster ?? []).forEach(c => {
      const s = c.scenarios?.find(x => x.scenario === scenario);
      const pt = s?.points?.find(p => p.month === m);
      row[`c${c.cluster_id}`] = pt?.avg_hba1c ?? null;
    });
    return row;
  });

  return (
    <ResponsiveContainer width="100%" height={height}>
      <LineChart data={data} margin={{ top: 10, right: 24, bottom: 8, left: 8 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#EDF2F7" />
        <XAxis dataKey="month" tickFormatter={(v) => `M${v}`} tick={{ fontSize: 11 }} />
        <YAxis domain={[4.5, 8]} tick={{ fontSize: 11 }} label={{ value: 'HbA1c (%)', angle: -90, position: 'insideLeft', style: { fontSize: 11, fill: '#718096' } }} />
        <Tooltip content={<ChartTooltip formatter={(v) => (v == null ? '—' : Number(v).toFixed(2))} />} />
        <Legend
          formatter={(k) => {
            const idx = parseInt(String(k).slice(1), 10);
            return <span style={{ fontSize: 11, color: '#4A5568' }}>{SEGMENT_SHORT[idx] ?? k}</span>;
          }}
          iconType="circle"
          iconSize={8}
          wrapperStyle={{ paddingTop: 6 }}
        />
        <ReferenceLine y={6.5} stroke="#EF6C00" strokeDasharray="4 3"
          label={{ value: 'T2D threshold (6.5)', position: 'right', fontSize: 10, fill: '#EF6C00' }} />
        <ReferenceLine y={8.0} stroke="#C62828" strokeDasharray="4 3"
          label={{ value: 'Uncontrolled (8.0)', position: 'right', fontSize: 10, fill: '#C62828' }} />
        {(trajectoryByCluster ?? []).map(c => (
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
