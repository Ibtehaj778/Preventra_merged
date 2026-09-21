import { useState, useEffect } from "react";
import { api } from "../data/api";
import { patients as mockPatients } from "../data/mockData";

export function usePatient(id) {
  const numId   = Number(id);
  const fallback = mockPatients.find((p) => p.patient_idx === numId) ?? mockPatients[0];

  const [data, setData]       = useState({ patient: fallback, shap_drivers: null, segment_survival: null });
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    if (id == null) return;
    api.getPatient(numId)
      .then((res) => setData(res))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, [numId]);

  return { data, loading, error };
}
