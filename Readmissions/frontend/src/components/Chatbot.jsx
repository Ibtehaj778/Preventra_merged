import React, { useEffect, useRef, useState } from 'react';
import { MessageCircle, X, Send, Loader2 } from 'lucide-react';
import { askChatbot } from '../api';

const FRIENDLY_ERROR = "Sorry, I couldn't process that question. Please try again.";

// How much of the conversation to send back with each question. The backend
// trims to the same order of magnitude; keeping it short here means a long
// session does not grow the request without bound.
const HISTORY_TURNS = 8;

export default function Chatbot() {
  const [open, setOpen] = useState(false);
  const [question, setQuestion] = useState('');
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const historyRef = useRef(null);

  useEffect(() => {
    if (historyRef.current) {
      historyRef.current.scrollTop = historyRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = async (e) => {
    e.preventDefault();
    const trimmed = question.trim();
    if (!trimmed || loading) return;

    setQuestion('');
    setLoading(true);
    // Snapshot the transcript before this question is appended: the backend
    // receives the question separately, and sending it twice reads as the user
    // having asked it already.
    const history = messages
      .filter((m) => !m.isError)
      .slice(-HISTORY_TURNS)
      .map(({ role, text }) => ({ role, text }));
    setMessages((prev) => [...prev, { role: 'user', text: trimmed }]);

    try {
      const { answer } = await askChatbot(trimmed, history);
      setMessages((prev) => [...prev, { role: 'bot', text: answer || FRIENDLY_ERROR }]);
    } catch {
      setMessages((prev) => [...prev, { role: 'bot', text: FRIENDLY_ERROR, isError: true }]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      {open && (
        <div className="fixed inset-x-3 bottom-24 z-[60] flex h-[70dvh] flex-col overflow-hidden rounded-2xl border border-gray-200 bg-white shadow-2xl sm:inset-x-auto sm:right-6 sm:h-[520px] sm:max-h-[calc(100dvh-8rem)] sm:w-[380px]">
          {/* Header */}
          <div className="bg-ns-navy px-5 py-4 flex items-center justify-between shrink-0">
            <div>
              <h2 className="text-white font-semibold text-base leading-tight">NeuroShield Assistant</h2>
              <p className="text-white/60 text-xs mt-0.5">Ask about patient risk data</p>
            </div>
            <button
              onClick={() => setOpen(false)}
              className="text-white/70 hover:text-white hover:bg-white/10 rounded-full p-1.5 transition-colors"
              aria-label="Close chat"
            >
              <X size={18} />
            </button>
          </div>

          {/* Message history */}
          <div ref={historyRef} className="flex-1 overflow-y-auto px-4 py-4 space-y-3 bg-gray-50">
            {messages.length === 0 && (
              <div className="text-sm text-gray-500 text-center mt-8 px-4">
                Try asking: "How many patients are high risk?", "What is the primary diagnosis of the top 5 patients?" or "What drives readmission after heart failure?"
              </div>
            )}
            {messages.map((msg, idx) => (
              <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                <div
                  className={`max-w-[85%] rounded-2xl px-4 py-2.5 text-sm whitespace-pre-wrap leading-relaxed ${
                    msg.role === 'user'
                      ? 'bg-ns-navy text-white rounded-br-sm'
                      : msg.isError
                      ? 'bg-red-50 text-red-700 border border-red-200 rounded-bl-sm'
                      : 'bg-white text-gray-800 border border-gray-200 rounded-bl-sm'
                  }`}
                >
                  {msg.text}
                </div>
              </div>
            ))}
            {loading && (
              <div className="flex justify-start">
                <div className="bg-white border border-gray-200 rounded-2xl rounded-bl-sm px-4 py-2.5 flex items-center gap-2 text-gray-400">
                  <Loader2 size={16} className="animate-spin" />
                  <span className="text-sm">Thinking…</span>
                </div>
              </div>
            )}
          </div>

          {/* Input */}
          <form onSubmit={handleSend} className="border-t border-gray-200 p-3 flex items-center gap-2 shrink-0 bg-white">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question…"
              disabled={loading}
              className="flex-1 text-sm border border-gray-300 rounded-full px-4 py-2 focus:outline-none focus:ring-2 focus:ring-ns-navy/40 disabled:bg-gray-100"
            />
            <button
              type="submit"
              disabled={loading || !question.trim()}
              className="bg-ns-navy text-white rounded-full p-2.5 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-ns-navy/90 transition-colors shrink-0"
              aria-label="Send question"
            >
              <Send size={16} />
            </button>
          </form>
        </div>
      )}

      {/* Floating toggle button */}
      <button
        onClick={() => setOpen((v) => !v)}
        className="fixed bottom-6 right-6 z-[60] bg-ns-navy hover:bg-ns-navy/90 text-white rounded-full p-4 shadow-xl transition-colors"
        aria-label={open ? 'Close chat' : 'Open chat'}
      >
        {open ? <X size={24} /> : <MessageCircle size={24} />}
      </button>
    </>
  );
}
