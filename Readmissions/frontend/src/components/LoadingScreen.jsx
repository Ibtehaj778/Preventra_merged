import React from 'react';

/**
 * The opening screen while the first requests come back - Readmissions' twin
 * of GLP-1's LoadingScreen, in Preventra's navy. See hooks/useAppLoader.js.
 */
export default function LoadingScreen({ progress = 0, status = 'Loading…' }) {
  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center"
      style={{ background: 'linear-gradient(135deg, #07162A 0%, #0F2A4A 55%, #1B4F8A 100%)' }}
      role="status"
      aria-live="polite"
    >
      <div className="flex w-full max-w-sm flex-col items-center gap-6 px-8">
        {/* Shield mark */}
        <div className="relative">
          <div
            className="flex h-16 w-16 animate-pulse items-center justify-center rounded-2xl shadow-2xl"
            style={{ background: 'rgba(255,255,255,0.08)', backdropFilter: 'blur(8px)' }}
          >
            <img src="/logo-mark.png" alt="" className="h-9 w-auto" />
          </div>
          <div
            className="pointer-events-none absolute inset-0 rounded-2xl"
            style={{ boxShadow: '0 0 60px 8px rgba(255,255,255,0.15)' }}
          />
        </div>

        {/* Title */}
        <div className="text-center">
          <h1 className="text-2xl font-semibold tracking-tight text-white">Readmission Risk</h1>
          <p className="mt-1 text-xs uppercase tracking-widest text-white/50">
            Preventra · Discharge risk & monitoring
          </p>
        </div>

        {/* Progress bar */}
        <div className="mt-2 w-full">
          <div className="h-1 overflow-hidden rounded-full" style={{ background: 'rgba(255,255,255,0.1)' }}>
            <div
              className="h-full rounded-full transition-all duration-500 ease-out"
              style={{
                width: `${Math.max(5, progress)}%`,
                background: 'linear-gradient(90deg, #60A5FA, #93C5FD)',
                boxShadow: '0 0 12px rgba(96,165,250,0.6)',
              }}
            />
          </div>
          <div className="mt-3 flex items-center justify-between">
            <span className="text-xs font-medium text-white/60">{status}</span>
            <span className="font-mono text-xs text-white/40">{Math.round(progress)}%</span>
          </div>
        </div>
      </div>
    </div>
  );
}
