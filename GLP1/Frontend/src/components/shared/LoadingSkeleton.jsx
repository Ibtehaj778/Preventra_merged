export function SkeletonCard({ h = 120, className = "" }) {
  return (
    <div className={`card overflow-hidden ${className}`} style={{ height: h }}>
      <div className="animate-pulse bg-gray-100 w-full h-full rounded-xl" />
    </div>
  );
}

export function SkeletonKPIStrip() {
  return (
    <div className="exec-kpi-grid">
      {Array.from({ length: 5 }, (_, i) => (
        <SkeletonCard key={i} h={96} />
      ))}
    </div>
  );
}

export function SkeletonTable({ rows = 6 }) {
  return (
    <div className="card p-4 space-y-3">
      <div className="h-6 w-48 bg-gray-100 rounded animate-pulse" />
      {Array.from({ length: rows }, (_, i) => (
        <div
          key={i}
          className="h-8 bg-gray-100 rounded animate-pulse"
          style={{ animationDelay: `${i * 0.04}s`, opacity: 1 - i * 0.12 }}
        />
      ))}
    </div>
  );
}

export function SkeletonChart({ h = 260, className = "" }) {
  return (
    <div className={`card p-5 ${className}`}>
      <div className="h-5 w-40 bg-gray-100 rounded animate-pulse mb-4" />
      <div className="animate-pulse bg-gray-100 rounded-lg" style={{ height: h }} />
    </div>
  );
}
