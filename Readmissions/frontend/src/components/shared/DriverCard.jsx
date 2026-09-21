import React from 'react';
import { Activity, Beaker, Pill, Stethoscope, AlertTriangle, FileText } from 'lucide-react';

export default function DriverCard({ label, value, explanation, riskBand, category }) {
  const normalizedBand = riskBand?.toLowerCase() || 'low';
  
  const borderColors = {
    high: 'border-l-risk-high',
    medium: 'border-l-risk-medium',
    low: 'border-l-risk-low'
  };
  
  const bgColors = {
    high: 'bg-red-50/30',
    medium: 'bg-yellow-50/30',
    low: 'bg-green-50/30'
  };

  const getIcon = (cat) => {
    switch (cat?.toLowerCase()) {
      case 'medication': return <Pill size={20} className="text-gray-500" />;
      case 'lab': return <Beaker size={20} className="text-gray-500" />;
      case 'history': return <FileText size={20} className="text-gray-500" />;
      case 'vitals': return <Activity size={20} className="text-gray-500" />;
      case 'diagnosis': return <Stethoscope size={20} className="text-gray-500" />;
      default: return <AlertTriangle size={20} className="text-gray-500" />;
    }
  };

  // Values arrive display-ready from the API and are shown as sent.
  //
  // This used to multiply any value containing a decimal point by 100 and add
  // a percent sign, on the assumption that a decimal meant a proportion. Every
  // decimal value in the data is a laboratory result, so a normal albumin of
  // 2.9 g/dL rendered as "290%" and a potassium of 4.1 mEq/L as "410%" - a
  // nonsense reading shown to clinicians. Genuine percentages (medication
  // adherence and the like) are formatted by the backend and already carry
  // their own "%", so nothing here needs converting.
  const formatValue = (val) => val;

  const borderClass = borderColors[normalizedBand] || borderColors.low;
  const bgClass = bgColors[normalizedBand] || bgColors.low;
  const displayValue = formatValue(value);

  return (
    <div className={`flex flex-col p-4 border rounded-r-lg shadow-sm ${borderClass} ${bgClass} border-t-gray-200 border-r-gray-200 border-b-gray-200 border-l-[4px]`}>
      <div className="flex items-start space-x-3">
        <div className="mt-1">
          {getIcon(category)}
        </div>
        <div>
          <div className="font-semibold text-gray-800">
            {label}: {displayValue}
          </div>
          <div className="text-sm text-gray-500 mt-1">
            {explanation}
          </div>
        </div>
      </div>
    </div>
  );
}
