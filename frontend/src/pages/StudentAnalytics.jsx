import { useEffect, useMemo, useState } from 'react';
import { BarChart3, Columns3, Copy, Database, Hash, ListTree } from 'lucide-react';
import TopBar from '../components/TopBar';
import StageGate from '../components/StageGate';
import EmptyState from '../components/EmptyState';
import Button from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import KpiCard, { formatNumber, formatPct } from '../components/KpiCard';
import PlotCard from '../components/PlotCard';
import Card from '../components/Card';
import DataTable from '../components/DataTable';
import { SelectField } from '../components/Field';
import { useAppStore } from '../hooks/AppStore';
import { useAction } from '../hooks/useApi';
import * as charts from '../charts/builders';

export function TargetDistributionCard({ analysis }) {
  const dist = analysis.target_distribution;
  return (
    <PlotCard title="Target distribution" subtitle={`Observed classes of “${analysis.overview.target}”${dist.missing ? ` · ${dist.missing} row(s) without a target value` : ''}`}
      figure={charts.targetDistribution(dist, analysis.classes)}
      table={{ columns: [{ key: 'class', header: 'Class' }, { key: 'count', header: 'Rows', align: 'right' }, { key: 'pct', header: '%', align: 'right', render: (r) => formatPct(r.pct) }], rows: dist.classes }} />
  );
}

export function EdaKpis({ analysis }) {
  const o = analysis.overview;
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-4">
      <KpiCard label="Rows" value={formatNumber(o.rows)} icon={Hash} hint={`${o.class_count} target classes`} />
      <KpiCard label="Model features" value={formatNumber(o.feature_count)} icon={Columns3} hint={`${o.numeric_features} numeric · ${o.categorical_features} categorical / boolean`} />
      <KpiCard label="Missing cells" value={formatPct(analysis.missing.pct_cells)} icon={Database} hint={`${formatNumber(analysis.missing.total_cells)} cells in ${analysis.missing.columns.length} column(s)`} />
      <KpiCard label="Duplicate rows" value={formatNumber(analysis.duplicates.count)} icon={Copy} hint={`${formatPct(analysis.duplicates.pct)} of rows`} />
    </div>
  );
}

function HistogramSection({ analysis }) {
  const numericCols = Object.keys(analysis.histograms);
  const [selected, setSelected] = useState(analysis.default_histograms);
  useEffect(() => setSelected(analysis.default_histograms), [analysis]);
  if (!numericCols.length) {
    return <PlotCard title="Numeric distributions" unavailable={{ reason: 'No numeric feature columns were detected.' }} />;
  }
  const toggle = (col) => setSelected((s) => (s.includes(col) ? s.filter((c) => c !== col) : [...s, col].slice(-6)));
  return (
    <Card title="Numeric distributions" subtitle="Defaults to the numeric columns most associated with the target. Select up to 6.">
      <div className="mb-4 flex flex-wrap gap-2" role="group" aria-label="Choose numeric columns">
        {numericCols.map((col) => (
          <button key={col} type="button" aria-pressed={selected.includes(col)} onClick={() => toggle(col)}
            className={`rounded-full border px-3 py-1 text-xs font-semibold focus:outline-none focus-visible:ring-2 focus-visible:ring-mint ${
              selected.includes(col) ? 'border-forest bg-mint-soft text-forest' : 'border-line-strong bg-card text-muted hover:text-ink'}`}>
            {col}
          </button>
        ))}
      </div>
      <div className="grid gap-4 lg:grid-cols-2">
        {selected.map((col) => {
          const h = analysis.histograms[col];
          return (
            <PlotCard key={col} title={col} className="shadow-none" height={240}
              unavailable={h.available ? null : { reason: h.reason }} figure={h.available ? charts.histogram(col, h) : null} />
          );
        })}
      </div>
    </Card>
  );
}

function CategoricalSection({ analysis }) {
  const cats = analysis.categorical_counts;
  const [col, setCol] = useState(cats[0]?.column || '');
  useEffect(() => setCol(cats[0]?.column || ''), [cats]);
  if (!cats.length) {
    return <PlotCard title="Categorical values" unavailable={{ reason: 'No categorical or boolean feature columns were detected.' }} />;
  }
  const entry = cats.find((c) => c.column === col) || cats[0];
  return (
    <PlotCard title="Categorical values" subtitle={`Top 10 values; the rest are grouped as “Other”. ${entry.distinct} distinct values, ${entry.missing} missing.`}
      actions={<SelectField label="Column" value={entry.column} onChange={setCol} options={cats.map((c) => ({ value: c.column, label: c.column }))} className="w-56" />}
      figure={charts.categoricalCounts(entry)}
      table={{ columns: [{ key: 'value', header: 'Value' }, { key: 'count', header: 'Rows', align: 'right' }, { key: 'pct', header: '%', align: 'right', render: (r) => formatPct(r.pct) }], rows: entry.values }} />
  );
}

function FeatureVsTarget({ analysis }) {
  const fvt = analysis.feature_vs_target;
  if (!fvt.available) return <PlotCard title="Features compared across outcomes" unavailable={fvt} />;
  return (
    <Card title="Features compared across outcomes"
      subtitle="The columns with the strongest descriptive association with the target (η² for numeric, Cramér's V for categorical). Association is not causation.">
      <div className="grid gap-4 lg:grid-cols-2">
        {fvt.charts.map((c) => (
          <PlotCard key={c.column} title={c.column} className="shadow-none" height={280}
            subtitle={`${c.kind === 'box' ? 'Box plot by class' : 'Share of each class within category'} · ${c.measure === 'eta_squared' ? 'η²' : "Cramér's V"} = ${c.score?.toFixed(3)}`}
            figure={c.kind === 'box' ? charts.boxByClass(c, analysis.classes) : charts.stackedByClass(c, analysis.classes)} />
        ))}
      </div>
    </Card>
  );
}

function NumericStatsTable({ stats }) {
  if (!stats.length) return null;
  const f = (v) => (v === null || v === undefined ? null : Number(v).toLocaleString(undefined, { maximumFractionDigits: 3 }));
  return (
    <Card title="Numeric summary statistics">
      <DataTable caption="Numeric summary statistics" dense maxHeight={420} rowKey={(r) => r.column} rows={stats}
        columns={[
          { key: 'column', header: 'Column', render: (r) => <span className="font-medium">{r.column}</span> },
          { key: 'count', header: 'Count', align: 'right', render: (r) => formatNumber(r.count) },
          { key: 'missing', header: 'Missing', align: 'right', render: (r) => formatNumber(r.missing) },
          ...['mean', 'std', 'min', 'q1', 'median', 'q3', 'max'].map((k) => ({ key: k, header: k === 'q1' ? '25%' : k === 'q3' ? '75%' : k, align: 'right', render: (r) => f(r[k]) })),
        ]} />
    </Card>
  );
}

function AnalyticsContent() {
  const { analysis, runAnalysis, summary } = useAppStore();
  const analyze = useAction(runAnalysis);
  const missing = analysis?.missing_chart;
  const corr = analysis?.correlation;
  const academic = analysis?.academic;
  const missingTable = useMemo(() => (missing?.available ? missing.columns : []), [missing]);

  if (!analysis) {
    return (
      <EmptyState icon={BarChart3} title="Analysis has not been run"
        description={`Run the exploratory analysis to compute statistics and charts from “${summary.dataset.filename}”.`}
        action={<Button icon={BarChart3} onClick={analyze.run} loading={analyze.pending}>Run analysis</Button>}>
        {analyze.error && <div className="mt-3 w-full max-w-lg"><ErrorBanner error={analyze.error} /></div>}
      </EmptyState>
    );
  }
  return (
    <div className="space-y-6">
      <EdaKpis analysis={analysis} />
      <div className="grid gap-6 xl:grid-cols-2">
        <TargetDistributionCard analysis={analysis} />
        <PlotCard title="Missing values by column" subtitle="Share of rows with no value." unavailable={missing.available ? null : missing}
          figure={missing.available ? charts.missingChart(missing.columns) : null}
          table={{ columns: [{ key: 'column', header: 'Column' }, { key: 'missing', header: 'Missing', align: 'right' }, { key: 'pct', header: '%', align: 'right', render: (r) => formatPct(r.pct) }], rows: missingTable }} />
      </div>
      <HistogramSection analysis={analysis} />
      <div className="grid gap-6 xl:grid-cols-2">
        <CategoricalSection analysis={analysis} />
        <PlotCard title="Correlation between numeric columns" height={420}
          subtitle={corr.available ? `Pearson r for numeric, non-binary, non-ID columns${corr.truncated ? ` (top ${corr.columns.length} of ${corr.total_candidates})` : ''}.` : null}
          unavailable={corr.available ? null : corr} figure={corr.available ? charts.heatmap(corr.columns, corr.matrix) : null} />
      </div>
      <FeatureVsTarget analysis={analysis} />
      <PlotCard title="Academic indicators by outcome" subtitle={academic.available ? academic.note : null}
        unavailable={academic.available ? null : academic} figure={academic.available ? charts.groupedMeans(academic) : null} />
      <NumericStatsTable stats={analysis.numeric_stats} />
      <div className="flex justify-end">
        <Button variant="secondary" icon={ListTree} onClick={analyze.run} loading={analyze.pending}>Re-run analysis</Button>
      </div>
    </div>
  );
}

export default function StudentAnalytics() {
  return (
    <>
      <TopBar eyebrow="Step 2 · Explore" title="Student Analytics"
        description="Descriptive statistics and charts computed from the uploaded file. Charts appear only when matching columns exist." />
      <StageGate requires="configured">
        <AnalyticsContent />
      </StageGate>
    </>
  );
}
