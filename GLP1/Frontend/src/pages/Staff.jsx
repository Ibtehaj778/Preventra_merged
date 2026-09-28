import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Stethoscope, HeartPulse, ChevronRight } from 'lucide-react';
import { api } from '../data/api';
import { useRole } from '../context/RoleContext';
import PageState from '../components/shared/PageState';

/**
 * Who looks after whom: each doctor and nurse with their patients and how many
 * of those are non-adherent. For hospital admins, case managers and the
 * superadmin. Doctors and nurses are accounts, added in User Management; a row
 * clicks through to the patient list filtered to that person's patients.
 */
export default function Staff() {
  const navigate = useNavigate();
  const { isManager } = useRole();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let live = true;
    api.getStaff().then((d) => { if (live) setData(d); }).catch((e) => { if (live) setError(e); });
    return () => { live = false; };
  }, []);

  if (!data) return <PageState error={error} label="the staff list" />;

  const showHospital = !data.hospital;
  const table = (title, Icon, people, param) => (
    <div className="card overflow-hidden">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-gray-100">
        <Icon size={16} className="text-gray-400" />
        <h2 className="text-base font-semibold text-gray-800" style={{ fontFamily: 'DM Serif Display, serif' }}>{title}</h2>
      </div>
      <div className="overflow-x-auto">
        <table className="data-table">
          <thead>
            <tr>
              <th>Name</th>
              {showHospital && <th>Hospital</th>}
              <th>Patients</th><th>Non-adherent</th><th>High dropout risk</th><th style={{ width: 40 }} />
            </tr>
          </thead>
          <tbody>
            {people.map((p) => (
              <tr key={p.id} className="cursor-pointer" onClick={() => navigate(`/patients?${param}=${encodeURIComponent(p.id)}`)}>
                <td>
                  <div className="text-sm font-medium text-gray-800">{p.name}</div>
                  <div className="text-[11px] text-gray-400">{p.email}</div>
                </td>
                {showHospital && <td className="text-xs text-gray-500">{p.hospital_id || '—'}</td>}
                <td className="font-mono text-sm font-semibold text-gray-800">{p.patients}</td>
                <td className="font-mono text-sm" style={{ color: p.non_adherent ? '#C62828' : '#A0AEC0', fontWeight: p.non_adherent ? 600 : 400 }}>
                  {p.non_adherent}
                </td>
                <td className="font-mono text-sm" style={{ color: p.high_risk ? '#EF6C00' : '#A0AEC0', fontWeight: p.high_risk ? 600 : 400 }}>
                  {p.high_risk}
                </td>
                <td className="text-gray-300"><ChevronRight size={15} /></td>
              </tr>
            ))}
          </tbody>
        </table>
        {!people.length && <div className="p-8 text-center text-sm text-gray-400">None yet.</div>}
      </div>
    </div>
  );

  return (
    <div className="max-w-[1100px] mx-auto space-y-5 animate-fade-in">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-800" style={{ fontFamily: 'DM Serif Display, serif' }}>Staff</h1>
          <p className="text-xs text-gray-400 mt-0.5">
            {data.hospital ? data.hospital.name : 'All hospitals'} · click someone to see their patients
          </p>
        </div>
        <div className="flex flex-wrap gap-2 text-xs font-semibold">
                  {data.no_doctor > 0 ? (
          <Link to="/patients?unassigned=doctor" className="px-3 py-1.5 rounded-full" style={{ background: '#FFF3E0', color: '#EF6C00' }}>
            {data.no_doctor.toLocaleString()} patients without a doctor
          </Link>
        ) : (
          <span className="px-3 py-1.5 rounded-full" style={{ background: '#E8F5E9', color: '#2E7D32' }}>Every patient has a doctor</span>
        )}
        {data.no_nurse > 0 ? (
          <Link to="/patients?unassigned=nurse" className="px-3 py-1.5 rounded-full" style={{ background: '#FFF3E0', color: '#EF6C00' }}>
            {data.no_nurse.toLocaleString()} patients without a nurse
          </Link>
        ) : (
          <span className="px-3 py-1.5 rounded-full" style={{ background: '#E8F5E9', color: '#2E7D32' }}>Every patient has a nurse</span>
        )}
        </div>
      </div>

      {table('Doctors', Stethoscope, data.doctors, 'doctor')}
      {table('Nurses', HeartPulse, data.nurses, 'nurse')}

      <p className="text-xs text-gray-500">
        Assign patients from the <Link to="/patients" className="font-semibold" style={{ color: 'var(--color-primary)' }}>Patients</Link> page:
        tick them and choose <em>Assign care team</em>, or open one patient.
        {isManager && <> New doctors and nurses are added in{' '}
          <Link to="/settings" className="font-semibold" style={{ color: 'var(--color-primary)' }}>Settings</Link>.</>}
      </p>
    </div>
  );
}
