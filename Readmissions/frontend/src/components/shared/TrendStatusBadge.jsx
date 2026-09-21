import React from 'react';
import { TrendingUp, TrendingDown, Minus, AlertTriangle, HelpCircle } from 'lucide-react';

const STATUS_CONFIG = {
  action_required: {
    label: 'Action Required',
    shortLabel: 'Action',
    icon: AlertTriangle,
    bg: 'bg-risk-high',
    text: 'text-risk-high',
    soft: 'bg-red-50 border-red-200',
  },
  deteriorating: {
    label: 'Deterioration',
    shortLabel: 'Worsening',
    icon: TrendingUp,
    bg: 'bg-risk-medium',
    text: 'text-risk-medium',
    soft: 'bg-yellow-50 border-yellow-200',
  },
  improving: {
    label: 'Improving',
    shortLabel: 'Improving',
    icon: TrendingDown,
    bg: 'bg-trend-improving',
    text: 'text-trend-improving',
    soft: 'bg-blue-50 border-blue-200',
  },
  stable: {
    label: 'Stable',
    shortLabel: 'Stable',
    icon: Minus,
    bg: 'bg-risk-low',
    text: 'text-risk-low',
    soft: 'bg-green-50 border-green-200',
  },
  insufficient_data: {
    label: 'Insufficient Data',
    // On the worklist a patient with only one scored admission is simply new to
    // monitoring, which reads better than "insufficient data" in a dense table.
    shortLabel: 'Not yet tracked',
    icon: HelpCircle,
    bg: 'bg-gray-400',
    text: 'text-gray-500',
    soft: 'bg-gray-50 border-gray-200',
  },
};

export function trendStatusConfig(status) {
  return STATUS_CONFIG[status] || STATUS_CONFIG.insufficient_data;
}

export default function TrendStatusBadge({ status, size = 'md', short = false }) {
  const cfg = trendStatusConfig(status);
  const Icon = cfg.icon;
  const sizes = {
    sm: 'px-2 py-0.5 text-xs gap-1',
    md: 'px-3 py-1 text-sm gap-1.5',
  };

  return (
    <span className={`inline-flex items-center font-medium text-white rounded-full whitespace-nowrap ${cfg.bg} ${sizes[size] || sizes.md}`}>
      <Icon size={size === 'sm' ? 12 : 14} />
      {short ? cfg.shortLabel : cfg.label}
    </span>
  );
}
