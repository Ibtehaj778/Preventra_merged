import React, { useEffect, useState } from 'react';
import { Navigate } from 'react-router-dom';
import { getPatients } from '../api';

// A patient's own record. The backend only ever returns their own row from the
// worklist, so the first row is theirs.
export default function MyRecord() {
  const [state, setState] = useState({ loading: true, id: null });

  useEffect(() => {
    let current = true;
    getPatients({ limit: 1 })
      .then((res) => { if (current) setState({ loading: false, id: res?.data?.[0]?.id ?? null }); })
      .catch(() => { if (current) setState({ loading: false, id: null }); });
    return () => { current = false; };
  }, []);

  if (state.loading) return <p className="p-6 text-sm text-gray-500">Loading your record…</p>;
  if (!state.id) {
    return (
      <p className="p-6 text-sm text-gray-500">
        No readmission record is linked to your account yet. Your care team can link it for you.
      </p>
    );
  }
  return <Navigate to={`/patients/${encodeURIComponent(state.id)}`} replace />;
}
