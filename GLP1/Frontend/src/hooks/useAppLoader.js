import { useEffect, useState } from 'react';
import { api } from '../data/api';

const STEPS = [
  { name: 'Loading summary metrics…',     fn: () => api.getSummary() },
  { name: 'Loading risk drivers…',         fn: () => api.getGlobalSHAP() },
  { name: 'Loading patient segments…',     fn: () => api.getSegments() },
  { name: 'Loading survival analysis…',    fn: () => api.getSurvival() },
  { name: 'Finalizing…',                   fn: () => Promise.resolve() },
];

const HARD_TIMEOUT_MS = 8000;
const MIN_DURATION_MS = 1500;

export function useAppLoader() {
  const [progress, setProgress] = useState(0);
  const [status, setStatus]     = useState(STEPS[0].name);
  const [ready, setReady]       = useState(false);

  useEffect(() => {
    const startedAt = Date.now();
    let cancelled = false;
    let completed = 0;

    const tick = () => {
      if (cancelled) return;
      completed += 1;
      // Cap visual progress at 95% until min duration elapses, so the bar
      // doesn't sit at 100% while we wait
      const realPct = (completed / STEPS.length) * 100;
      setProgress(Math.min(realPct,99));
      const next = STEPS[completed];
      if (next) setStatus(next.name);
    };

    // Fire all requests in parallel; advance the progress as each settles
    STEPS.forEach((step) => {
      Promise.resolve()
        .then(step.fn)
        .catch(() => null)         // graceful: hooks have mock fallbacks
        .finally(() => tick());
    });

    const reveal = () => {
      if (cancelled) return;
      setProgress(100);
      setStatus('Ready');
      setTimeout(() => !cancelled && setReady(true), 350);
    };

    // Hard timeout — never block the UI for more than 8s
    const timeout = setTimeout(reveal, HARD_TIMEOUT_MS);

    // Reveal once all steps complete AND minimum duration has elapsed
    const interval = setInterval(() => {
      if (completed >= STEPS.length) {
        const elapsed   = Date.now() - startedAt;
        const remaining = Math.max(0, MIN_DURATION_MS - elapsed);
        clearInterval(interval);
        clearTimeout(timeout);
        setTimeout(reveal, remaining);
      }
    }, 50);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
      clearInterval(interval);
    };
  }, []);

  return { ready, progress, status };
}
