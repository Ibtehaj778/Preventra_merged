import { useEffect, useRef } from 'react';
import Message from './Message';
import SuggestedPrompts from './SuggestedPrompts';

export default function MessageList({ messages, loading, onSuggest }) {
  const endRef = useRef(null);

  useEffect(() => {
    if (endRef.current) {
      endRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [messages.length, loading]);

  if (messages.length === 0 && !loading) {
    return <SuggestedPrompts onPick={onSuggest} />;
  }

  return (
    <div className="flex flex-col gap-3 px-3 py-3">
      {messages.map((m) => (
        <Message key={m.id} message={m} />
      ))}
      {loading && (
        <div className="flex justify-start animate-fade-in">
          <div className="bg-slate-100 text-slate-500 rounded-2xl rounded-bl-sm px-3.5 py-2.5 text-[13px] shadow-sm">
            <span className="inline-flex items-center gap-1">
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse" />
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse" style={{ animationDelay: '150ms' }} />
              <span className="w-1.5 h-1.5 rounded-full bg-slate-400 animate-pulse" style={{ animationDelay: '300ms' }} />
              <span className="ml-1.5">thinking…</span>
            </span>
          </div>
        </div>
      )}
      <div ref={endRef} />
    </div>
  );
}
