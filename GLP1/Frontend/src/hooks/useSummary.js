import { useState, useEffect } from "react";
import { api } from "../data/api";

// No stand-in figures: until the caller's own summary arrives the page shows a
// skeleton, and a failure shows the failure. Made-up KPIs on a hospital's
// dashboard would read exactly like real ones.
export function useSummary() {
  const [data, setData]       = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

  useEffect(() => {
    let live = true;
    Promise.all([api.getSummary(), api.getGlobalSHAP()])
      .then(([summary, shap]) => {
        if (!live) return;
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
      .catch((err) => { if (live) setError(err); })
      .finally(() => { if (live) setLoading(false); });
    return () => { live = false; };
  }, []);

  return { data, loading, error };
}
