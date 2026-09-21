import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { predictPatient, savePatientToWorklist, getManualEntrySchema } from '../api';
import RiskBadge from '../components/shared/RiskBadge';
import DriverCard from '../components/shared/DriverCard';
import AiInsightsPanel from '../components/shared/AiInsightsPanel';
import {
  MimicPatientForm, emptyForm, filledFieldCount, getScoreColor,
} from '../components/shared/PatientFormFields';
import {
  UserPlus,
  Loader2,
  AlertCircle,
  CheckCircle,
  ArrowRight,
  Info,
} from 'lucide-react';

// The model wants 94 features; this form asks for the ~50 a clinician can
// actually supply at discharge. The rest are left missing on purpose — see
// api/mimic_scoring.py for why that is safe rather than lossy.
const MISSINGNESS_NOTE = [
  'A blank field is scored as unknown, not as zero. HistGradientBoosting learned a split direction for missing values during training.',
  'The 48 lab aggregates, the min/max/abnormal-count variants and the remaining APR-DRG detail stay missing unless a batch run supplies them.',
  'charlson_score is derived from the ticked comorbidities on the server and is never accepted as typed input.',
  'Category values come from GET /api/manual-entry/schema, so a model retrain updates this form without a code change.',
];

// ---------------------------------------------------------------------------
// Main component
// ---------------------------------------------------------------------------
export default function ManualEntry() {
  const navigate = useNavigate();

  const [form, setForm]         = useState(emptyForm);
  const [categoricals, setCategoricals] = useState(null);
  const [loading, setLoading]   = useState(false);
  const [error, setError]       = useState(null);
  const [result, setResult]     = useState(null);   // prediction result from backend
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [showDefaults, setShowDefaults] = useState(false);

  const set = (key) => (val) => setForm((f) => ({ ...f, [key]: val }));

  // Category options are read from the model's own feature spec. If the call
  // fails the form still renders — PatientFormFields falls back to the values
  // baked in at build time — so a schema outage degrades rather than blocks.
  useEffect(() => {
    let cancelled = false;
    getManualEntrySchema()
      .then((schema) => { if (!cancelled && schema?.categorical) setCategoricals(schema.categorical); })
      .catch(() => { /* fall back to built-in category lists */ });
    return () => { cancelled = true; };
  }, []);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setLoading(true);
    setError(null);
    setResult(null);
    setSaved(false);
    setSaveError(null);

    try {
      const res = await predictPatient(form);
      setResult(res);
    } catch (err) {
      setError(err.message || 'Prediction failed. Is the backend running?');
    } finally {
      setLoading(false);
    }
  };

  const handleSave = async () => {
    if (!result) return;
    setSaving(true);
    setSaveError(null);

    try {
      await savePatientToWorklist({
        patient_id:    result.patient_id,
        discharge_date: result.discharge_date,
        risk_score:    result.risk_score,
        risk_band:     result.risk_band,
        driver_1:      result.driver_1_raw,
        driver_2:      result.driver_2_raw,
        driver_3:      result.driver_3_raw,
        raw_inputs:    form,
      });
      setSaved(true);
    } catch (err) {
      setSaveError(err.message || 'Failed to save to dashboard.');
    } finally {
      setSaving(false);
    }
  };

  const handleReset = () => {
    setForm(emptyForm());
    setResult(null);
    setError(null);
    setSaved(false);
    setSaveError(null);
  };

  return (
    <div className="p-4 sm:p-6 max-w-5xl mx-auto space-y-6 pb-16 animate-in fade-in duration-500">

      {/* Page header */}
      <div className="border-b border-gray-200 pb-4">
        <div className="flex items-center space-x-3">
          <UserPlus className="text-ns-navy" size={28} />
          <div>
            <h1 className="text-2xl font-bold text-ns-navy">Manual Patient Entry</h1>
            <p className="text-gray-500 mt-0.5 text-sm">
              Enter clinical details to get an instant readmission risk prediction.
            </p>
          </div>
        </div>
      </div>

      {/* How missing fields are treated */}
      <div className="bg-blue-50 border border-blue-200 rounded-xl p-4">
        <button
          type="button"
          onClick={() => setShowDefaults((v) => !v)}
          className="flex items-center space-x-2 text-blue-700 font-medium text-sm hover:underline"
        >
          <Info size={16} />
          <span>{showDefaults ? 'Hide' : 'Show'} how blank fields are scored</span>
        </button>
        {showDefaults && (
          <ul className="mt-3 space-y-1.5 text-sm text-blue-800 list-disc list-inside">
            {MISSINGNESS_NOTE.map((note, i) => <li key={i}>{note}</li>)}
          </ul>
        )}
      </div>

      {/* Form */}
      <form onSubmit={handleSubmit} className="space-y-5">

        <MimicPatientForm form={form} set={set} categoricals={categoricals} />

        {/* Error */}
        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 flex items-start space-x-3 text-red-800">
            <AlertCircle size={20} className="mt-0.5 shrink-0" />
            <div>
              <div className="font-semibold">Prediction failed</div>
              <div className="text-sm mt-0.5 text-red-600">{error}</div>
            </div>
          </div>
        )}

        {/* Submit */}
        <div className="flex items-center justify-end gap-4">
          <span className="text-sm text-gray-500">
            {filledFieldCount(form)} field{filledFieldCount(form) === 1 ? '' : 's'} supplied — the rest score as unknown
          </span>
          <button
            type="submit"
            disabled={loading}
            className="px-8 py-3 bg-ns-navy text-white rounded-xl font-semibold hover:bg-blue-900 transition-colors shadow-sm focus:ring-2 focus:ring-offset-2 focus:ring-ns-navy disabled:opacity-60 disabled:cursor-not-allowed flex items-center space-x-2"
          >
            {loading ? (
              <>
                <Loader2 size={18} className="animate-spin" />
                <span>Running predictor...</span>
              </>
            ) : (
              <span>Run Prediction</span>
            )}
          </button>
        </div>
      </form>

      {/* Result panel */}
      {result && (
        <div className="space-y-5 animate-in slide-in-from-bottom-4 fade-in duration-500">

          {/* Score card */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <div className="flex items-center justify-between mb-5">
              <h2 className="text-lg font-bold text-ns-navy">Prediction Result</h2>
              <span className="text-xs text-gray-400 font-mono">{result.patient_id}</span>
            </div>

            <div className="flex items-center justify-center space-x-10 py-4">
              <div className="flex flex-col items-center">
                <span className="text-sm text-gray-500 mb-1">Risk Score</span>
                <span className={`text-6xl font-black ${getScoreColor(result.risk_band)}`}>
                  {parseFloat(result.risk_score).toFixed(1)}%
                </span>
              </div>
              <div className="h-16 w-px bg-gray-200" />
              <div className="flex flex-col items-center space-y-2">
                <span className="text-sm text-gray-500">Risk Band</span>
                <RiskBadge riskBand={result.risk_band} size="md" />
              </div>
            </div>
          </div>

          {/* Drivers */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6">
            <h3 className="text-base font-semibold text-ns-navy mb-4 border-b pb-2">
              Top 3 Risk Drivers
            </h3>
            <div className="space-y-3">
              {(result.drivers || []).map((driver, idx) => (
                <DriverCard
                  key={idx}
                  label={driver.label}
                  value={driver.value}
                  explanation={driver.explanation}
                  category={driver.category}
                  riskBand={result.risk_band}
                />
              ))}
            </div>
          </div>

          <AiInsightsPanel
            patientId={result.patient_id}
            riskScore={result.risk_score}
            riskBand={result.risk_band}
            drivers={result.drivers}
          />

          {/* Save / navigation */}
          <div className="bg-white rounded-xl border border-gray-200 shadow-sm p-6 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div>
              <p className="font-medium text-gray-800">Add this patient to the Dashboard?</p>
              <p className="text-sm text-gray-500 mt-0.5">
                They will appear in the main worklist with the current batch date.
              </p>
              {saveError && (
                <p className="text-sm text-red-600 mt-1">{saveError}</p>
              )}
              {saved && (
                <p className="text-sm text-green-600 font-medium mt-1 flex items-center gap-1">
                  <CheckCircle size={14} /> Patient added to the worklist.
                </p>
              )}
            </div>
            <div className="flex items-center space-x-3">
              <button
                type="button"
                onClick={handleReset}
                className="px-4 py-2 text-sm font-medium border border-gray-300 rounded-lg text-gray-600 hover:bg-gray-50 transition-colors"
              >
                New Entry
              </button>
              {saved ? (
                <button
                  type="button"
                  onClick={() => navigate('/')}
                  className="group px-5 py-2 bg-ns-navy text-white rounded-lg text-sm font-semibold hover:bg-blue-900 transition-colors flex items-center space-x-2"
                >
                  <span>View Dashboard</span>
                  <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
                </button>
              ) : (
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={saving}
                  className="px-5 py-2 bg-ns-navy text-white rounded-lg text-sm font-semibold hover:bg-blue-900 transition-colors flex items-center space-x-2 disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {saving ? (
                    <>
                      <Loader2 size={16} className="animate-spin" />
                      <span>Saving...</span>
                    </>
                  ) : (
                    <span>Add to Dashboard</span>
                  )}
                </button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
