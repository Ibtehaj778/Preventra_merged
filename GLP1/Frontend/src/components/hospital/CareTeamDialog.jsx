import { useEffect, useState } from 'react';
import { X, Loader2 } from 'lucide-react';
import { api } from '../../data/api';

/**
 * Assign a doctor and nurses to one patient, or to several at once.
 *
 * One patient: the doctor and the nurse list are set as shown.
 * Several: the doctor changes only if one is picked, and ticked nurses are
 * added to whoever each patient already has.
 *
 * Everyone offered belongs to the patients' hospital; the server checks that
 * again and refuses the whole batch otherwise (Backend/core/hospital.assign).
 */
export default function CareTeamDialog({ patientIdxs, hospitalId, current, onClose, onSaved }) {
  const single = patientIdxs.length === 1;
  const [staff, setStaff] = useState(null);
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const [doctorId, setDoctorId] = useState(single ? (current?.doctorId ?? '') : '__keep__');
  const [nurseIds, setNurseIds] = useState(single ? (current?.nurseIds ?? []) : []);

  useEffect(() => {
    let live = true;
    api.getStaff().then((s) => { if (live) setStaff(s); }).catch((e) => { if (live) setError(e.message); });
    return () => { live = false; };
  }, []);

  useEffect(() => {
    const onKey = (e) => e.key === 'Escape' && onClose();
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [onClose]);

  // The superadmin looking at every hospital gets every hospital's staff back;
  // only the patients' own hospital's people can be assigned.
  const sameHospital = (p) => !hospitalId || !p.hospital_id || p.hospital_id === hospitalId;
  const doctors = (staff?.doctors || []).filter(sameHospital);
  const nurses = (staff?.nurses || []).filter(sameHospital);
  const toggleNurse = (id) =>
    setNurseIds((ids) => (ids.includes(id) ? ids.filter((n) => n !== id) : [...ids, id]));

  const save = async (e) => {
    e.preventDefault();
    const body = { patient_ids: patientIdxs };
    if (single) {
      body.doctor_id = doctorId;
      body.nurse_ids = nurseIds;
    } else {
      if (doctorId !== '__keep__') body.doctor_id = doctorId;
      if (nurseIds.length) body.add_nurse_ids = nurseIds;
      if (body.doctor_id === undefined && !body.add_nurse_ids) {
        setError('Pick a doctor or at least one nurse.');
        return;
      }
    }
    setBusy(true);
    setError(null);
    try {
      await api.setCareTeam(body);
      onSaved?.();
    } catch (err) {
      setError(err.message);
      setBusy(false);
    }
  };

  const select = 'w-full text-sm rounded-lg border border-gray-200 px-3 py-2 bg-white focus:outline-none focus:ring-1 focus:ring-blue-400';
  return (
    <div className="fixed inset-0 z-[60] flex items-center justify-center p-4" style={{ background: 'rgba(15,23,42,0.4)' }}
         onClick={onClose}>
      <form onSubmit={save} onClick={(e) => e.stopPropagation()} role="dialog" aria-modal="true"
            aria-label="Assign care team" className="card w-full max-w-md shadow-2xl" style={{ padding: 0 }}>
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-100">
          <h2 className="text-base font-semibold text-gray-800">
            {single ? `Care team for patient #${patientIdxs[0]}` : `Care team for ${patientIdxs.length} patients`}
          </h2>
          <button type="button" onClick={onClose} aria-label="Close" className="text-gray-400 hover:text-gray-600">
            <X size={18} />
          </button>
        </div>
        <div className="px-5 py-4 space-y-5">
          {!staff && !error && <div className="h-24 rounded-lg bg-gray-100 animate-pulse" />}
          {staff && (<>
            <label className="block">
              <span className="text-xs font-semibold uppercase tracking-wider text-gray-400">Doctor</span>
              <select value={doctorId} onChange={(e) => setDoctorId(e.target.value)} className={`${select} mt-1.5`}>
                {!single && <option value="__keep__">Leave as it is</option>}
                <option value="">No doctor</option>
                {doctors.map((d) => (
                  <option key={d.id} value={d.id}>{d.name} ({d.patients} patients)</option>
                ))}
              </select>
              {doctors.length === 0 && (
                <span className="block mt-1 text-xs text-gray-400">No doctor accounts in this hospital yet.</span>
              )}
            </label>
            <fieldset>
              <legend className="text-xs font-semibold uppercase tracking-wider text-gray-400">
                {single ? 'Nurses' : 'Add nurses'}
              </legend>
              {nurses.length === 0 && <p className="mt-1.5 text-sm text-gray-400">No nurse accounts in this hospital yet.</p>}
              <div className="mt-1.5 max-h-48 overflow-y-auto space-y-1">
                {nurses.map((n) => (
                  <label key={n.id} className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm hover:bg-gray-50 cursor-pointer">
                    <input type="checkbox" checked={nurseIds.includes(n.id)} onChange={() => toggleNurse(n.id)} />
                    <span className="flex-1 text-gray-700">{n.name}</span>
                    <span className="text-xs text-gray-400">{n.patients} patients</span>
                  </label>
                ))}
              </div>
            </fieldset>
          </>)}
          {error && <p className="rounded-md px-3 py-2 text-sm" style={{ background: '#FFEBEE', color: '#C62828' }}>{error}</p>}
        </div>
        <div className="flex justify-end gap-2 px-5 py-3 border-t border-gray-100">
          <button type="button" onClick={onClose}
            className="text-sm px-4 py-2 rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50">Cancel</button>
          <button type="submit" disabled={!staff || busy}
            className="inline-flex items-center gap-2 text-sm font-semibold px-4 py-2 rounded-lg text-white disabled:opacity-50"
            style={{ background: 'var(--color-primary)' }}>
            {busy && <Loader2 size={15} className="animate-spin" />} Save
          </button>
        </div>
      </form>
    </div>
  );
}
