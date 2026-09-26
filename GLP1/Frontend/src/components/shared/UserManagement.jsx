// User Management - identical copy in GLP1/Frontend and Readmissions/frontend
// (src/components/shared/UserManagement.jsx). Accounts are shared by both apps,
// so change both files together.
//
// Everything here is a view over the auth service's /auth/admin/* endpoints
// (Readmissions/api/user_admin.py), which decide who may do what. Hiding a
// control is a courtesy; the server refuses the call either way.
import { useCallback, useEffect, useState } from 'react';

const ROLE_LABELS = {
  superadmin: 'Superadmin', hospital_admin: 'Hospital admin', doctor: 'Doctor',
  nurse: 'Nurse', case_manager: 'Case manager', insurer: 'Insurer', patient: 'Patient',
};

// Mirrors ASSIGNABLE in Readmissions/api/user_admin.py.
const ASSIGNABLE = {
  superadmin: ['hospital_admin', 'doctor', 'nurse', 'case_manager', 'insurer', 'patient'],
  hospital_admin: ['doctor', 'nurse', 'case_manager', 'patient'],
};
const HOSPITAL_ROLES = ['hospital_admin', 'doctor', 'nurse', 'case_manager', 'patient'];

const input = 'w-full rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-800 focus:border-blue-500 focus:outline-none';
const button = 'rounded-md bg-blue-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-blue-700 disabled:opacity-50';
const ghost = 'rounded-md border border-gray-300 px-2.5 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50 disabled:opacity-50';
const panel = 'rounded-xl border border-gray-200 bg-white p-5';

/**
 * @param {string}   authBaseUrl  origin of the shared auth service (the Readmissions API)
 * @param {Function} getToken     returns the signed-in user's bearer token. Pass a stable
 *                               function (module-level), not an inline arrow: a new
 *                               function each render would reload the list each render.
 * @param {object}   me           the signed-in account: { sub|id, email, role, hospital_id }
 */
export default function UserManagement({ authBaseUrl, getToken, me }) {
  const isSuper = me?.role === 'superadmin';
  const myId = me?.sub || me?.id;
  const assignable = ASSIGNABLE[me?.role] || [];

  const [users, setUsers] = useState([]);
  const [hospitals, setHospitals] = useState([]);
  const [insurers, setInsurers] = useState([]);
  const [filter, setFilter] = useState({ hospital_id: '', status: '' });
  const [error, setError] = useState(null);
  const [notice, setNotice] = useState(null);
  const [busy, setBusy] = useState(false);

  const request = useCallback(async (path, { method = 'GET', body } = {}) => {
    const res = await fetch(`${authBaseUrl.replace(/\/$/, '')}${path}`, {
      method,
      headers: { Authorization: `Bearer ${getToken()}`,
                 ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok) {
      const detail = Array.isArray(data.detail) ? data.detail.map((d) => d.msg).join('; ') : data.detail;
      throw new Error(detail || `Request failed (${res.status})`);
    }
    return data;
  }, [authBaseUrl, getToken]);

  // Bumped after every change to refetch the lists.
  const [reloadKey, setReloadKey] = useState(0);

  useEffect(() => {
    // A response that arrives after the filters changed is dropped, so a slow
    // earlier request cannot overwrite a newer answer.
    let current = true;
    const qs = new URLSearchParams(Object.entries(filter).filter(([, v]) => v));
    Promise.all([
      request(`/auth/admin/users${qs.toString() ? `?${qs}` : ''}`),
      request('/auth/admin/hospitals'),
      isSuper ? request('/auth/admin/insurers') : Promise.resolve([]),
    ]).then(([u, h, i]) => {
      if (!current) return;
      setUsers(u); setHospitals(h); setInsurers(i); setError(null);
    }).catch((e) => { if (current) setError(e.message); });
    return () => { current = false; };
  }, [request, filter, isSuper, reloadKey]);

  const run = async (action, onDone) => {
    setBusy(true); setError(null);
    try { const out = await action(); onDone?.(out); setReloadKey((k) => k + 1); }
    catch (e) { setError(e.message); }
    finally { setBusy(false); }
  };

  const hospitalName = (id) => hospitals.find((h) => h.id === id)?.name || id || '—';

  return (
    <div className="space-y-5">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">User Management</h2>
        <p className="text-sm text-gray-500">
          {isSuper ? 'All hospitals and insurers.' : `Staff and patients of ${hospitalName(me?.hospital_id)}.`}
          {' '}Accounts work in both GLP-1 and Readmissions.
        </p>
      </div>

      {error && <div className="rounded-md bg-red-50 px-3 py-2 text-sm text-red-700">{error}</div>}
      {notice && <Notice notice={notice} onClose={() => setNotice(null)} />}

      {isSuper && (
        <div className="grid gap-5 md:grid-cols-2">
          <OrgPanel title="Hospitals" items={hospitals} busy={busy}
                    onCreate={(name) => run(() => request('/auth/admin/hospitals', { method: 'POST', body: { name } }))} />
          <OrgPanel title="Insurers" items={insurers} busy={busy}
                    onCreate={(name) => run(() => request('/auth/admin/insurers', { method: 'POST', body: { name } }))} />
        </div>
      )}

      <AddUser assignable={assignable} isSuper={isSuper} hospitals={hospitals} insurers={insurers} busy={busy}
               onAdd={(body) => run(() => request('/auth/admin/users', { method: 'POST', body }),
                                    (out) => setNotice({ kind: 'created', results: [out] }))} />

      <ImportCsv isSuper={isSuper} hospitals={hospitals} insurers={insurers} busy={busy}
                 onImport={(body) => run(() => request('/auth/admin/users/import', { method: 'POST', body }),
                                         (out) => setNotice({ kind: 'import', ...out }))} />

      <div className={panel}>
        <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
          <h3 className="font-semibold text-gray-800">Accounts ({users.length})</h3>
          <div className="flex gap-2">
            {isSuper && (
              <select className={input} value={filter.hospital_id}
                      onChange={(e) => setFilter({ ...filter, hospital_id: e.target.value })}>
                <option value="">All hospitals</option>
                {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
              </select>
            )}
            <select className={input} value={filter.status}
                    onChange={(e) => setFilter({ ...filter, status: e.target.value })}>
              <option value="">Any status</option>
              <option value="pending">Pending</option>
              <option value="active">Active</option>
            </select>
          </div>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 text-xs uppercase text-gray-500">
              <tr><th className="py-2 pr-3">Account</th><th className="py-2 pr-3">Role</th>
                  <th className="py-2 pr-3">Hospital / insurer</th><th className="py-2 pr-3">Status</th>
                  <th className="py-2 pr-3">Created</th><th className="py-2" /></tr>
            </thead>
            <tbody>
              {users.map((u) => (
                <UserRow key={u.sub} user={u} me={me} myId={myId} isSuper={isSuper}
                         assignable={assignable} hospitals={hospitals} insurers={insurers}
                         hospitalName={hospitalName} busy={busy}
                         onSave={(body) => run(() => request(`/auth/admin/users/${u.sub}`, { method: 'PATCH', body }))} />
              ))}
              {!users.length && (
                <tr><td colSpan={6} className="py-6 text-center text-gray-400">No accounts match.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}

// Can this signed-in manager change this row? The same rules as the server's
// _may_manage, so the controls shown are the ones that will work.
function canManage(user, me, myId, isSuper) {
  if (user.role === 'superadmin' || user.sub === myId) return false;
  if (isSuper) return true;
  return user.hospital_id === me?.hospital_id && ASSIGNABLE.hospital_admin.includes(user.role);
}

function UserRow({ user, me, myId, isSuper, assignable, hospitals, insurers, hospitalName, busy, onSave }) {
  const [role, setRole] = useState(user.role);
  const [hospitalId, setHospitalId] = useState(user.hospital_id || '');
  const [insurerId, setInsurerId] = useState(user.insurer_id || '');
  const editable = canManage(user, me, myId, isSuper);
  const changed = role !== user.role || (hospitalId || null) !== (user.hospital_id || null)
                  || (insurerId || null) !== (user.insurer_id || null);
  const placement = () => (HOSPITAL_ROLES.includes(role) ? { hospital_id: hospitalId || null }
                           : role === 'insurer' ? { insurer_id: insurerId || null } : {});

  return (
    <tr className="border-b border-gray-100 align-top">
      <td className="py-2 pr-3">
        <div className="font-medium text-gray-800">{user.email}</div>
        <div className="text-xs text-gray-500">
          {user.name || '—'}{user.must_change_password && ' · must set a password'}
        </div>
      </td>
      <td className="py-2 pr-3">
        {editable ? (
          <select className={input} value={role} onChange={(e) => setRole(e.target.value)}>
            {[...new Set([user.role, ...assignable])].map((r) => (
              <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>))}
          </select>
        ) : ROLE_LABELS[user.role] || user.role}
      </td>
      <td className="py-2 pr-3">
        {editable && isSuper && HOSPITAL_ROLES.includes(role) ? (
          <select className={input} value={hospitalId} onChange={(e) => setHospitalId(e.target.value)}>
            <option value="">— choose —</option>
            {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        ) : editable && isSuper && role === 'insurer' ? (
          <select className={input} value={insurerId} onChange={(e) => setInsurerId(e.target.value)}>
            <option value="">— choose —</option>
            {insurers.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
          </select>
        ) : user.insurer_id || hospitalName(user.hospital_id)}
      </td>
      <td className="py-2 pr-3">
        <span className={`rounded-full px-2 py-0.5 text-xs font-medium ${
          user.status === 'pending' ? 'bg-amber-100 text-amber-800' : 'bg-green-100 text-green-800'}`}>
          {user.status}
        </span>
      </td>
      <td className="py-2 pr-3 text-xs text-gray-500">{(user.created_at || '').slice(0, 10) || '—'}</td>
      <td className="py-2 text-right whitespace-nowrap">
        {editable && (
          <div className="flex justify-end gap-1.5">
            {changed && (
              <button className={ghost} disabled={busy}
                      onClick={() => onSave({ role, ...placement() })}>Save</button>
            )}
            {user.status === 'pending' ? (
              <button className={ghost} disabled={busy}
                      onClick={() => onSave({ status: 'active', role, ...placement() })}>Approve</button>
            ) : (
              <button className={ghost} disabled={busy}
                      onClick={() => onSave({ status: 'pending' })}>Suspend</button>
            )}
          </div>
        )}
      </td>
    </tr>
  );
}

function OrgPanel({ title, items, busy, onCreate }) {
  const [name, setName] = useState('');
  return (
    <div className={panel}>
      <h3 className="mb-2 font-semibold text-gray-800">{title} ({items.length})</h3>
      <form className="mb-3 flex gap-2"
            onSubmit={(e) => { e.preventDefault(); if (name.trim()) { onCreate(name.trim()); setName(''); } }}>
        <input className={input} placeholder={`New ${title.toLowerCase().slice(0, -1)} name`}
               value={name} onChange={(e) => setName(e.target.value)} />
        <button className={button} disabled={busy || !name.trim()}>Add</button>
      </form>
      <ul className="max-h-40 space-y-1 overflow-y-auto text-sm text-gray-700">
        {items.map((o) => <li key={o.id}>{o.name} <span className="text-xs text-gray-400">{o.id}</span></li>)}
      </ul>
    </div>
  );
}

function AddUser({ assignable, isSuper, hospitals, insurers, busy, onAdd }) {
  const [form, setForm] = useState({ email: '', name: '', role: assignable[0] || '',
                                     hospital_id: '', insurer_id: '' });
  const set = (k) => (e) => setForm({ ...form, [k]: e.target.value });
  return (
    <div className={panel}>
      <h3 className="mb-1 font-semibold text-gray-800">Add a person</h3>
      <p className="mb-3 text-xs text-gray-500">
        They get a temporary password to change at first sign-in. If they already
        signed up and are waiting for approval, this approves their account instead.
      </p>
      <form className="grid gap-2 md:grid-cols-5"
            onSubmit={(e) => {
              e.preventDefault();
              onAdd({ email: form.email, name: form.name, role: form.role,
                      hospital_id: isSuper && HOSPITAL_ROLES.includes(form.role) ? form.hospital_id || null : null,
                      insurer_id: form.role === 'insurer' ? form.insurer_id || null : null });
              setForm({ ...form, email: '', name: '' });
            }}>
        <input className={input} type="email" required placeholder="Email" value={form.email} onChange={set('email')} />
        <input className={input} placeholder="Name" value={form.name} onChange={set('name')} />
        <select className={input} value={form.role} onChange={set('role')}>
          {assignable.map((r) => <option key={r} value={r}>{ROLE_LABELS[r]}</option>)}
        </select>
        {isSuper && HOSPITAL_ROLES.includes(form.role) ? (
          <select className={input} required value={form.hospital_id} onChange={set('hospital_id')}>
            <option value="">Hospital…</option>
            {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
          </select>
        ) : form.role === 'insurer' ? (
          <select className={input} required value={form.insurer_id} onChange={set('insurer_id')}>
            <option value="">Insurer…</option>
            {insurers.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
          </select>
        ) : <div />}
        <button className={button} disabled={busy}>Add</button>
      </form>
    </div>
  );
}

function ImportCsv({ isSuper, hospitals, insurers, busy, onImport }) {
  const [csv, setCsv] = useState('');
  const [hospitalId, setHospitalId] = useState('');
  const [insurerId, setInsurerId] = useState('');
  const readFile = (e) => {
    const file = e.target.files?.[0];
    if (file) file.text().then(setCsv);
  };
  return (
    <details className={panel}>
      <summary className="cursor-pointer font-semibold text-gray-800">Import staff from CSV</summary>
      <p className="mt-2 text-xs text-gray-500">
        Header row required: <code>email,name,role</code>. Roles use the names above
        (for example <code>doctor</code>, <code>nurse</code>). Each row succeeds or fails on its own.
      </p>
      <div className="mt-3 space-y-2">
        <input type="file" accept=".csv,text/csv" onChange={readFile} className="text-sm" />
        <textarea className={`${input} h-28 font-mono text-xs`} value={csv} onChange={(e) => setCsv(e.target.value)}
                  placeholder={'email,name,role\ndoc@hospital.org,Dr Jane Smith,doctor'} />
        {isSuper && (
          <div className="grid gap-2 md:grid-cols-2">
            <select className={input} value={hospitalId} onChange={(e) => setHospitalId(e.target.value)}>
              <option value="">Hospital for hospital roles…</option>
              {hospitals.map((h) => <option key={h.id} value={h.id}>{h.name}</option>)}
            </select>
            <select className={input} value={insurerId} onChange={(e) => setInsurerId(e.target.value)}>
              <option value="">Insurer for insurer rows…</option>
              {insurers.map((i) => <option key={i.id} value={i.id}>{i.name}</option>)}
            </select>
          </div>
        )}
        <button className={button} disabled={busy || !csv.trim()}
                onClick={() => onImport({ csv, hospital_id: hospitalId || null, insurer_id: insurerId || null })}>
          Import
        </button>
      </div>
    </details>
  );
}

// Temporary passwords are shown once, here, and never again - the server keeps
// only a hash. The admin hands them over; the user must change theirs at first
// sign-in.
function Notice({ notice, onClose }) {
  const created = notice.kind === 'import' ? notice.created : notice.results;
  const failed = notice.kind === 'import' ? notice.failed : [];
  return (
    <div className="rounded-xl border border-blue-200 bg-blue-50 p-4 text-sm text-gray-800">
      <div className="mb-2 flex items-start justify-between gap-3">
        <b>{notice.kind === 'import' ? `Imported ${created.length}, ${failed.length} failed` : 'Done'}</b>
        <button className={ghost} onClick={onClose}>Dismiss</button>
      </div>
      {created.some((c) => c.temporary_password) && (
        <p className="mb-2 text-xs text-gray-600">
          Temporary passwords are shown only now. Share each one privately; the person
          must change it the first time they sign in.
        </p>
      )}
      <ul className="space-y-1">
        {created.map((c) => (
          <li key={c.user.sub}>
            {c.user.email} — {c.approved_existing
              ? 'existing account approved (they keep their own password)'
              : <>temporary password <code className="rounded bg-white px-1.5 py-0.5 font-mono">{c.temporary_password}</code></>}
          </li>
        ))}
        {failed.map((f) => (
          <li key={`${f.line}-${f.email}`} className="text-red-700">
            Line {f.line} ({f.email || 'no email'}): {f.error}
          </li>
        ))}
      </ul>
    </div>
  );
}
