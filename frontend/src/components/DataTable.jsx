// Generic table. Cell values are rendered as text (React escapes them); never as HTML.
export default function DataTable({ columns, rows, rowKey, caption, emptyMessage = 'No rows to show.', dense = false, maxHeight, highlightRow }) {
  const cellPad = dense ? 'px-3 py-2' : 'px-4 py-3';
  return (
    <div className="overflow-x-auto rounded-xl border border-line" style={maxHeight ? { maxHeight, overflowY: 'auto' } : undefined}>
      <table className="min-w-full text-left text-sm">
        {caption && <caption className="sr-only">{caption}</caption>}
        <thead className="sticky top-0 z-10 bg-canvas">
          <tr>
            {columns.map((col) => (
              <th key={col.key} scope="col"
                className={`${cellPad} border-b border-line-strong text-[11px] font-bold uppercase tracking-wide text-muted ${col.align === 'right' ? 'text-right' : ''}`}>
                {col.header}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.length === 0 && (
            <tr>
              <td colSpan={columns.length} className="px-4 py-6 text-center text-muted">{emptyMessage}</td>
            </tr>
          )}
          {rows.map((row, i) => {
            const key = rowKey ? rowKey(row, i) : i;
            const highlighted = highlightRow && highlightRow(row);
            return (
              <tr key={key} className={`border-b border-[#F3F3F4] last:border-0 hover:bg-[#FAFAFA] ${highlighted ? 'bg-mint-soft' : 'bg-card'}`}>
                {columns.map((col) => {
                  const value = col.render ? col.render(row, i) : row[col.key];
                  return (
                    <td key={col.key} className={`${cellPad} align-middle ${col.align === 'right' ? 'text-right tabular-nums' : ''} ${col.className || ''}`}>
                      {value === null || value === undefined || value === '' ? <span className="text-subtle">—</span> : value}
                    </td>
                  );
                })}
              </tr>
            );
          })}
        </tbody>
      </table>
    </div>
  );
}

export function Pagination({ page, pages, total, onPage, label = 'rows' }) {
  if (!pages || pages <= 1) {
    return <p className="mt-3 text-sm text-muted">{total} {label}</p>;
  }
  return (
    <nav aria-label="Pagination" className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-muted">
      <span>{total} {label} · page {page} of {pages}</span>
      <div className="flex gap-2">
        <button type="button" className="rounded-lg border border-line-strong bg-card px-3 py-1.5 font-semibold text-ink disabled:text-subtle" disabled={page <= 1} onClick={() => onPage(page - 1)}>
          Previous
        </button>
        <button type="button" className="rounded-lg border border-line-strong bg-card px-3 py-1.5 font-semibold text-ink disabled:text-subtle" disabled={page >= pages} onClick={() => onPage(page + 1)}>
          Next
        </button>
      </div>
    </nav>
  );
}
