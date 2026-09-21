import { useState } from 'react';
import { Send } from 'lucide-react';

const MAX_LEN = 2000;

export default function MessageInput({ onSend, disabled }) {
  const [value, setValue] = useState('');

  const submit = () => {
    const text = value.trim();
    if (!text || disabled) return;
    onSend(text);
    setValue('');
  };

  const onKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit();
    }
  };

  const remaining = MAX_LEN - value.length;
  const nearLimit = remaining < 100;

  return (
    <div className="border-t border-slate-200 bg-white px-3 py-2.5">
      <div className="flex items-end gap-2">
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value.slice(0, MAX_LEN))}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Ask about the data…"
          disabled={disabled}
          className="flex-1 resize-none rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-[13.5px] leading-snug focus:outline-none focus:border-[var(--color-primary-light)] focus:bg-white transition disabled:opacity-60 max-h-32"
          style={{ minHeight: '38px' }}
        />
        <button
          type="button"
          onClick={submit}
          disabled={disabled || !value.trim()}
          className="shrink-0 w-9 h-9 rounded-xl bg-[var(--color-primary)] text-white flex items-center justify-center hover:bg-[var(--color-primary-light)] transition disabled:opacity-40 disabled:cursor-not-allowed"
          aria-label="Send message"
        >
          <Send size={16} />
        </button>
      </div>
      {nearLimit && (
        <div className={`text-[10.5px] mt-1 text-right ${remaining < 0 ? 'text-red-600' : 'text-slate-500'}`}>
          {remaining} chars left
        </div>
      )}
    </div>
  );
}
