import { useState, useEffect } from "react";
import { api } from "../data/api";

// null until loaded - never stand-in cost figures.
export function useCostEffectiveness() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    let live = true;
    api.getCostEffectiveness()
      .then((res) => { if (live) setData(res); })
      .catch((err) => { if (live) setError(err); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  return { data, loading, error };
}
