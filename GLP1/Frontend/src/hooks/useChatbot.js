import { useCallback, useEffect, useState } from 'react';
import { api } from '../data/api';
import { useRole } from '../context/RoleContext';

const SESSION_KEY = 'glp1_chatbot_session_id';

function loadSessionId() {
  try {
    return sessionStorage.getItem(SESSION_KEY) || null;
  } catch {
    return null;
  }
}

function saveSessionId(id) {
  try {
    if (id) sessionStorage.setItem(SESSION_KEY, id);
  } catch {
    /* ignore */
  }
}

function clearSessionId() {
  try {
    sessionStorage.removeItem(SESSION_KEY);
  } catch {
    /* ignore */
  }
}

export function useChatbot() {
  const { role } = useRole();
  const [messages, setMessages] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [sessionId, setSessionId] = useState(loadSessionId);

  useEffect(() => {
    if (!sessionId) return;
    let cancelled = false;
    api.getChatSession(sessionId)
      .then((data) => {
        if (cancelled) return;
        const restored = (data?.messages || []).map((m, i) => ({
          id: `restored-${i}`,
          role: m.role,
          content: m.content,
          toolCalls: [],
        }));
        if (restored.length) setMessages(restored);
      })
      .catch(() => {
        clearSessionId();
        setSessionId(null);
      });
    return () => {
      cancelled = true;
    };
  }, [sessionId]);

  const sendMessage = useCallback(async (text) => {
    const trimmed = (text || '').trim();
    if (!trimmed || loading) return;

    const userMsg = { id: `u-${Date.now()}`, role: 'user', content: trimmed, toolCalls: [] };
    setMessages((prev) => [...prev, userMsg]);
    setLoading(true);
    setError(null);

    try {
      const payload = {
        messages: [{ role: 'user', content: trimmed }],
        session_id: sessionId || undefined,
        role_context: role,
      };
      const data = await api.postChatMessage(payload);
      if (data?.session_id && data.session_id !== sessionId) {
        setSessionId(data.session_id);
        saveSessionId(data.session_id);
      }
      const botMsg = {
        id: `a-${Date.now()}`,
        role: 'assistant',
        content: data?.reply || '(No response.)',
        toolCalls: data?.tool_calls || [],
      };
      setMessages((prev) => [...prev, botMsg]);
      if (data?.error) setError(data.error);
    } catch (err) {
      const errorMsg = {
        id: `e-${Date.now()}`,
        role: 'assistant',
        content: "I couldn't reach the assistant — check that the backend is running and try again.",
        toolCalls: [],
        isError: true,
      };
      setMessages((prev) => [...prev, errorMsg]);
      setError(err?.message || 'Network error');
    } finally {
      setLoading(false);
    }
  }, [loading, sessionId, role]);

  const clearHistory = useCallback(async () => {
    const currentId = sessionId;
    setMessages([]);
    setError(null);
    setSessionId(null);
    clearSessionId();
    if (currentId) {
      try { await api.clearChatSession(currentId); } catch { /* ignore */ }
    }
  }, [sessionId]);

  return { messages, loading, error, sendMessage, clearHistory };
}
