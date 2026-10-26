import { AlertCircle, RotateCw, X } from 'lucide-react';

export default function ErrorBanner({ error, onRetry, onDismiss, title = 'Something went wrong' }) {
  if (!error) return null;
  const message = typeof error === 'string' ? error : error.message;
  const details = typeof error === 'object' ? error.details : null;
  const subErrors = details && Array.isArray(details.errors) ? details.errors : [];
  return (
    <div role="alert" className="flex items-start gap-3 rounded-xl border border-risk-high/30 bg-risk-high-soft p-4 text-sm text-risk-high-text">
      <AlertCircle className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold">{title}</p>
        <p className="mt-0.5 break-words">{message}</p>
        {subErrors.length > 1 && (
          <ul className="mt-1 list-disc pl-5">
            {subErrors.map((e) => <li key={e.code}>{e.message}</li>)}
          </ul>
        )}
      </div>
      {onRetry && (
        <button type="button" onClick={onRetry} className="inline-flex items-center gap-1 rounded-md px-2 py-1 font-semibold hover:bg-white/60 focus:outline-none focus-visible:ring-2 focus-visible:ring-risk-high">
          <RotateCw className="h-3.5 w-3.5" aria-hidden="true" /> Retry
        </button>
      )}
      {onDismiss && (
        <button type="button" onClick={onDismiss} aria-label="Dismiss error" className="rounded-md p-1 hover:bg-white/60">
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      )}
    </div>
  );
}
