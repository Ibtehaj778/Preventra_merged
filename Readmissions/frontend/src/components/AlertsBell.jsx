import React, { useEffect, useRef, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { getAlerts, acknowledgeAlert } from '../api';
import { Bell, Check, Loader2 } from 'lucide-react';

const POLL_INTERVAL_MS = 30000;

export default function AlertsBell() {
  const navigate = useNavigate();
  const [alerts, setAlerts] = useState([]);
  const [open, setOpen] = useState(false);
  const [acknowledgingId, setAcknowledgingId] = useState(null);
  const containerRef = useRef(null);

  const load = () => {
    getAlerts()
      .then((data) => setAlerts(Array.isArray(data) ? data : []))
      .catch(() => {});
  };

  useEffect(() => {
    load();
    const interval = setInterval(load, POLL_INTERVAL_MS);
    return () => clearInterval(interval);
  }, []);

  useEffect(() => {
    const handleClickOutside = (e) => {
      if (containerRef.current && !containerRef.current.contains(e.target)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const handleAcknowledge = async (alertId) => {
    setAcknowledgingId(alertId);
    try {
      await acknowledgeAlert(alertId);
      setAlerts((prev) => prev.filter((a) => a.id !== alertId));
    } catch {
      // leave it in the list — user can retry
    } finally {
      setAcknowledgingId(null);
    }
  };

  const handleGoToPatient = (patientId) => {
    setOpen(false);
    navigate(`/patients/${patientId}`);
  };

  return (
    <div className="relative" ref={containerRef}>
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="relative p-2 text-gray-500 hover:text-ns-navy hover:bg-gray-100 rounded-full transition-colors"
        aria-label="Alerts"
      >
        <Bell size={20} />
        {alerts.length > 0 && (
          <span className="absolute -top-0.5 -right-0.5 bg-risk-high text-white text-[10px] font-bold rounded-full min-w-[18px] h-[18px] flex items-center justify-center px-1">
            {alerts.length > 9 ? '9+' : alerts.length}
          </span>
        )}
      </button>

      {open && (
        <div className="absolute right-0 mt-2 w-96 bg-white rounded-xl border border-gray-200 shadow-lg z-50 overflow-hidden animate-in fade-in slide-in-from-top-2 duration-150">
          <div className="px-4 py-3 border-b border-gray-100 bg-gray-50">
            <h3 className="font-semibold text-gray-800 text-sm">Risk Increase Alerts</h3>
          </div>
          <div className="max-h-96 overflow-y-auto divide-y divide-gray-100">
            {alerts.length === 0 && (
              <p className="text-sm text-gray-400 italic px-4 py-6 text-center">No unacknowledged alerts.</p>
            )}
            {alerts.map((alert) => (
              <div key={alert.id} className="px-4 py-3 hover:bg-gray-50 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <button
                    type="button"
                    onClick={() => handleGoToPatient(alert.patient_id)}
                    className="text-left flex-1"
                  >
                    <p className="text-sm font-semibold text-ns-navy hover:underline">{alert.patient_id}</p>
                    <p className="text-sm text-gray-600 mt-0.5">
                      {parseFloat(alert.old_score).toFixed(1)}% ({alert.old_band}) &rarr;{' '}
                      <span className="font-semibold text-risk-high">
                        {parseFloat(alert.new_score).toFixed(1)}% ({alert.new_band})
                      </span>
                    </p>
                    <p className="text-xs text-gray-400 mt-1">{alert.triggered_at}</p>
                  </button>
                  <button
                    type="button"
                    onClick={() => handleAcknowledge(alert.id)}
                    disabled={acknowledgingId === alert.id}
                    className="shrink-0 p-1.5 text-gray-400 hover:text-green-600 hover:bg-green-50 rounded-full transition-colors disabled:opacity-50"
                    title="Acknowledge"
                  >
                    {acknowledgingId === alert.id ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Check size={16} />
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
