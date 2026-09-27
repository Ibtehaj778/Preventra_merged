import { useState, useEffect } from "react";
import { api } from "../data/api";

// null until loaded - never stand-in model metrics.
export function useModelInfo() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    let live = true;
    api.getModelInfo()
      .then((res) => {
        if (!live) return;
        // Normalise API shape to match what Settings.jsx expects
        setData({
          name:        res.name,
          params:      res.params,
          accuracy:    res.accuracy,
          precision:   res.precision,
          recall:      res.recall,
          f1:          res.f1,
          auc:         res.auc_roc,
          threshold:   res.threshold,
          trainSize:   res.train_size,
          testSize:    res.test_size,
          lastTrained: res.last_trained,
        });
      })
      .catch((err) => { if (live) setError(err); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  return { data, loading, error };
}
