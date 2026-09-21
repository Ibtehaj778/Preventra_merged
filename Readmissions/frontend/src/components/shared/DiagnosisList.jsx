import React from 'react';
import { Stethoscope } from 'lucide-react';

/**
 * Every diagnosis recorded for an admission, principal first.
 *
 * WHY THIS IS NOT THE WORKLIST CELL
 * ---------------------------------
 * The worklist shows one row per patient and has to stay a table, so it folds
 * the secondary diagnoses behind an expander. This is the record a coordinator
 * opens to decide what to do about someone, so nothing is folded: the full
 * list renders, and the count of what the extract could not carry is stated
 * rather than left as a silent gap.
 *
 * Conditions that place the patient in a monitoring group are tagged, because
 * a stay admitted for liver disease can be monitored as heart failure and the
 * reason should be visible on the record instead of inferred.
 */
export default function DiagnosisList({ patient }) {
  const list = patient?.diagnoses?.length
    ? patient.diagnoses
    : [{
        position: 'principal',
        code: patient?.primary_icd_code || '',
        title: patient?.primary_diagnosis || '',
        group: '',
        group_label: '',
      }];

  const coded = patient?.n_diagnoses_coded || 0;
  const notCarried = Math.max(coded - list.length, 0);
  const hasSecondary = list.some((d) => d.position === 'secondary');

  return (
    <div>
      <h3 className="text-lg font-semibold text-ns-navy mb-4 border-b pb-2 flex items-center justify-between">
        <span>Diagnoses</span>
        {coded > 0 && (
          <span className="text-xs font-normal text-gray-400">
            {list.length} of {coded} coded
          </span>
        )}
      </h3>

      <div className="bg-white rounded-xl border border-gray-200 shadow-sm divide-y divide-gray-100">
        {list.map((d, i) => (
          <div key={`${d.title}-${i}`} className="p-3.5 flex items-start gap-3">
            {/* Sequence position is real information: the principal diagnosis
                is what the stay was coded as being for. */}
            <span className="mt-0.5 shrink-0 text-[10px] font-semibold uppercase tracking-wide text-gray-400 w-14">
              {d.position === 'principal' ? 'Primary' : `Sec ${i}`}
            </span>

            <div className="min-w-0 flex-1">
              <div className="text-sm text-gray-800 leading-snug">
                {d.title || <span className="text-gray-400 italic">not coded</span>}
              </div>

              <div className="flex flex-wrap items-center gap-1.5 mt-1">
                {d.code && (
                  <span className="text-[11px] font-mono text-gray-500 bg-gray-100 rounded px-1.5 py-px">
                    ICD {d.code}
                  </span>
                )}
                {d.group_label && (
                  <span className="inline-flex items-center gap-1 text-[11px] text-ns-navy bg-ns-navy/5 border border-ns-navy/15 rounded px-1.5 py-px">
                    <Stethoscope size={10} />
                    {d.group_label}
                  </span>
                )}
              </div>
            </div>
          </div>
        ))}
      </div>

      {patient?.group_label && patient.clinical_group !== 'general' && (
        <p className="text-xs text-gray-500 mt-2.5 leading-relaxed">
          Monitored as <span className="font-semibold text-ns-navy">{patient.group_label}</span>
          {patient.group_evidence && <> — {patient.group_evidence}</>}
          {patient.group_confidence === 'moderate' && (
            <span className="text-gray-400"> (matched on the diagnosis text, not a code)</span>
          )}
        </p>
      )}

      {/* Stated once, not badged on every row - and only when there is
          actually a secondary to qualify. */}
      {(hasSecondary || notCarried > 0) && (
        <p className="text-xs text-gray-400 mt-1.5 leading-relaxed">
          {hasSecondary && 'Secondary diagnoses are carried as text without their ICD codes.'}
          {notCarried > 0 && (
            <>{hasSecondary ? ' ' : ''}{notCarried} further{' '}
            {notCarried === 1 ? 'diagnosis was' : 'diagnoses were'} coded for this stay but{' '}
            {notCarried === 1 ? 'is' : 'are'} not in the extract.</>
          )}
        </p>
      )}
    </div>
  );
}
