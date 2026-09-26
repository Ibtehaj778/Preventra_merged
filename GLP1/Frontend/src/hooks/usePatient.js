import { useState, useEffect } from "react";
import { api } from "../data/api";

// No stand-in data: a patient the backend refuses (not yours, or not there)
// must read as unavailable, never as someone else's record. Every other hook
// keeps its mock fallback for now; this is the one that shows a person.
export function usePatient(id) {
  const numId = Number(id);
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (id == null) return;
    let current = true;
    api.getPatient(numId)
      .then((res) => { if (current) { setData(res); setError(null); } })
      .catch((err) => { if (current) { setData(null); setError(err); } })
      .finally(() => { if (current) setLoading(false); });
    return () => { current = false; };
  }, [id, numId]);

  return { data, loading, error };
}
