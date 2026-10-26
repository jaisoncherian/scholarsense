export function formatNumber(value, digits = 0) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return null;
  return Number(value).toLocaleString(undefined, { minimumFractionDigits: digits, maximumFractionDigits: digits });
}

export function formatPct(value, digits = 1) {
  const n = formatNumber(value, digits);
  return n === null ? null : `${n}%`;
}

export function formatScore(value) {
  return value === null || value === undefined ? null : Number(value).toFixed(3);
}

export default function KpiCard({ label, value, hint, icon: Icon, tone = 'default' }) {
  const available = value !== null && value !== undefined && value !== '';
  return (
    <div className={`min-w-0 rounded-card border bg-card p-5 shadow-card ${tone === 'accent' ? 'border-mint' : 'border-line'}`}>
      <div className="flex min-h-8 items-start justify-between gap-3">
        <p className="pt-1 text-xs font-semibold uppercase tracking-wide text-subtle">{label}</p>
        {Icon && (
          <span className="rounded-lg bg-mint-soft p-2 text-forest" aria-hidden="true">
            <Icon className="h-4 w-4" />
          </span>
        )}
      </div>
      <p className={`mt-2 font-display font-bold tabular-nums tracking-tight ${available ? 'text-3xl text-ink' : 'text-base text-subtle'}`}>
        {available ? value : 'Not available'}
      </p>
      {hint && <p className="mt-1 text-sm text-muted">{hint}</p>}
    </div>
  );
}
