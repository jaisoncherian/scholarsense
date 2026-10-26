export default function EmptyState({ icon: Icon, title, description, action, children, compact = false }) {
  return (
    <div className={`flex flex-col items-center justify-center rounded-card border border-dashed border-line-strong bg-card text-center ${compact ? 'p-6' : 'p-10'}`}>
      {Icon && (
        <span className="mb-3 rounded-full bg-mint-soft p-3 text-forest" aria-hidden="true">
          <Icon className="h-6 w-6" />
        </span>
      )}
      <h3 className="font-display text-base font-semibold text-ink">{title}</h3>
      {description && <p className="mt-1 max-w-xl text-sm text-muted">{description}</p>}
      {children}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}
