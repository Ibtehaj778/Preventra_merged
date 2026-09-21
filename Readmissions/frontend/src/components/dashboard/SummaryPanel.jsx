import React, { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { getSummary, getPatients } from '../../api';
import { ArrowUp, ArrowDown, Calendar, Users, Activity, AlertCircle, TrendingUp } from 'lucide-react';

// ---------------------------------------------------------------------------
// Skeleton placeholder (no spinners)
// ---------------------------------------------------------------------------
function SummarySkeleton() {
  return (
    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-6 animate-pulse">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <div className="h-6 bg-gray-200 rounded w-40" />
        <div className="h-6 bg-gray-100 rounded w-32" />
      </div>
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        {[...Array(4)].map((_, i) => (
          <div key={i} className="p-4 bg-gray-50 rounded-lg border border-gray-100 space-y-3">
            <div className="h-4 bg-gray-200 rounded w-3/4" />
            <div className="h-8 bg-gray-200 rounded w-1/2" />
          </div>
        ))}
      </div>
    </div>
  );
}

export default function SummaryPanel() {
  const [data, setData]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState(null);
  const [needsAttention, setNeedsAttention] = useState(null);
  const [, setSearchParams] = useSearchParams();

  useEffect(() => {
    setLoading(true);
    setError(null);
    getSummary()
      .then((res) => { setData(res); setLoading(false); })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, []);

  // Post-discharge trend counts aren't in executive_summary (which is written
  // per batch, before any re-scoring), so they're derived from the worklist.
  // Best-effort: a failure here leaves the tile hidden rather than breaking
  // the whole summary.
  useEffect(() => {
    getPatients()
      .then((rows) => {
        const count = (rows || []).filter(
          (p) => p.monitoring_status === 'action_required' || p.monitoring_status === 'deteriorating',
        ).length;
        setNeedsAttention(count);
      })
      .catch(() => setNeedsAttention(null));
  }, []);

  if (loading) return <SummarySkeleton />;

  if (error) {
    return (
      <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 flex items-start space-x-3 text-red-800">
        <AlertCircle size={20} className="mt-0.5 shrink-0" />
        <div>
          <div className="font-semibold">Failed to load summary</div>
          <div className="text-sm mt-0.5 text-red-600">{error}</div>
        </div>
      </div>
    );
  }

  if (!data) return <SummarySkeleton />;

  const isUp   = data.high_delta > 0;
  const isDown = data.high_delta < 0;

  return (
    <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm mb-6">
      <div className="flex justify-between items-center mb-6 border-b pb-4">
        <h2 className="text-xl font-semibold text-ns-navy flex items-center space-x-2">
          <Activity className="text-gray-400" />
          <span>Executive Summary</span>
        </h2>
        <div className="flex items-center space-x-2 text-sm text-gray-500 bg-gray-50 px-3 py-1.5 rounded-full border">
          <Calendar size={16} />
          <span>Batch Date: <strong>{data.batch_date}</strong></span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-6">
        {/* Needs Attention — post-discharge trend, click to filter the worklist */}
        {needsAttention !== null && (
          <button
            type="button"
            onClick={() => {
              const next = new URLSearchParams(window.location.search);
              next.set('trend', 'NeedsAttention');
              setSearchParams(next);
            }}
            className="flex flex-col space-y-2 p-4 bg-red-50/50 rounded-lg border border-red-100 text-left hover:border-risk-high hover:shadow-sm transition-all focus:outline-none focus:ring-2 focus:ring-risk-high/40"
          >
            <div className="flex items-center space-x-2 text-risk-high text-sm font-medium">
              <TrendingUp size={18} />
              <span>Needs Attention</span>
            </div>
            <div className="text-3xl font-bold text-gray-900">{needsAttention}</div>
            <div className="text-xs text-gray-500">rising since discharge</div>
          </button>
        )}

        {/* Total Patients */}
        <div className="flex flex-col space-y-2 p-4 bg-gray-50 rounded-lg border border-gray-100">
          <div className="flex items-center space-x-2 text-gray-500 text-sm font-medium">
            <Users size={18} />
            <span>Total Patients Scored</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{data.total_patients}</div>
        </div>

        {/* High Risk */}
        <div className="flex flex-col space-y-2 p-4 bg-red-50/50 rounded-lg border border-red-100">
          <div className="flex items-center space-x-2 text-risk-high text-sm font-medium">
            <div className="w-3 h-3 rounded-full bg-risk-high" />
            <span>High Risk</span>
          </div>
          <div className="flex items-end space-x-3">
            <div className="text-3xl font-bold text-gray-900">{data.high_count}</div>
            {(isUp || isDown) && (
              <div className={`flex items-center text-sm font-medium mb-1 ${isUp ? 'text-risk-high' : 'text-risk-low'}`}>
                {isUp ? <ArrowUp size={16} /> : <ArrowDown size={16} />}
                <span>{Math.abs(data.high_delta)} WoW</span>
              </div>
            )}
            {data.high_delta === 0 && (
              <div className="text-sm text-gray-400 font-medium mb-1"></div>
            )}
          </div>
        </div>

        {/* Medium Risk */}
        <div className="flex flex-col space-y-2 p-4 bg-yellow-50/40 rounded-lg border border-yellow-100">
          <div className="flex items-center space-x-2 text-risk-medium text-sm font-medium">
            <div className="w-3 h-3 rounded-full bg-risk-medium" />
            <span>Medium Risk</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{data.medium_count}</div>
        </div>

        {/* Low Risk */}
        <div className="flex flex-col space-y-2 p-4 bg-green-50/40 rounded-lg border border-green-100">
          <div className="flex items-center space-x-2 text-risk-low text-sm font-medium">
            <div className="w-3 h-3 rounded-full bg-risk-low" />
            <span>Low Risk</span>
          </div>
          <div className="text-3xl font-bold text-gray-900">{data.low_count}</div>
        </div>
      </div>
    </div>
  );
}
