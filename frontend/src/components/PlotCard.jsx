import { useState } from 'react';
import { BarChart3 } from 'lucide-react';
import Card from './Card';
import LazyPlot from '../charts/LazyPlot';
import DataTable from './DataTable';

// A chart card. If `unavailable` is set ({reason}), the reason is shown instead of a chart.
// `table` ({columns, rows}) adds an accessible data-table view of the same numbers.
export default function PlotCard({ title, subtitle, figure, unavailable, height = 320, actions, table, className = '', footer }) {
  const [showTable, setShowTable] = useState(false);
  const tableToggle = table && !unavailable ? (
    <button type="button" onClick={() => setShowTable((v) => !v)} aria-pressed={showTable}
      className="rounded-lg px-2 py-1 text-xs font-semibold text-forest hover:bg-mint-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-mint">
      {showTable ? 'Show chart' : 'Show table'}
    </button>
  ) : null;
  return (
    <Card title={title} subtitle={subtitle} className={className} actions={(actions || tableToggle) && <>{actions}{tableToggle}</>}>
      {unavailable ? (
        <div className="flex min-h-[120px] flex-col items-center justify-center gap-2 rounded-xl bg-canvas p-6 text-center">
          <BarChart3 className="h-5 w-5 text-subtle" aria-hidden="true" />
          <p className="text-sm font-semibold text-ink">Chart not available</p>
          <p className="max-w-md text-sm text-muted">{unavailable.reason}</p>
        </div>
      ) : showTable ? (
        <DataTable columns={table.columns} rows={table.rows} dense maxHeight={height} caption={title} />
      ) : figure ? (
        <LazyPlot data={figure.data} layout={figure.layout} height={figure.layout.height || height} ariaLabel={title} />
      ) : null}
      {footer && <div className="mt-3 text-xs text-muted">{footer}</div>}
    </Card>
  );
}
