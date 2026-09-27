import React, { useEffect, useState } from 'react';
import { Building } from 'lucide-react';
import { API_BASE_URL, getActingHospital, setActingHospital } from '../api';
import { getToken, readClaims } from '../api/auth';

/**
 * The superadmin's hospital picker: every page then shows exactly what that
 * hospital's admin sees, or every hospital at once. Renders nothing for anyone
 * else - and the backend ignores the choice for anyone else too.
 *
 * Changing it reloads the page, so nothing on screen can mix two hospitals.
 */
export default function HospitalPicker() {
  const isSuper = readClaims()?.role === 'superadmin';
  const [hospitals, setHospitals] = useState([]);
  const current = getActingHospital();

  useEffect(() => {
    if (!isSuper) return undefined;
    let live = true;
    fetch(`${API_BASE_URL}/auth/admin/hospitals`, { headers: { Authorization: `Bearer ${getToken()}` } })
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => { if (live) setHospitals(Array.isArray(list) ? list : []); })
      .catch(() => {});
    return () => { live = false; };
  }, [isSuper]);

  if (!isSuper) return null;
  return (
    <label className="flex items-center gap-1.5 rounded-lg border border-gray-200 bg-gray-50 px-2 py-1 text-sm text-gray-600">
      <Building size={15} className="text-gray-400" />
      <span className="sr-only">Hospital</span>
      <select
        value={current}
        onChange={(e) => { setActingHospital(e.target.value); window.location.reload(); }}
        className="max-w-[11rem] bg-transparent py-0.5 font-medium text-gray-800 focus:outline-none"
      >
        <option value="">All hospitals</option>
        {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        {current && !hospitals.some((h) => h.id === current) && <option value={current}>{current}</option>}
      </select>
    </label>
  );
}
