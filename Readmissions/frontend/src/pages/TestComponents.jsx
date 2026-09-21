import React from 'react';
import RiskBadge from '../components/shared/RiskBadge';
import DriverCard from '../components/shared/DriverCard';

export default function TestComponents() {
  const drivers = [
    { label: 'Prior Admissions', value: '4', explanation: 'Patient has had 4 admissions in the past 12 months.', riskBand: 'High', category: 'history' },
    { label: 'HbA1c Level', value: '8.5%', explanation: 'Elevated HbA1c indicative of poorly controlled diabetes.', riskBand: 'Medium', category: 'lab' },
    { label: 'Recent Weight', value: 'Stable', explanation: 'No significant BMI drop in last 6 months.', riskBand: 'Low', category: 'vitals' }
  ];

  return (
    <div className="p-4 sm:p-6 max-w-4xl mx-auto space-y-10">
      <h1 className="text-3xl font-bold text-ns-navy border-b pb-4">Shared Components Gallery</h1>
      
      <section>
        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
          <span>RiskBadge Component</span>
        </h2>
        
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm space-y-8">
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-3 uppercase tracking-wider">Medium Size (Default)</h3>
            <div className="flex gap-4">
              <RiskBadge riskBand="High" />
              <RiskBadge riskBand="Medium" />
              <RiskBadge riskBand="Low" />
            </div>
          </div>
          
          <div>
            <h3 className="text-sm font-medium text-gray-500 mb-3 uppercase tracking-wider">Small Size (sm)</h3>
            <div className="flex gap-4">
              <RiskBadge riskBand="High" size="sm" />
              <RiskBadge riskBand="Medium" size="sm" />
              <RiskBadge riskBand="Low" size="sm" />
            </div>
          </div>
        </div>
      </section>

      <section>
        <h2 className="text-xl font-semibold mb-6 flex items-center gap-2">
          <span>DriverCard Component</span>
        </h2>
        
        <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {drivers.map((driver, idx) => (
              <DriverCard 
                key={idx}
                label={driver.label}
                value={driver.value}
                explanation={driver.explanation}
                riskBand={driver.riskBand}
                category={driver.category}
              />
            ))}
          </div>
        </div>
      </section>
    </div>
  );
}
