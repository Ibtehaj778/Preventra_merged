import React, { useEffect, useRef, useState } from 'react';
import { Stethoscope, ChevronDown, X } from 'lucide-react';

/**
 * Filter the worklist by one or more conditions.
 *
 * WHY MULTI-SELECT
 * ----------------
 * 21.8% of the cohort has more than one of these conditions, and the counts
 * beside each option are membership counts - how many patients HAVE the
 * condition - so they sum to more than the cohort. That is intended: a patient
 * with heart failure and diabetes is one patient appearing in two conditions.
 *
 * `match` decides how several selections combine. "any" is the union, which is
 * what a ward list wants. "all" is the intersection, which is how you find
 * comorbidity - 24 patients have both heart failure and diabetes, and they are
 * a different clinical problem from the 691 who have either.
 */
export default function ConditionFilter({ groups, selected, match, onChange }) {
  const [open, setOpen] = useState(false);
  const ref = useRef(null);

  useEffect(() => {
    if (!open) return undefined;
    const onDown = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    const onKey = (e) => { if (e.key === 'Escape') setOpen(false); };
    document.addEventListener('mousedown', onDown);
    document.addEventListener('keydown', onKey);
    return () => {
      document.removeEventListener('mousedown', onDown);
      document.removeEventListener('keydown', onKey);
    };
  }, [open]);

  const toggle = (key) => {
    const next = selected.includes(key)
      ? selected.filter((k) => k !== key)
      : [...selected, key];
    onChange(next, match);
  };

  const label = selected.length === 0
    ? 'All conditions'
    : selected.length === 1
      ? (groups.find((g) => g.key === selected[0])?.label || selected[0])
      : `${selected.length} conditions`;

  return (
    <div className="flex items-center gap-2 text-sm" ref={ref}>
      <Stethoscope size={16} className="text-gray-400" />
      <span className="text-gray-500">Condition</span>

      <div className="relative">
        <button
          type="button"
          onClick={() => setOpen((o) => !o)}
          aria-expanded={open}
          aria-haspopup="listbox"
          className="flex items-center gap-2 border border-gray-300 rounded-lg px-2.5 py-1.5 text-sm text-gray-700 bg-white hover:border-ns-navy focus:outline-none focus:ring-2 focus:ring-ns-navy/30"
        >
          <span>{label}</span>
          {selected.length > 1 && (
            <span className="text-xs text-gray-400">{match === 'all' ? 'all of' : 'any of'}</span>
          )}
          <ChevronDown size={14} className="text-gray-400" />
        </button>

        {open && (
          <div
            role="listbox"
            className="absolute z-30 mt-1 w-72 bg-white border border-gray-200 rounded-xl shadow-lg p-1.5 max-h-96 overflow-y-auto"
          >
            {/* Only meaningful once two conditions are picked, so it appears then. */}
            {selected.length > 1 && (
              <div className="flex items-center gap-1 px-2 py-2 mb-1 border-b border-gray-100">
                <span className="text-xs text-gray-500 mr-1">Patient must have</span>
                {[['any', 'any of them'], ['all', 'all of them']].map(([value, text]) => (
                  <button
                    key={value}
                    type="button"
                    onClick={() => onChange(selected, value)}
                    className={`text-xs px-2 py-1 rounded-md transition-colors ${
                      match === value
                        ? 'bg-ns-navy text-white'
                        : 'text-gray-600 hover:bg-gray-100'
                    }`}
                  >
                    {text}
                  </button>
                ))}
              </div>
            )}

            <button
              type="button"
              onClick={() => onChange([], match)}
              className="w-full text-left px-2.5 py-1.5 rounded-lg text-sm text-gray-600 hover:bg-gray-50"
            >
              All conditions
            </button>

            {groups.map((g) => {
              const on = selected.includes(g.key);
              return (
                <button
                  key={g.key}
                  type="button"
                  role="option"
                  aria-selected={on}
                  onClick={() => toggle(g.key)}
                  className={`w-full flex items-center gap-2.5 px-2.5 py-1.5 rounded-lg text-sm text-left transition-colors ${
                    on ? 'bg-ns-navy/5' : 'hover:bg-gray-50'
                  }`}
                >
                  <span
                    aria-hidden
                    className={`w-4 h-4 shrink-0 rounded border flex items-center justify-center text-[10px] leading-none ${
                      on ? 'bg-ns-navy border-ns-navy text-white' : 'border-gray-300'
                    }`}
                  >
                    {on ? '✓' : ''}
                  </span>
                  <span className="flex-1 text-gray-700">{g.label}</span>
                  <span className="text-xs text-gray-400">{g.count}</span>
                </button>
              );
            })}
          </div>
        )}
      </div>

      {/* Chips, so a multi-condition filter stays visible and individually
          removable after the menu closes. With one selected the button
          already names it, so chips would just repeat it. */}
      {selected.length > 1 && selected.map((key) => (
        <button
          key={key}
          type="button"
          onClick={() => toggle(key)}
          title="Remove this condition"
          className="inline-flex items-center gap-1 text-xs bg-ns-navy/5 text-ns-navy border border-ns-navy/15 rounded-full pl-2.5 pr-1.5 py-1 hover:bg-ns-navy/10"
        >
          {groups.find((g) => g.key === key)?.label || key}
          <X size={12} />
        </button>
      ))}
    </div>
  );
}
