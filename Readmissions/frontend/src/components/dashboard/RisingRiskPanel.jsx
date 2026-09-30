import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { AlertTriangle, ChevronDown, ChevronUp } from 'lucide-react';
import { getRisingRisk, markRiskSeen } from '../../api';
import { RisingRiskRow } from '../shared/RisingRiskList';

const FIRST = 5;

/**
 * "Needs attention": the signed-in doctor's (or nurse's) patients whose latest
 * monitoring week got worse, at the top of their patient list. The backend
 * decides whose patients these are (api/risk_watch.py). Hidden when nothing
 * rose, so a quiet week costs no space.
 */
export default function RisingRiskPanel() {
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [expanded, setExpanded] = useState(false);

  useEffect(() => {
    let live = true;
    getRisingRisk(50).then((d) => { if (live) setData(d); }).catch(() => {});
    return () => { live = false; };
  }, []);

  if (!data || !data.total) return null;

  const open = (item) => {
    // Tell the bell, so its count drops now rather than at its next poll.
    markRiskSeen(item.patient_id, item.week_number)
      .then(() => window.dispatchEvent(new Event('rising-risk-changed')))
      .catch(() => {});
    navigate(`/patients/${encodeURIComponent(item.patient_id)}/trend`);
  };
  const shown = expanded ? data.patients : data.patients.slice(0, FIRST);

  return (
    <section className="mb-5 overflow-hidden rounded-xl border border-red-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center gap-2 border-b border-red-100 bg-red-50 px-4 py-3">
        <AlertTriangle size={18} className="text-risk-high" />
        <h2 className="font-semibold text-ns-navy">Needs attention</h2>
        <span className="text-sm text-gray-600">
          {data.total} of your patients got worse in their latest week
          {data.urgent > 0 && <> · <strong className="text-risk-high">{data.urgent} urgent</strong></>}
        </span>
      </div>
      <div className="divide-y divide-gray-100">
        {shown.map((item) => <RisingRiskRow key={item.patient_id} item={item} onOpen={open} />)}
      </div>
      {data.patients.length > FIRST && (
        <button type="button" onClick={() => setExpanded((v) => !v)}
          className="flex w-full items-center justify-center gap-1 border-t border-gray-100 py-2 text-sm font-medium text-ns-navy hover:bg-gray-50">
          {expanded ? <>Show fewer <ChevronUp size={14} /></>
            : <>Show all {data.patients.length}{data.total > data.patients.length ? ` of ${data.total}` : ''} <ChevronDown size={14} /></>}
        </button>
      )}
    </section>
  );
}
