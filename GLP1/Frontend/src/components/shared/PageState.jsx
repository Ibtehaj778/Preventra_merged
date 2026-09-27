import { AlertTriangle } from 'lucide-react';
import { SkeletonKPIStrip, SkeletonChart } from './LoadingSkeleton';

/**
 * What a page shows until its data has arrived: a skeleton while loading, the
 * reason if the request failed. Never stand-in numbers - a made-up figure on a
 * dashboard reads exactly like a real one.
 */
export default function PageState({ error, label = 'this page' }) {
  if (error) {
    return (
      <div className="card p-6 flex items-start gap-3 text-sm" style={{ color: '#C62828' }}>
        <AlertTriangle size={18} className="flex-shrink-0 mt-0.5" />
        <div>
          <div className="font-semibold">Couldn&apos;t load {label}</div>
          <div className="text-xs mt-0.5" style={{ color: '#E57373' }}>{error.message || String(error)}</div>
        </div>
      </div>
    );
  }
  return (
    <div className="space-y-5 animate-fade-in">
      <SkeletonKPIStrip />
      <SkeletonChart />
    </div>
  );
}
