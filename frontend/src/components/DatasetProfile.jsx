import { AlertTriangle, Copy, Database, FileSpreadsheet, Info, Rows3 } from 'lucide-react';
import Card from './Card';
import KpiCard, { formatNumber, formatPct } from './KpiCard';
import Badge from './Badge';
import DataTable from './DataTable';

export function formatBytes(bytes) {
  if (bytes === null || bytes === undefined) return null;
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`;
}

export function DatasetKpis({ summary }) {
  const ds = summary.dataset;
  const p = summary.profile;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="Rows" value={formatNumber(ds.rows)} icon={Rows3} hint={`${formatNumber(ds.columns)} columns`} />
      <KpiCard label="File" value={formatBytes(ds.size_bytes)} icon={FileSpreadsheet} hint={`${ds.delimiter}-delimited · ${ds.encoding}`} />
      <KpiCard label="Missing cells" value={formatNumber(p.missing_cells)} icon={Database}
        hint={`${formatPct(p.missing_cells_pct)} of all cells · ${p.columns_with_missing} column(s) affected`} />
      <KpiCard label="Duplicate rows" value={formatNumber(p.duplicate_rows)} icon={Copy}
        hint={ds.rows ? `${formatPct((100 * p.duplicate_rows) / ds.rows)} of rows` : null} />
    </div>
  );
}

const LEVEL_TONE = { error: 'danger', warning: 'warning', info: 'mint' };

export function IssueList({ issues }) {
  if (!issues.length) {
    return <p className="text-sm text-muted">No structural issues were detected.</p>;
  }
  return (
    <ul className="space-y-2">
      {issues.map((issue) => (
        <li key={issue.code + issue.message} className="flex gap-3 rounded-xl border border-line bg-canvas p-3 text-sm">
          {issue.level === 'info' ? <Info className="mt-0.5 h-4 w-4 flex-none text-forest" aria-hidden="true" />
            : <AlertTriangle className="mt-0.5 h-4 w-4 flex-none text-risk-medium-text" aria-hidden="true" />}
          <div className="min-w-0">
            <p className="text-ink"><Badge tone={LEVEL_TONE[issue.level]} className="mr-2">{issue.level}</Badge>{issue.message}</p>
            {issue.columns?.length > 0 && <p className="mt-1 break-words text-xs text-muted">Columns: {issue.columns.join(', ')}</p>}
          </div>
        </li>
      ))}
    </ul>
  );
}

const FLAG_LABELS = {
  constant: 'Constant', id_like: 'ID-like', high_cardinality: 'High cardinality', mostly_missing: 'Mostly missing', later_term: 'Possible later-term',
};

export function ColumnTable({ columns }) {
  return (
    <DataTable caption="Detected column types" dense maxHeight={420} rowKey={(c) => c.name} rows={columns}
      columns={[
        { key: 'name', header: 'Column', render: (c) => <span className="font-medium text-ink">{c.name}</span> },
        { key: 'type', header: 'Detected type', render: (c) => <Badge>{c.type}</Badge> },
        { key: 'missing', header: 'Missing', align: 'right', className: 'whitespace-nowrap', render: (c) => `${formatNumber(c.missing)} (${formatPct(c.missing_pct)})` },
        { key: 'unique', header: 'Unique values', align: 'right', render: (c) => formatNumber(c.unique) },
        { key: 'flags', header: 'Flags', render: (c) => (c.flags.length ? (
          <span className="flex flex-wrap gap-1">{c.flags.map((f) => <Badge key={f} tone="warning">{FLAG_LABELS[f] || f}</Badge>)}</span>
        ) : null) },
      ]} />
  );
}

export function PreviewTable({ preview }) {
  const cols = [{ key: '__row', header: '#', align: 'right', render: (_, i) => preview.row_ids[i] + 1 }].concat(
    preview.columns.map((name, idx) => ({ key: `c${idx}`, header: name, render: (row) => row[idx], className: 'whitespace-nowrap' })),
  );
  return (
    <Card title={`Preview: first ${preview.rows.length} rows`} subtitle={`${formatNumber(preview.total_rows)} rows in total. Missing values are shown as —.`}>
      <DataTable caption="Dataset preview" dense columns={cols} rows={preview.rows} maxHeight={480} />
    </Card>
  );
}
