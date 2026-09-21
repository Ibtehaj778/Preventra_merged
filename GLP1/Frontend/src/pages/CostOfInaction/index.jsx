import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, Activity, DollarSign, Stethoscope } from 'lucide-react';
import { useRole } from '../../context/RoleContext';
import DownstreamCostPanel from './DownstreamCostPanel';
import ReboundRiskPanel from './ReboundRiskPanel';
import PayerROIPanel from './PayerROIPanel';

const SUB_NAV = [
  { id: 'downstream', label: 'Downstream Cost',  icon: DollarSign },
  { id: 'rebound',    label: 'Metabolic Rebound', icon: Activity },
  { id: 'roi',        label: 'Payer ROI',         icon: AlertTriangle },
];

export default function CostOfInaction() {
  const { isInsurer } = useRole();
  const [active, setActive] = useState('downstream');
  const refs = useRef({});

  // Scroll-spy: update `active` when a panel scrolls into view.
  useEffect(() => {
    const observer = new IntersectionObserver(
      entries => {
        entries.forEach(e => {
          if (e.isIntersecting) setActive(e.target.dataset.panel);
        });
      },
      { rootMargin: '-30% 0px -60% 0px', threshold: 0 }
    );
    Object.values(refs.current).forEach(el => el && observer.observe(el));
    return () => observer.disconnect();
  }, []);

  const scrollTo = (id) => {
    const el = refs.current[id];
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  return (
    <div className="max-w-[1200px] mx-auto space-y-5 animate-fade-in">
      {/* Clinician view banner */}
      {!isInsurer && (
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-2 sm:gap-3 px-4 py-3 rounded-xl text-sm font-medium animate-fade-up"
          style={{ background: '#F0FFF4', color: '#2E7D32', border: '1px solid #C8E6C9' }}>
          <span className="flex items-center gap-2.5">
            <Stethoscope size={15} />
            Clinician View — This screen is designed for Insurer/Payer financial planning. All tools remain accessible.
          </span>
          <div className="flex flex-wrap items-center gap-3 text-xs font-semibold flex-shrink-0">
            <Link to="/patients" className="hover:underline underline-offset-2" style={{ color: '#2E7D32' }}>Patient Risk Panel →</Link>
            <Link to="/"         className="hover:underline underline-offset-2" style={{ color: '#2E7D32' }}>Executive Summary →</Link>
          </div>
        </div>
      )}

      {/* Framing banner */}
      <div className="card p-5" style={{ background: 'linear-gradient(135deg, #FFF9F0, #FFF3E0)', borderColor: '#FFE0B2' }}>
        <div className="flex items-start gap-4">
          <div className="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
               style={{ background: '#EF6C00' }}>
            <AlertTriangle size={18} color="white" />
          </div>
          <div className="flex-1">
            <div className="text-xs font-bold uppercase tracking-wider mb-1" style={{ color: '#EF6C00' }}>
              Cost of Inaction
            </div>
            <div className="font-display text-lg font-semibold text-gray-800 mb-1">
              What happens when patients drop off GLP-1 therapy?
            </div>
            <div className="text-sm text-gray-600 leading-relaxed">
              Three views on the downstream consequences of non-adherence:
              medical spend the payer absorbs when a patient drops out,
              the metabolic rebound trajectory of each risk cluster,
              and the ROI the payer earns by keeping patients on therapy.
              All numbers derive from the Phase 1–3 consequence model.
            </div>
          </div>
        </div>
      </div>

      {/* Sticky sub-nav */}
      <div className="sticky top-0 z-10 -mx-4 px-4 lg:-mx-6 lg:px-6 py-2"
           style={{ background: 'var(--bg-canvas)', borderBottom: '1px solid var(--border)' }}>
        <div className="flex items-center gap-1 overflow-x-auto">
          {SUB_NAV.map(({ id, label, icon: Icon }) => (
            <button key={id} onClick={() => scrollTo(id)}
              className="flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold transition-all whitespace-nowrap flex-shrink-0"
              style={{
                background: active === id ? 'var(--color-primary)' : 'transparent',
                color:      active === id ? 'white' : 'var(--text-secondary)',
              }}>
              <Icon size={13} />
              {label}
            </button>
          ))}
        </div>
      </div>

      {/* Panel sections */}
      <div ref={el => refs.current.downstream = el} data-panel="downstream" className="scroll-mt-16">
        <DownstreamCostPanel />
      </div>
      <div ref={el => refs.current.rebound = el}    data-panel="rebound"    className="scroll-mt-16">
        <ReboundRiskPanel />
      </div>
      <div ref={el => refs.current.roi = el}        data-panel="roi"        className="scroll-mt-16">
        <PayerROIPanel />
      </div>
    </div>
  );
}
