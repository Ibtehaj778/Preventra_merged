import { useState, useEffect } from "react";
import { api } from "../data/api";

// null until loaded - never stand-in survival curves.
export function useSurvival() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    let live = true;
    api.getSurvival()
      .then((res) => {
        if (!live) return;
        setData({
          curves:         res.curves,
          checkpoints:    res.checkpoints,
          medianSurvival: res.median_survival,
        });
      })
      .catch((err) => { if (live) setError(err); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  return { data, loading, error };
}
