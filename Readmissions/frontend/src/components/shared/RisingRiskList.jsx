import React from 'react';
import { AlertTriangle, TrendingUp } from 'lucide-react';

/**
 * One row per patient whose latest monitoring week got worse. Shared by the
 * bell and the "Needs attention" panel so the two always read the same way.
 */
export function RisingRiskRow({ item, onOpen, compact = false }) {
  const urgent = item.severity === 'urgent';
  const Icon = urgent ? AlertTriangle : TrendingUp;
  return (
    <button type="button" onClick={() => onOpen(item)}
      className={`w-full text-left px-4 py-3 hover:bg-gray-50 transition-colors ${item.seen ? 'opacity-70' : ''}`}>
      <div className="flex items-start gap-3">
        <span className={`mt-0.5 shrink-0 rounded-full p-1.5 ${urgent ? 'bg-red-50 text-risk-high' : 'bg-amber-50 text-risk-medium'}`}>
          <Icon size={14} />
        </span>
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-x-2">
            <span className="text-sm font-semibold text-ns-navy">{item.patient_id}</span>
            <span className={`rounded-full px-2 py-0.5 text-[10px] font-bold uppercase ${urgent ? 'bg-risk-high text-white' : 'bg-amber-100 text-amber-800'}`}>
              {urgent ? 'Urgent' : 'Rising'}
            </span>
            {!item.seen && <span className="h-2 w-2 rounded-full bg-ns-navy" title="Not opened yet" />}
          </div>
          <p className="text-sm text-gray-600 mt-0.5">
            {item.previous_score.toFixed(1)}% ({item.previous_band}) &rarr;{' '}
            <span className={`font-semibold ${urgent ? 'text-risk-high' : 'text-risk-medium'}`}>
              {item.risk_score.toFixed(1)}% ({item.risk_band})
            </span>
            <span className="text-xs text-gray-400"> · week {item.week_number}</span>
          </p>
          <p className="text-xs text-gray-500 mt-0.5">{item.reasons.join(' · ')}</p>
          {!compact && item.primary_diagnosis && (
            <p className="text-xs text-gray-400 mt-0.5 truncate">{item.primary_diagnosis}</p>
          )}
        </div>
      </div>
    </button>
  );
}
