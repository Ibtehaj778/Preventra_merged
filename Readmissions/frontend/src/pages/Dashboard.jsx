import React, { useState } from 'react';
import SummaryPanel from '../components/dashboard/SummaryPanel';
import FilterBar from '../components/dashboard/FilterBar';
import PatientWorklist from '../components/dashboard/PatientWorklist';
import PatientDetailPanel from '../components/dashboard/PatientDetailPanel';

export default function Dashboard() {
  const [selectedPatientId, setSelectedPatientId] = useState(null);

  return (
    <div className="p-4 sm:p-6 max-w-7xl mx-auto relative">
      <SummaryPanel />
      <FilterBar />
      
      {/* Interactive Worklist */}
      <PatientWorklist onSelectPatient={setSelectedPatientId} />

      {/* Slide-in Detail Panel Overlay */}
      {selectedPatientId && (
        <PatientDetailPanel 
          patientId={selectedPatientId} 
          onClose={() => setSelectedPatientId(null)} 
        />
      )}
    </div>
  );
}
