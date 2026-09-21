import { useState, useEffect, useRef } from 'react';
import * as Slider from '@radix-ui/react-slider';
import { Building2 } from 'lucide-react';
import { SectionHeader } from '../../components/shared';
import { SkeletonChart } from '../../components/shared/LoadingSkeleton';
import ROIBarChart from '../../components/charts/ROIBarChart';
import ROITrajectoryChart from '../../components/charts/ROITrajectoryChart';
import { usePayerROI } from '../../hooks/usePayerROI';
import { DEMO_POST_GENERIC_MODE } from '../../data/config';

const fmtMoney = (n) => {
  if (!Number.isFinite(n)) return '—';
  const abs = Math.abs(n);
  const sign = n < 0 ? '-' : '';
  if (abs >= 1e6) return `${sign}$${(abs / 1e6).toFixed(2)}M`;
  if (abs >= 1e3) return `${sign}$${(abs / 1e3).toFixed(1)}K`;
  return `${sign}$${Math.round(abs)}`;
};
const fmtPct  = (n) => Number.isFinite(n) ? `${(n * 100).toFixed(1)}%` : '—';
const fmtROIx = (n) => Number.isFinite(n) ? `${n.toFixed(2)}×` : '—';
const fmtInt  = (n) => Number.isFinite(n) ? Math.round(n).toLocaleString() : '—';

const PAYER_SCENARIOS = [
  { id: 'current',       label: 'Current (2025)' },
  { id: 'medicare_2028', label: 'Medicare 2028'  },
  { id: 'post_generic',  label: 'Post-generic 2032+' },
];

const ROI_FIELD = 'intervention_roi_net';

// Dark hero palette
const HERO_BG        = '#0A1F3D';
const HERO_ACCENT    = '#5EEAD4';
const HERO_NEGATIVE  = '#FCA5A5';
const HERO_LABEL     = 'rgba(255,255,255,0.5)';
const HERO_MUTED     = 'rgba(255,255,255,0.7)';
const HERO_DIVIDER   = 'rgba(255,255,255,0.08)';

/**
 * Smoothly count from the current displayed value to `target`.
 * Uses easeOutCubic. Returns the intermediate value; the component formats it.
 */
function useCountUp(target, duration = 700) {
  const [value, setValue] = useState(Number.isFinite(target) ? 0 : target);
  const currentRef = useRef(0);

  useEffect(() => {
    if (!Number.isFinite(target)) {
      setValue(target);
      return;
    }
    const from  = currentRef.current;
    const start = performance.now();
    let raf;
    const step = (t) => {
      const p = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - p, 3);
      const cur = from + (target - from) * eased;
      currentRef.current = cur;
      setValue(cur);
      if (p < 1) raf = requestAnimationFrame(step);
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [target, duration]);

  return value;
}

/**
 * Premium slider for the dark hero band — teal range, white thumb, muted labels.
 */
function ControlSlider({ label, value, valueDisplay, onChange, min, max, step, ticks }) {
  return (
    <div className="flex flex-col gap-3">
      <div className="flex items-baseline justify-between">
        <span className="text-[11px] uppercase tracking-[0.14em] font-medium" style={{ color: HERO_LABEL }}>{label}</span>
        <span className="font-display text-lg text-white tabular-nums">{valueDisplay}</span>
      </div>
      <Slider.Root
        className="relative flex items-center select-none touch-none w-full h-5"
        min={min} max={max} step={step}
        value={[value]}
        onValueChange={([v]) => onChange(v)}
      >
        <Slider.Track className="relative grow h-[3px] rounded-full" style={{ background: 'rgba(255,255,255,0.12)' }}>
          <Slider.Range className="absolute h-full rounded-full transition-colors" style={{ background: HERO_ACCENT }} />
        </Slider.Track>
        <Slider.Thumb
          className="block w-4 h-4 rounded-full focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-offset-transparent transition-transform hover:scale-110"
          style={{
            background: '#FFFFFF',
            border: `2px solid ${HERO_ACCENT}`,
            boxShadow: `0 0 0 3px rgba(94,234,212,0.15), 0 2px 6px rgba(0,0,0,0.4)`,
          }}
          aria-label={label}
        />
      </Slider.Root>
      <div className="flex justify-between text-[10px] tabular-nums font-medium" style={{ color: 'rgba(255,255,255,0.35)' }}>
        {ticks.map((t, i) => <span key={i}>{t}</span>)}
      </div>
    </div>
  );
}

export default function PayerROIPanel() {
  const [interventionCost, setInterventionCost] = useState(500);
  const [payerType,        setPayerType]        = useState(DEMO_POST_GENERIC_MODE ? 'post_generic' : 'current');
  const [adherenceUplift,  setAdherenceUplift]  = useState(0.15);
  const { data, loading, error } = usePayerROI(interventionCost, payerType, adherenceUplift);

  const clusters    = data?.by_cluster ?? [];
  const nTotal      = data?.n_patients_total ?? 0;
  const pop5        = data?.population_intervention_roi_net_5yr;
  const pop10       = data?.population_intervention_roi_net_10yr;
  const avgDrugCost = clusters.length
    ? clusters.reduce((s, c) => s + c.avg_annual_drug_cost, 0) / clusters.length
    : null;

  const heroCU = useCountUp(Number.isFinite(pop10)        ? pop10        : 0);
  const pop5CU = useCountUp(Number.isFinite(pop5)         ? pop5         : 0);
  const drugCU = useCountUp(Number.isFinite(avgDrugCost)  ? avgDrugCost  : 0);
  const ptsCU  = useCountUp(nTotal);

  const heroColor = pop10 >= 0 ? HERO_ACCENT : HERO_NEGATIVE;

  if (error) {
    return (
      <div className="card p-6">
        <SectionHeader title="Payer ROI" />
        <div className="text-sm text-red-600">
          Failed to load payer ROI data. Check the backend is running.
        </div>
      </div>
    );
  }

  const heroValue = loading && !data ? '—' : fmtROIx(heroCU);

  return (
    <div className="space-y-5">
      {/* ═══ Main card ════════════════════════════════════════════════════ */}
      <div className="card overflow-hidden p-0 animate-fade-up">

        {/* ── Top row: dark hero (left) + dark sliders (right) ─────────── */}
        <div className="grid grid-cols-1 lg:grid-cols-12" style={{ background: HERO_BG }}>

          {/* Hero panel */}
          <div className="lg:col-span-5 px-5 py-6 sm:px-8 sm:py-9 flex flex-col border-b lg:border-b-0 lg:border-r"
               style={{ borderColor: HERO_DIVIDER }}>
            <div>
              <h2 className="font-display text-lg font-semibold text-white leading-tight">Payer ROI</h2>
              <p className="text-xs mt-1 leading-relaxed" style={{ color: HERO_MUTED }}>
                Net return on adherence program spend — medical savings minus extra drug cost, per $1 invested.
              </p>
            </div>

            {!DEMO_POST_GENERIC_MODE && (
              <div className="mt-4 flex items-center gap-2">
                <Building2 size={12} style={{ color: HERO_LABEL }} />
                <div className="flex items-center rounded-lg p-0.5" style={{ background: 'rgba(255,255,255,0.06)' }}>
                  {PAYER_SCENARIOS.map(s => (
                    <button key={s.id} onClick={() => setPayerType(s.id)}
                      className="px-2.5 py-1 rounded-md text-[10px] font-semibold transition-all"
                      style={{
                        background: payerType === s.id ? 'rgba(255,255,255,0.12)' : 'transparent',
                        color:      payerType === s.id ? 'white' : HERO_LABEL,
                      }}>
                      {s.label}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {/* Hero metric */}
            <div className="mt-8 animate-fade-up" style={{ animationDelay: '0.08s' }}>
              <div className="text-[10px] uppercase tracking-[0.18em] font-semibold mb-4" style={{ color: HERO_LABEL }}>
                10-year population Net ROI
              </div>
              <div className="flex items-baseline gap-3">
                <span className="font-display font-semibold leading-none tabular-nums transition-colors"
                      style={{ color: heroColor, fontSize: 'clamp(2.5rem, 10vw, 4rem)' }}>
                  {heroValue}
                </span>
                <span className="text-[11px] font-medium leading-relaxed" style={{ color: HERO_MUTED }}>
                  on every $1<br />of program spend
                </span>
              </div>
            </div>

            {/* Supporting stats */}
            <div className="mt-8 pt-6 grid grid-cols-3 gap-4 animate-fade-up"
                 style={{ borderTop: `1px solid ${HERO_DIVIDER}`, animationDelay: '0.16s' }}>
              <DarkStat label="5-yr ROI"    value={loading && !data ? '—' : fmtROIx(pop5CU)}  color={pop5 >= 0 ? HERO_ACCENT : HERO_NEGATIVE} />
              <DarkStat label="Avg drug/yr" value={loading && !data ? '—' : fmtMoney(drugCU)} color="#FFFFFF" />
              <DarkStat label="Patients"    value={loading && !data ? '—' : fmtInt(ptsCU)}    color="#FFFFFF" />
            </div>
          </div>

          {/* Sliders panel — same dark bg */}
          <div className="lg:col-span-7 px-5 py-6 sm:px-10 sm:py-9 flex flex-col justify-center gap-7 sm:gap-9 animate-fade-up"
               style={{ animationDelay: '0.24s' }}>

            <ControlSlider
              label="Program cost per patient"
              value={interventionCost}
              valueDisplay={<>{fmtMoney(interventionCost)}<span className="text-xs font-normal ml-1" style={{ color: HERO_LABEL }}>/ yr</span></>}
              onChange={setInterventionCost}
              min={0} max={3000} step={50}
              ticks={['$0', '$1.5K', '$3K']}
            />
            <ControlSlider
              label="Adherence uplift from program"
              value={adherenceUplift}
              valueDisplay={<>+{fmtPct(adherenceUplift)}<span className="text-xs font-normal ml-1" style={{ color: HERO_LABEL }}>of patients</span></>}
              onChange={setAdherenceUplift}
              min={0} max={0.5} step={0.01}
              ticks={['0%', '+25%', '+50%']}
            />
          </div>
        </div>

        {/* ── Full-width bar chart section ─────────────────────────────── */}
        <div className="px-5 py-6 sm:px-8 sm:py-8 border-t border-gray-100">
          <div className="mb-4 animate-fade-up" style={{ animationDelay: '0.32s' }}>
            <div className="text-sm font-semibold text-gray-900">Net ROI by cluster</div>
            <div className="text-[11px] text-gray-400 mt-0.5">At 1, 3, 5, and 10-year horizons</div>
          </div>
          <div className="animate-fade-up" style={{ animationDelay: '0.4s' }}>
            {loading && !data
              ? <SkeletonChart h={280} />
              : <ROIBarChart data={clusters} height={280} roiField={ROI_FIELD} />}
          </div>
        </div>
      </div>

      {/* ═══ Trajectory card ═══════════════════════════════════════════════ */}
      <div className="card p-8 animate-fade-up" style={{ animationDelay: '0.48s' }}>
        <div className="mb-6">
          <div className="text-sm font-semibold text-gray-900">10-year Net ROI trajectory</div>
          <div className="text-[11px] text-gray-400 mt-0.5">Per-year return by cluster — steeper slopes indicate faster payoff</div>
        </div>
        {loading && !data
          ? <SkeletonChart h={300} />
          : <ROITrajectoryChart data={clusters} height={300} roiField={ROI_FIELD} />}
      </div>
    </div>
  );
}

function DarkStat({ label, value, color }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-[0.14em] font-semibold mb-2" style={{ color: HERO_LABEL }}>{label}</div>
      <div className="font-display text-xl font-semibold tabular-nums leading-none transition-colors" style={{ color }}>
        {value}
      </div>
    </div>
  );
}
