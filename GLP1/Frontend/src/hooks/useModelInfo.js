import { useState, useEffect } from "react";
import { api } from "../data/api";
import { modelInfo as mockModelInfo } from "../data/mockData";

export function useModelInfo() {
  const [data, setData]       = useState(mockModelInfo);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    api.getModelInfo()
      .then((res) => {
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
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
