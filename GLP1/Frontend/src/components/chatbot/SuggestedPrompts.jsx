import { Sparkles } from 'lucide-react';

const PROMPTS = [
  'Which segment has the highest dropout?',
  'What is the ROI at $500 intervention with 15% adherence uplift?',
  'Tell me about patient 42',
  'Why is cluster 1 at high risk?',
];

export default function SuggestedPrompts({ onPick }) {
  return (
    <div className="px-4 py-6 flex flex-col items-center text-center gap-3">
      <div className="w-11 h-11 rounded-full bg-[var(--color-primary)]/10 text-[var(--color-primary)] flex items-center justify-center">
        <Sparkles size={22} />
      </div>
      <div>
        <div className="text-[14px] font-semibold text-slate-800">Ask the analytics assistant</div>
        <div className="text-[12px] text-slate-500 mt-0.5 leading-relaxed">
          Plain-language questions about anything on the dashboard — patients, segments, ROI, cost of inaction.
        </div>
      </div>
      <div className="flex flex-col gap-1.5 w-full mt-1">
        {PROMPTS.map((p) => (
          <button
            key={p}
            type="button"
            onClick={() => onPick?.(p)}
            className="text-left text-[12.5px] text-slate-700 bg-slate-50 hover:bg-slate-100 border border-slate-200 rounded-lg px-3 py-2 transition"
          >
            {p}
          </button>
        ))}
      </div>
    </div>
  );
}
