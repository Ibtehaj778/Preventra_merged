import { useEffect, useState } from 'react';
import { Building2 } from 'lucide-react';
import { AUTH_BASE, getActingHospital, setActingHospital } from '../../data/api';
import { useAuth } from '../../context/AuthContext';
import { useRole } from '../../context/RoleContext';

/**
 * The superadmin's hospital picker: every page then shows what that hospital's
 * admin sees, or every hospital at once. Nothing for anyone else - and the
 * backend ignores the choice for anyone else too. Changing it reloads, so no
 * screen can mix two hospitals' figures.
 */
export default function HospitalPicker() {
  const { isSuperadmin } = useRole();
  const { token } = useAuth();
  const [hospitals, setHospitals] = useState([]);
  const current = getActingHospital();

  useEffect(() => {
    if (!isSuperadmin) return undefined;
    let live = true;
    fetch(`${AUTH_BASE}/auth/admin/hospitals`, { headers: { Authorization: `Bearer ${token}` } })
      .then((r) => (r.ok ? r.json() : []))
      .then((list) => { if (live) setHospitals(Array.isArray(list) ? list : []); })
      .catch(() => {});
    return () => { live = false; };
  }, [isSuperadmin, token]);

  if (!isSuperadmin) return null;
  return (
    <label className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-full text-xs border border-gray-200 bg-white">
      <Building2 size={12} className="text-gray-400" />
      <span className="sr-only">Hospital</span>
      <select value={current}
        onChange={(e) => { setActingHospital(e.target.value); window.location.reload(); }}
        className="bg-transparent font-medium text-gray-700 focus:outline-none max-w-[10rem]">
        <option value="">All hospitals</option>
        {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
        {current && !hospitals.some((h) => h.id === current) && <option value={current}>{current}</option>}
      </select>
    </label>
  );
}
