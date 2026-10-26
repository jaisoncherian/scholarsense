import { useId } from 'react';

export const inputClass =
  'h-10 w-full rounded-lg border border-line-strong bg-card px-3 text-sm text-ink placeholder:text-subtle focus:border-forest focus:outline-none focus:ring-2 focus:ring-mint-soft disabled:bg-canvas disabled:text-subtle';

export function Field({ label, hint, children, className = '' }) {
  const id = useId();
  return (
    <div className={`min-w-0 ${className}`}>
      <label htmlFor={id} className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">{label}</label>
      {children(id)}
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

export function SelectField({ label, hint, value, onChange, options, placeholder, disabled, className }) {
  return (
    <Field label={label} hint={hint} className={className}>
      {(id) => (
        <select id={id} className={inputClass} value={value ?? ''} disabled={disabled} onChange={(e) => onChange(e.target.value)}>
          {placeholder !== undefined && <option value="">{placeholder}</option>}
          {options.map((o) => (
            <option key={o.value} value={o.value} disabled={o.disabled}>{o.label}</option>
          ))}
        </select>
      )}
    </Field>
  );
}

export function TextField({ label, hint, value, onChange, type = 'text', className, ...rest }) {
  return (
    <Field label={label} hint={hint} className={className}>
      {(id) => <input id={id} type={type} className={inputClass} value={value ?? ''} onChange={(e) => onChange(e.target.value)} {...rest} />}
    </Field>
  );
}
