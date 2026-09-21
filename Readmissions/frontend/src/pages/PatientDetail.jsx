import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { getPatientById, getSummaryHistory } from '../api';
import RiskBadge from '../components/shared/RiskBadge';
import DriverCard from '../components/shared/DriverCard';
import AiInsightsPanel from '../components/shared/AiInsightsPanel';
import CareCoordination from '../components/dashboard/CareCoordination';
import ForecastPanel from '../components/dashboard/ForecastPanel';
import { ArrowLeft, Calendar, AlertCircle, ListChecks, TrendingUp, CalendarClock, ChevronRight } from 'lucide-react';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

function PageSkeleton() {
  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-8 animate-pulse">
      <div className="h-5 bg-gray-200 rounded w-28" />
      <div className="bg-white p-8 rounded-2xl border border-gray-200 flex justify-between gap-6">
        <div className="space-y-3">
          <div className="h-8 bg-gray-200 rounded w-40" />
          <div className="h-4 bg-gray-100 rounded w-32" />
        </div>
        <div className="bg-gray-50 px-8 py-4 rounded-xl border border-gray-100 flex space-x-8">
          <div className="space-y-2"><div className="h-4 bg-gray-200 rounded w-24" /><div className="h-14 bg-gray-200 rounded w-16" /></div>
          <div className="space-y-2"><div className="h-4 bg-gray-200 rounded w-20" /><div className="h-8 bg-gray-200 rounded w-20" /></div>
        </div>
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        <div className="space-y-4">
          {[0,1,2].map(i => <div key={i} className="bg-white rounded-xl border border-gray-200 p-4 h-24 bg-gray-100" />)}
        </div>
        <div className="lg:col-span-2 space-y-8">
          <div className="bg-white rounded-xl border border-gray-200 p-6 h-80 bg-gray-50" />
          <div className="bg-white rounded-xl border border-gray-200 p-6 h-40 bg-gray-50" />
        </div>
      </div>
    </div>
  );
}

export default function PatientDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [patient, setPatient] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    getPatientById(id)
      .then((patientData) => {
        setPatient(patientData);
        let patientHistory = patientData.history || [];
        if (patientHistory.length === 1) {
          patientHistory = [
            { week: "Previous", score: patientHistory[0].score },
            patientHistory[0]
          ];
        }
        setHistory(patientHistory);
        setLoading(false);
      })
      .catch((err) => { setError(err.message); setLoading(false); });
  }, [id]);

  const getScoreColor = (band) => {
    const normalized = band?.toLowerCase();
    if (normalized === 'high') return 'text-risk-high';
    if (normalized === 'medium') return 'text-risk-medium';
    return 'text-risk-low';
  };
  
  const getSuggestedActions = (band) => {
    const normalized = band?.toLowerCase();
    if (normalized === 'high') return [
      "Schedule follow-up call within 48 hours.",
      "Review medication adherence.",
      "Arrange immediate post-discharge clinical evaluation."
    ];
    if (normalized === 'medium') return [
      "Ensure outbound contact within 7 days.",
      "Verify HbA1c labs have been scheduled for next month.",
    ];
    return [
      "Maintain standard care routine.",
      "Follow up during next scheduled annual visit."
    ];
  };

  if (loading) return <PageSkeleton />;

  if (error) {
    return (
      <div className="p-4 sm:p-6 max-w-5xl mx-auto">
        <button onClick={() => navigate('/')} className="flex items-center space-x-2 text-gray-500 hover:text-ns-navy mb-6 font-medium">
          <ArrowLeft size={18} /><span>Back to Worklist</span>
        </button>
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3 text-red-800">
          <AlertCircle size={20} className="mt-0.5 shrink-0" />
          <div>
            <div className="font-semibold">Please Select a valid patient from the dashbaoard</div>
            <div className="text-sm mt-0.5 text-red-600">{error}</div>
          </div>
        </div>
      </div>
    );
  }

  // Fall back to the discharge figures for a patient with no weekly series,
  // so a record that predates monitoring still renders a number rather than a
  // blank where the headline should be.
  const currentScore = patient.current_score ?? patient.risk_score;
  const currentBand = patient.current_band || patient.risk_band;
  const hasMonitoring =
    patient.current_score != null && patient.current_score !== patient.risk_score;
  const actions = getSuggestedActions(currentBand);

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-8 animate-in fade-in duration-500">
      
      {/* Back Button */}
      <button 
        onClick={() => navigate('/')}
        className="flex items-center space-x-2 text-gray-500 hover:text-ns-navy transition-colors font-medium mb-2 focus:outline-none"
      >
        <ArrowLeft size={18} />
        <span>Back to Worklist</span>
      </button>

      {/* Header Profile */}
      <div className="bg-white p-8 rounded-2xl border border-gray-200 shadow-sm flex flex-col md:flex-row items-center md:items-start justify-between gap-6">
        <div className="flex flex-col items-center md:items-start space-y-2">
          <h1 className="text-3xl font-bold text-gray-900">{patient.id}</h1>
          <div className="flex items-center space-x-2 text-gray-500">
            <Calendar size={18} />
            <span>Discharged: <strong>{patient.discharge_date}</strong></span>
          </div>
          <button
            onClick={() => navigate(`/patients/${patient.id}/trend`)}
            className="flex items-center space-x-1.5 text-sm font-semibold text-ns-navy hover:underline mt-1"
          >
            <CalendarClock size={16} />
            <span>Readmission Risk Trend</span>
            <ChevronRight size={14} />
          </button>
        </div>

        <div className="flex flex-col md:flex-row items-center space-y-4 md:space-y-0 md:space-x-8 bg-gray-50 px-8 py-4 rounded-xl border border-gray-100">
          {/* The headline is where the patient is NOW, after weekly monitoring —
              the same number the worklist ranks on and the forecast projects
              from. The discharge score sits beneath it as context, because a
              patient who left at 16% and is now at 39% is the case this whole
              programme exists to catch, and showing only the 16% hid it. */}
          <div className="flex flex-col items-center md:items-end">
            <span className="text-sm font-medium text-gray-500 mb-1">Current Risk Score</span>
            <span className={`text-6xl font-black ${getScoreColor(currentBand)} leading-none`}>
              {parseFloat(currentScore).toFixed(1)}%
            </span>
            {hasMonitoring && (
              <span className="text-xs text-gray-500 mt-1.5">
                {parseFloat(patient.risk_score).toFixed(1)}% at discharge
                {patient.weeks_tracked ? ` · ${patient.weeks_tracked} weeks monitored` : ''}
              </span>
            )}
          </div>
          <div className="hidden md:block w-px h-16 bg-gray-300"></div>
          <div className="flex flex-col items-center md:items-start space-y-2">
            <span className="text-sm font-medium text-gray-500">Risk Band</span>
            <div className="transform scale-110">
              <RiskBadge riskBand={currentBand} />
            </div>
            {hasMonitoring && patient.risk_band !== currentBand && (
              <span className="text-xs text-gray-500">was {patient.risk_band} at discharge</span>
            )}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
        
        {/* Left Column: Drivers */}
        <div className="lg:col-span-1 space-y-6">
          <h2 className="text-xl font-semibold text-ns-navy border-b pb-2">Primary Drivers</h2>
          <div className="space-y-4">
            {patient.drivers.map((driver, idx) => (
              <DriverCard
                key={idx}
                label={driver.label}
                value={driver.value}
                explanation={driver.explanation}
                category={driver.category}
                riskBand={patient.risk_band}
              />
            ))}
          </div>
        </div>

        {/* Right Column: Chart & Actions */}
        <div className="lg:col-span-2 space-y-8">
          
          {/* Score History */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h2 className="text-xl font-semibold text-ns-navy mb-6 flex items-center space-x-2">
              <TrendingUp className="text-gray-400" size={22} />
              <span>Score History</span>
            </h2>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={history} margin={{ top: 5, right: 20, left: -20, bottom: 5 }}>
                  <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="#f0f0f0" />
                  <XAxis 
                    dataKey="week" 
                    tick={{fill: '#9ca3af', fontSize: 13}}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis 
                    domain={[0, 100]}
                    tick={{fill: '#9ca3af', fontSize: 13}}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip 
                    contentStyle={{ borderRadius: '8px', border: '1px solid #e5e7eb', boxShadow: '0 4px 6px -1px rgb(0 0 0 / 0.1)' }}
                  />
                  <Line 
                    type="monotone" 
                    dataKey="score" 
                    stroke="#0F2A4A" 
                    strokeWidth={3}
                    dot={{ fill: '#0F2A4A', strokeWidth: 2, r: 4 }}
                    activeDot={{ r: 6, fill: '#C0392B', strokeWidth: 0 }}
                  />
                </LineChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Suggested Actions */}
          <div className="bg-white p-6 rounded-xl border border-gray-200 shadow-sm">
            <h2 className="text-xl font-semibold text-ns-navy mb-4 flex items-center space-x-2 border-b pb-4">
              <ListChecks className="text-gray-400" size={22} />
              <span>Suggested Clinical Actions</span>
            </h2>
            <ul className="space-y-3">
              {actions.map((action, idx) => (
                <li key={idx} className="flex items-start bg-gray-50 p-3 rounded-lg border border-gray-100">
                  <div className={`mt-0.5 mr-3 w-5 h-5 rounded-full flex items-center justify-center shrink-0 ${getScoreColor(currentBand).replace('text-', 'bg-').replace('high', 'high/20').replace('medium', 'medium/20').replace('low', 'low/20')}`}>
                    <div className={`w-2 h-2 rounded-full ${getScoreColor(currentBand).replace('text-', 'bg-')}`}></div>
                  </div>
                  <span className="text-gray-700 font-medium">{action}</span>
                </li>
              ))}
            </ul>
          </div>

          <ForecastPanel patientId={patient.id} />

          <AiInsightsPanel
            patientId={patient.id}
            riskScore={patient.risk_score}
            riskBand={patient.risk_band}
            drivers={patient.drivers}
          />

          <CareCoordination patientId={patient.id} />

        </div>
      </div>

      <div className="h-10"></div>
    </div>
  );
}
