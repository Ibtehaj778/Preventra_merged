import { RotateCcw, X } from 'lucide-react';
import MessageInput from './MessageInput';
import MessageList from './MessageList';
import { useChatbot } from '../../hooks/useChatbot';

export default function ChatPanel({ onClose }) {
  const { messages, loading, sendMessage, clearHistory } = useChatbot();

  return (
    <div
      className="fixed bottom-24 right-6 z-50 w-[380px] max-w-[calc(100vw-2rem)] h-[560px] max-h-[calc(100vh-8rem)] bg-white rounded-2xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-fade-in"
      role="dialog"
      aria-label="Analytics assistant"
    >
      <div className="flex items-center justify-between px-4 py-3 border-b border-slate-200 bg-[var(--color-primary-dark)] text-white">
        <div>
          <div className="text-[14px] font-semibold leading-tight">Analytics Assistant</div>
          <div className="text-[11px] text-white/70 leading-tight">Ask about the GLP-1 dashboard</div>
        </div>
        <div className="flex items-center gap-1">
          {messages.length > 0 && (
            <button
              type="button"
              onClick={clearHistory}
              title="Clear conversation"
              className="w-7 h-7 rounded-lg text-white/80 hover:text-white hover:bg-white/10 flex items-center justify-center transition"
            >
              <RotateCcw size={14} />
            </button>
          )}
          <button
            type="button"
            onClick={onClose}
            title="Close"
            className="w-7 h-7 rounded-lg text-white/80 hover:text-white hover:bg-white/10 flex items-center justify-center transition"
          >
            <X size={16} />
          </button>
        </div>
      </div>
      <div className="flex-1 overflow-y-auto bg-white">
        <MessageList messages={messages} loading={loading} onSuggest={sendMessage} />
      </div>
      <MessageInput onSend={sendMessage} disabled={loading} />
    </div>
  );
}
