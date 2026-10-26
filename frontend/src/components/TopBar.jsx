// Page header: eyebrow, title, description and page-level actions.
export default function TopBar({ eyebrow, title, description, actions }) {
  return (
    <header className="mb-6 flex flex-wrap items-end justify-between gap-4">
      <div className="min-w-0 max-w-3xl">
        {eyebrow && (
          <p className="mb-2 inline-flex rounded-md bg-mint-soft px-2 py-0.5 text-xs font-bold uppercase tracking-wide text-forest">{eyebrow}</p>
        )}
        <h1 className="font-display text-3xl font-bold tracking-tight text-ink">{title}</h1>
        {description && <p className="mt-2 text-base text-muted">{description}</p>}
      </div>
      {actions && <div className="flex flex-wrap items-center gap-2">{actions}</div>}
    </header>
  );
}
