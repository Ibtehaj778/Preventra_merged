import { useState, useEffect } from "react";
import { api } from "../data/api";
import { ceaData as mockCEA, segmentProfiles as mockSegments } from "../data/mockData";

const FALLBACK = { cea: mockCEA, benchmarks: null };

export function useCostEffectiveness() {
  const [data, setData]       = useState(FALLBACK);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    api.getCostEffectiveness()
      .then((res) => setData(res))
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
