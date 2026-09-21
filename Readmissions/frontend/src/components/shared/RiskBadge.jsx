import React from 'react';

export default function RiskBadge({ riskBand, size = 'md' }) {
  const normalizedBand = riskBand?.toLowerCase() || 'low';
  
  const colors = {
    high: 'bg-risk-high',
    medium: 'bg-risk-medium',
    low: 'bg-risk-low'
  };

  const sizes = {
    sm: 'px-2 py-0.5 text-xs',
    md: 'px-3 py-1 text-sm'
  };

  const bgColor = colors[normalizedBand] || colors.low;
  const sizeClasses = sizes[size] || sizes.md;

  return (
    <span className={`inline-flex items-center justify-center font-medium text-white rounded-full ${bgColor} ${sizeClasses}`}>
      {riskBand}
    </span>
  );
}
