import { useEffect, useState } from 'react';
import { getAlerts, getMe, getPatients, getSummary, pingService } from '../api';
import { readClaims } from '../api/auth';

// The same opening sequence as GLP-1 (GLP1/Frontend/src/hooks/useAppLoader.js):
// a progress bar that advances as the first requests come back. They also wake
// the API and the database, which on a cold start is most of the wait - so the
// first page then opens on a warm service rather than behind its own spinners.
const HARD_TIMEOUT_MS = 8000;     // never hold the app back longer than this
const MIN_DURATION_MS = 1500;     // and never flash the screen for a split second

// Only light requests, fitted to the role: a patient has no worklist or alerts.
function stepsFor(role) {
  const isPatient = role === 'patient';
  return [
    { name: 'Connecting to Preventra…', fn: () => pingService() },
    { name: 'Checking your account…', fn: () => getMe() },
    { name: isPatient ? 'Loading your record…' : 'Loading your patients…',
      fn: () => getPatients({ limit: 1 }) },
    ...(isPatient ? [] : [
      { name: 'Loading risk summary…', fn: () => getSummary() },
      { name: 'Loading alerts…', fn: () => getAlerts() },
    ]),
    { name: 'Finalizing…', fn: () => Promise.resolve() },
  ];
}

export function useAppLoader() {
  const [steps] = useState(() => stepsFor(readClaims()?.role));
  const [progress, setProgress] = useState(0);
  const [status, setStatus] = useState(steps[0].name);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const startedAt = Date.now();
    let cancelled = false;
    let completed = 0;

    const tick = () => {
      if (cancelled) return;
      completed += 1;
      // Held below 100% until the reveal, so the bar never sits full while
      // the minimum duration runs out.
      setProgress(Math.min((completed / steps.length) * 100, 99));
      const next = steps[completed];
      if (next) setStatus(next.name);
    };

    // All at once; each settled request moves the bar. A failure still counts:
    // the page it belongs to reports the error itself, and a lapsed session is
    // already sent to the portal by the API client.
    steps.forEach((step) => {
      Promise.resolve()
        .then(step.fn)
        .catch(() => null)
        .finally(tick);
    });

    let revealTimer;
    const reveal = () => {
      if (cancelled) return;
      setProgress(100);
      setStatus('Ready');
      revealTimer = setTimeout(() => !cancelled && setReady(true), 350);
    };

    const timeout = setTimeout(reveal, HARD_TIMEOUT_MS);
    const interval = setInterval(() => {
      if (completed >= steps.length) {
        clearInterval(interval);
        clearTimeout(timeout);
        revealTimer = setTimeout(reveal, Math.max(0, MIN_DURATION_MS - (Date.now() - startedAt)));
      }
    }, 50);

    return () => {
      cancelled = true;
      clearTimeout(timeout);
      clearTimeout(revealTimer);
      clearInterval(interval);
    };
  }, [steps]);

  return { ready, progress, status };
}
