import React, { useEffect, useState, useMemo } from 'react';
import { getSummary, getSummaryHistory, getModelMetrics, getTopDrivers } from '../api';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer, Cell,
  LineChart, Line
} from 'recharts';
import { Info, BarChart3, TrendingUp, Activity, ListOrdered, AlertCircle } from 'lucide-react';

// Skeleton blocks
function ChartSkeleton() {
  return (
    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-48 mb-6" />
      <div className="h-64 bg-gray-100 rounded" />
    </div>
  );
}
function MetricSkeleton() {
  return (
    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-48 mb-6" />
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="bg-gray-50 rounded-lg p-4 space-y-2">
            <div className="h-4 bg-gray-200 rounded w-24" />
            <div className="h-8 bg-gray-200 rounded w-16" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function Analytics() {
  const [summary, setSummary] = useState(null);
  const [history, setHistory] = useState([]);
  const [metrics, setMetrics] = useState(null);
  const [topDrivers, setTopDrivers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      getSummary(),
      getSummaryHistory(),
      getModelMetrics(),
      getTopDrivers()
    ])
      .then(([sumData, histData, metricData, driversData]) => {
        setSummary(sumData);
        setHistory(histData);
        setMetrics(metricData);
        setTopDrivers(driversData);
        setLoading(false);
      })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  // 1. Risk Distribution Chart Data
  const distributionData = useMemo(() => {
    if (!summary) return [];
    return [
      { name: 'Low',    count: parseInt(summary.low_count,    10) || 0, fill: '#1E7D44' },
      { name: 'Medium', count: parseInt(summary.medium_count, 10) || 0, fill: '#F0A500' },
      { name: 'High',   count: parseInt(summary.high_count,   10) || 0, fill: '#C0392B' },
    ];
  }, [summary]);

  // 2. Trend line colour determination
  const trendColor = useMemo(() => {
    if (history.length < 2) return '#1E7D44'; // Default green
    const first = history[0].high_count;
    const last = history[history.length - 1].high_count;
    return last > first ? '#C0392B' : '#1E7D44'; // Red if increasing, green if flat/decreasing
  }, [history]);


  if (loading) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-8">
        <div className="border-b border-gray-200 pb-4 animate-pulse">
          <div className="h-7 bg-gray-200 rounded w-56 mb-2" />
          <div className="h-4 bg-gray-100 rounded w-80" />
        </div>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          <ChartSkeleton /><ChartSkeleton /><MetricSkeleton /><ChartSkeleton />
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 sm:p-6 max-w-7xl mx-auto">
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3 text-red-800">
          <AlertCircle size={20} className="mt-0.5 shrink-0" />
          <div>
            <div className="font-semibold">Failed to load analytics</div>
            <div className="text-sm mt-0.5 text-red-600">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      <div className="border-b border-gray-200 pb-4">
        <h1 className="text-2xl font-bold text-ns-navy">Analytics & Performance</h1>
        <p className="text-gray-500 mt-1">Review model metrics and population-level risk distributions.</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
        
        {/* Risk Distribution Chart */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <h2 className="text-lg font-semibold text-ns-navy mb-6 flex items-center space-x-2">
            <BarChart3 className="text-gray-400" />
            <span>Risk Distribution (Current Batch)</span>
          </h2>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={distributionData} layout="vertical" margin={{ top: 5, right: 30, left: 20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" horizontal={true} vertical={false} stroke="#f0f0f0" />
                <XAxis type="number" tickLine={false} axisLine={false} tick={{fill: '#9ca3af'}} />
                <YAxis dataKey="name" type="category" tickLine={false} axisLine={false} tick={{fill: '#4b5563', fontWeight: 500}} />
                <RechartsTooltip 
                  cursor={{fill: '#f9fafb'}}
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Bar dataKey="count" radius={[0, 4, 4, 0]} barSize={32}>
                  {distributionData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={entry.fill} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Week-over-week Trend */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <h2 className="text-lg font-semibold text-ns-navy mb-6 flex items-center space-x-2">
            <TrendingUp className="text-gray-400" />
            <span>High-Risk Population Trend</span>
          </h2>
          <div className="h-64 w-full">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={history} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                <XAxis 
                  dataKey="week_label" 
                  tick={{fill: '#9ca3af', fontSize: 13}}
                  axisLine={false}
                  tickLine={false}
                />
                <YAxis 
                  domain={['dataMin - 10', 'dataMax + 10']}
                  tick={{fill: '#9ca3af', fontSize: 13}}
                  axisLine={false}
                  tickLine={false}
                />
                <RechartsTooltip 
                  contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                />
                <Line 
                  type="monotone" 
                  dataKey="high_count" 
                  name="High Risk Count"
                  stroke={trendColor} 
                  strokeWidth={3}
                  dot={{ fill: trendColor, strokeWidth: 2, r: 4 }}
                  activeDot={{ r: 6, fill: trendColor, strokeWidth: 0 }}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </div>

        {/* Model Performance Card */}
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm flex flex-col">
          <h2 className="text-lg font-semibold text-ns-navy mb-6 flex items-center justify-between">
            <div className="flex items-center space-x-2">
              <Activity className="text-gray-400" />
              <span>Model Performance Benchmarks</span>
            </div>
            {/* Read from the served model's own card rather than hardcoded,
                so a retrain cannot leave this describing a different model. */}
            <span className="text-xs px-2 py-1 bg-gray-100 text-gray-500 rounded font-medium border border-gray-200">
              {metrics.architecture || 'Gradient boosting'}
            </span>
          </h2>
          
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 flex-1">
            {/* AUC-ROC with Tooltip */}
            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 flex flex-col justify-center">
              <div className="flex items-center space-x-1.5 mb-1.5 relative group cursor-help">
                <span className="text-sm font-medium text-gray-500 border-b border-dotted border-gray-400">AUC-ROC</span>
                <Info size={14} className="text-gray-400" />
                
                {/* Tooltip Popup */}
                <div className="absolute bottom-full mb-2 w-60 p-3 bg-gray-800 text-white text-xs rounded-lg shadow-xl opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none -left-2 z-10">
                  <div className="font-semibold mb-1">Area Under the Curve</div>
                  Measures the model's ability to distinguish between patients who will readmit and those who won't. 1.0 is perfect, 0.5 is a coin toss.
                  <svg className="absolute text-gray-800 h-2 w-full left-0 top-full" x="0px" y="0px" viewBox="0 0 255 255" xmlSpace="preserve"><polygon className="fill-current" points="0,0 127.5,127.5 255,0"/></svg>
                </div>
              </div>
              <div className="text-3xl font-bold text-gray-900">{metrics.auc_roc.toFixed(3)}</div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 flex flex-col justify-center">
              <span className="text-sm font-medium text-gray-500 mb-1.5">Precision</span>
              <div className="text-3xl font-bold text-gray-900">{metrics.precision.toFixed(3)}</div>
              {metrics.prevalence && (
                <span className="text-[11px] text-gray-400 mt-1 leading-snug">
                  against a {(metrics.prevalence * 100).toFixed(1)}% base rate
                </span>
              )}
            </div>

            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 flex flex-col justify-center">
              <span className="text-sm font-medium text-gray-500 mb-1.5">Recall (Sensitivity)</span>
              <div className="text-3xl font-bold text-gray-900">{metrics.recall.toFixed(3)}</div>
            </div>

            <div className="bg-gray-50 rounded-lg p-4 border border-gray-100 flex flex-col justify-center">
              <span className="text-sm font-medium text-gray-500 mb-1.5">Operation Threshold</span>
              <div className="text-3xl font-bold text-gray-900 text-ns-navy">{metrics.threshold.toFixed(2)}</div>
            </div>
          </div>
        </div>

        {/* Top Drivers Table */}
        <div className="bg-white p-0 rounded-xl border border-gray-200 shadow-sm flex flex-col overflow-hidden">
          <div className="p-6 border-b border-gray-100">
            <h2 className="text-lg font-semibold text-ns-navy flex items-center space-x-2">
              <ListOrdered className="text-gray-400" />
              <span>Top Drivers (High-Risk Cohort)</span>
            </h2>
          </div>
          <div className="overflow-x-auto flex-1">
            <table className="w-full text-left text-sm whitespace-nowrap">
              <thead className="bg-gray-50 border-b border-gray-200 text-gray-500 font-medium">
                <tr>
                  <th className="px-6 py-3">Driver Name</th>
                  <th className="px-6 py-3 text-right">Patient Count</th>
                  <th className="px-6 py-3 text-right">% of Cohort</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {topDrivers.map((driver, idx) => (
                  <tr key={idx} className="hover:bg-gray-50 transition-colors">
                    <td className="px-6 py-3.5 font-medium text-gray-800">{driver.name}</td>
                    <td className="px-6 py-3.5 text-right font-medium text-gray-900">{driver.count}</td>
                    <td className="px-6 py-3.5 text-right text-gray-500">{driver.percent}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
        
      </div>
    </div>
  );
}
