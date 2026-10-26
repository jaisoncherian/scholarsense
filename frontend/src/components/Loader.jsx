import { Loader2 } from 'lucide-react';

export function Spinner({ label = 'Loading', className = '' }) {
  return (
    <span role="status" className={`inline-flex items-center gap-2 text-sm text-muted ${className}`}>
      <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
      <span>{label}</span>
    </span>
  );
}

export function Skeleton({ className = '', style }) {
  return <div aria-hidden="true" style={style} className={`animate-pulse rounded-lg bg-line ${className}`} />;
}

export default function Loader({ label = 'Loading…', rows = 3 }) {
  return (
    <div className="space-y-3" aria-busy="true">
      <Spinner label={label} />
      {Array.from({ length: rows }).map((_, i) => (
        <Skeleton key={i} className="h-16 w-full" />
      ))}
    </div>
  );
}
