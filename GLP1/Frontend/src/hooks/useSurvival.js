import { useState, useEffect } from "react";
import { api } from "../data/api";
import {
  survivalCurves as mockCurves,
  survivalCheckpoints as mockCheckpoints,
  medianSurvival as mockMedian,
} from "../data/mockData";

const FALLBACK = {
  curves:          mockCurves,
  checkpoints:     mockCheckpoints,
  medianSurvival:  mockMedian,
};

export function useSurvival() {
  const [data, setData]       = useState(FALLBACK);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    api.getSurvival()
      .then((res) => {
        setData({
          curves:         res.curves,
          checkpoints:    res.checkpoints,
          medianSurvival: res.median_survival,
        });
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
