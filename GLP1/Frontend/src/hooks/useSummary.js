import { useState, useEffect } from "react";
import { api } from "../data/api";
import {
  summaryKPIs,
  adherenceBySegment,
  globalSHAPDrivers,
  dropoutByWindow,
} from "../data/mockData";

const FALLBACK = {
  kpis:                 summaryKPIs,
  adherence_by_segment: adherenceBySegment,
  dropout_by_window:    dropoutByWindow,
  global_shap_drivers:  globalSHAPDrivers,
};

export function useSummary() {
  const [data, setData]       = useState(FALLBACK);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    Promise.all([api.getSummary(), api.getGlobalSHAP()])
      .then(([summary, shap]) => {
        setData({
          kpis: {
            totalPatients:      summary.kpis.total_patients,
            adherenceRate:      summary.kpis.adherence_rate,
            dropoutRate:        summary.kpis.dropout_rate,
            avgAnnualCost:      summary.kpis.avg_annual_cost,
            wastedSpendAnnual:  summary.kpis.wasted_spend_annual,
            benchmarkAdherence: summary.kpis.adherence_rate,
          },
          adherence_by_segment: summary.adherence_by_segment,
          dropout_by_window:    summary.dropout_by_window,
          global_shap_drivers:  shap.drivers,
        });
      })
      .catch((err) => setError(err))
      .finally(() => setLoading(false));
  }, []);

  return { data, loading, error };
}
