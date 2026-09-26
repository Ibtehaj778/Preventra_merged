import { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { api } from '../data/api';

// A patient's own record. The backend only ever returns their own row from the
// patient list, so the first row is theirs.
export default function MyRecord() {
  const [state, setState] = useState({ loading: true, idx: null });

  useEffect(() => {
    let current = true;
    api.getPatients({ page_size: 1 })
      .then((res) => { if (current) setState({ loading: false, idx: res.patients?.[0]?.patient_idx ?? null }); })
      .catch(() => { if (current) setState({ loading: false, idx: null }); });
    return () => { current = false; };
  }, []);

  if (state.loading) return <div className="card p-8 text-center text-sm text-gray-500">Loading your record…</div>;
  if (state.idx == null) {
    return (
      <div className="card p-8 text-center text-sm text-gray-500">
        No GLP-1 record is linked to your account yet. Your care team can link it for you.
      </div>
    );
  }
  return <Navigate to={`/patients/${state.idx}`} replace />;
}
