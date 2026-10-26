import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { Download, Play, Search, SlidersHorizontal } from 'lucide-react';
import TopBar from '../components/TopBar';
import StageGate from '../components/StageGate';
import Card from '../components/Card';
import Button, { buttonClass } from '../components/Button';
import Badge, { RiskBadge, SplitBadge } from '../components/Badge';
import Notice from '../components/Notice';
import ErrorBanner from '../components/ErrorBanner';
import Loader from '../components/Loader';
import DataTable, { Pagination } from '../components/DataTable';
import PlotCard from '../components/PlotCard';
import FeatureListCard from '../components/FeatureListCard';
import { SelectField, TextField } from '../components/Field';
import { formatScore } from '../components/KpiCard';
import { useAppStore } from '../hooks/AppStore';
import { useAction, useApiData } from '../hooks/useApi';
import { api } from '../services/api';
import { classCounts, riskHistogram } from '../charts/builders';

export function GeneratePanel() {
  const { summary, predict, metrics } = useAppStore();
  const [model, setModel] = useState('selected');
  const [scope, setScope] = useState(summary.predictions?.scope || 'test');
  const action = useAction(predict);
  const available = metrics ? Object.keys(metrics.models) : [];
  const selectedLabel = metrics?.selection?.selected ? metrics.models[metrics.selection.selected].label : null;
  return (
    <Card title={summary.predictions ? 'Re-score rows' : 'Generate predictions'}
      subtitle="Scores rows with a trained model. Held-out test rows give unbiased estimates; training rows are in-sample and optimistic.">
      <div className="grid gap-4 md:grid-cols-2">
        <SelectField label="Model" value={model} onChange={setModel}
          options={[{ value: 'selected', label: `Selected model${selectedLabel ? ` (${selectedLabel})` : ''}` },
            ...available.map((k) => ({ value: k, label: metrics.models[k].label }))]} />
        <fieldset>
          <legend className="mb-1 block text-xs font-semibold uppercase tracking-wide text-muted">Rows to score</legend>
          <div className="flex flex-wrap gap-3 text-sm">
            <label className="flex items-center gap-2"><input type="radio" name="scope" checked={scope === 'test'} onChange={() => setScope('test')} className="accent-[#2E5A44]" /> Held-out test rows only</label>
            <label className="flex items-center gap-2"><input type="radio" name="scope" checked={scope === 'all'} onChange={() => setScope('all')} className="accent-[#2E5A44]" /> All rows</label>
          </div>
        </fieldset>
      </div>
      {scope === 'all' && (
        <Notice tone="warning" className="mt-3">Scoring all rows includes the training rows. Their predictions are in-sample and look better than the model really is.</Notice>
      )}
      <div className="mt-4">
        <Button icon={Play} onClick={() => action.run({ model, scope })} loading={action.pending}>
          {summary.predictions ? 'Re-generate predictions' : 'Generate predictions'}
        </Button>
      </div>
      {action.error && <div className="mt-3"><ErrorBanner error={action.error} onDismiss={action.clearError} /></div>}
    </Card>
  );
}

function ThresholdEditor({ thresholds }) {
  const { setThresholds } = useAppStore();
  const [low, setLow] = useState(String(thresholds.low));
  const [high, setHigh] = useState(String(thresholds.high));
  useEffect(() => { setLow(String(thresholds.low)); setHigh(String(thresholds.high)); }, [thresholds.low, thresholds.high]);
  const action = useAction(setThresholds);
  const l = Number(low);
  const h = Number(high);
  const valid = low !== '' && high !== '' && l > 0 && l < h && h < 1;
  return (
    <Card title="Risk categories" subtitle="Risk score = model-estimated probability of the at-risk class. Not a calibrated real-world probability.">
      <div className="flex flex-wrap items-end gap-3">
        <TextField label="Medium from" type="number" step="0.01" min="0.01" max="0.98" value={low} onChange={setLow} className="w-32" />
        <TextField label="High from" type="number" step="0.01" min="0.02" max="0.99" value={high} onChange={setHigh} className="w-32" />
        <Button variant="secondary" icon={SlidersHorizontal} disabled={!valid} loading={action.pending} onClick={() => action.run(l, h)}>Apply thresholds</Button>
      </div>
      <p className="mt-2 text-xs text-muted">
        Low: score &lt; {thresholds.low} · Medium: {thresholds.low} ≤ score &lt; {thresholds.high} · High: score ≥ {thresholds.high}. Defaults are 0.33 / 0.66.
      </p>
      {!valid && <p className="mt-1 text-xs font-semibold text-risk-high-text">Thresholds must satisfy 0 &lt; medium &lt; high &lt; 1.</p>}
      {action.error && <div className="mt-3"><ErrorBanner error={action.error} onDismiss={action.clearError} /></div>}
    </Card>
  );
}

function PredictionsContent() {
  const { summary, resultsVersion, datasetVersion } = useAppStore();
  const [filters, setFilters] = useState({ split: 'test', predicted_class: '', risk: '', q: '', page: 1 });
  const [search, setSearch] = useState('');
  const hasPredictions = !!summary.predictions;
  useEffect(() => {
    const t = setTimeout(() => setFilters((f) => (f.q === search ? f : { ...f, q: search, page: 1 })), 300);
    return () => clearTimeout(t);
  }, [search]);
  useEffect(() => {
    if (summary.predictions?.scope === 'test') setFilters((f) => ({ ...f, split: 'test', page: 1 }));
  }, [summary.predictions?.scope, summary.predictions?.generated_at]);
  const query = useApiData(() => api.listPredictions({ ...filters, page_size: 25 }), [JSON.stringify(filters), resultsVersion, datasetVersion], hasPredictions);
  const setFilter = (key) => (value) => setFilters((f) => ({ ...f, [key]: value, page: 1 }));

  if (!hasPredictions) return <GeneratePanel />;
  if (query.error) return <ErrorBanner error={query.error} onRetry={query.reload} />;
  if (!query.data) return <Loader label="Loading predictions…" />;
  const { meta, summary: s, rows } = query.data;

  return (
    <div className="space-y-6">
      <Notice tone="mint" title={`Scored with ${meta.model_label}${meta.model === meta.selected_model ? ' (selected model)' : ''}`}>
        {meta.risk_note} At-risk class: “{meta.at_risk_class}”. Predicted classes are model estimates; a non-at-risk prediction (for example “Enrolled”) is not a confirmed outcome.
      </Notice>
      {meta.scope === 'all' && filters.split !== 'test' && <Notice tone="warning">{meta.split_notes.train}</Notice>}
      <div className="grid gap-6 xl:grid-cols-3">
        <PlotCard title="Predicted class distribution" subtitle={`${s.total} row(s) in the current split filter`} figure={classCounts(s.by_predicted_class, meta.classes)}
          table={{ columns: [{ key: 'k', header: 'Class' }, { key: 'v', header: 'Rows', align: 'right' }], rows: Object.entries(s.by_predicted_class).map(([k, v]) => ({ k, v })) }} />
        <PlotCard title="Risk score distribution" subtitle="Dotted lines mark the category thresholds." figure={riskHistogram(s.risk_histogram, meta.thresholds)}
          table={{ columns: [{ key: 'k', header: 'Category' }, { key: 'v', header: 'Rows', align: 'right' }], rows: Object.entries(s.by_risk_category).map(([k, v]) => ({ k: `${k} risk`, v })) }} />
        <ThresholdEditor thresholds={meta.thresholds} />
      </div>

      <Card title="Scored students" subtitle={meta.split_notes[filters.split] || 'All scored rows.'}
        actions={<a className={buttonClass('secondary', 'sm')} href={api.exportUrl('predictions')} download><Download className="h-4 w-4" aria-hidden="true" /> Export CSV</a>}>
        <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <SelectField label="Rows" value={filters.split} onChange={setFilter('split')}
            options={[
              { value: 'test', label: `Held-out test rows (${query.data.split_counts.test})` },
              { value: 'train', label: `Training rows, in-sample (${query.data.split_counts.train})`, disabled: !query.data.split_counts.train },
              { value: 'unlabeled', label: `Rows without target (${query.data.split_counts.unlabeled})`, disabled: !query.data.split_counts.unlabeled },
              { value: 'all', label: 'All scored rows' },
            ]} />
          <SelectField label="Predicted class" value={filters.predicted_class} onChange={setFilter('predicted_class')} placeholder="All classes"
            options={meta.classes.map((c) => ({ value: c, label: c }))} />
          <SelectField label="Risk category" value={filters.risk} onChange={setFilter('risk')} placeholder="All categories"
            options={['High', 'Medium', 'Low'].map((c) => ({ value: c, label: `${c} risk` }))} />
          <TextField label={`Search ${meta.id_column ? `by ${meta.id_column}` : 'by row'}`} value={search} onChange={setSearch} placeholder="Type to search…" />
        </div>
        <DataTable caption="Scored students" rowKey={(r) => r.row_id} rows={rows} emptyMessage="No rows match these filters."
          columns={[
            { key: 'identifier', header: meta.id_column || 'Row', render: (r) => <span className="whitespace-nowrap font-medium">{r.identifier}</span> },
            { key: 'split', header: 'Split', render: (r) => <SplitBadge split={r.split} /> },
            { key: 'predicted_class', header: 'Predicted class', render: (r) => <Badge>{r.predicted_class}</Badge> },
            ...meta.classes.map((c) => ({ key: `p_${c}`, header: `P(${c})`, align: 'right', render: (r) => formatScore(r.probabilities[c]) })),
            { key: 'risk_score', header: 'Risk score', align: 'right', render: (r) => <span className="font-semibold">{formatScore(r.risk_score)}</span> },
            { key: 'risk_category', header: 'Risk', render: (r) => <RiskBadge category={r.risk_category} /> },
            { key: 'observed', header: 'Observed outcome', render: (r) => r.observed },
            { key: 'actions', header: 'Details', render: (r) => (
              <span className="flex gap-3 whitespace-nowrap text-xs font-semibold">
                <Link className="text-forest hover:underline" to={`/explainability?row=${r.row_id}`}>View details</Link>
                <Link className="text-forest hover:underline" to={`/interventions?row=${r.row_id}`}>Support</Link>
              </span>
            ) },
          ]} />
        <Pagination page={query.data.page} pages={query.data.pages} total={query.data.total} onPage={(p) => setFilters((f) => ({ ...f, page: p }))} />
      </Card>
      <FeatureListCard features={meta.features} timingLabel={meta.timing_label} earlyPrediction={meta.early_prediction} title="Features used by this model" />
      <GeneratePanel />
    </div>
  );
}

export default function RiskPredictions() {
  return (
    <>
      <TopBar eyebrow="Step 4 · Predict" title="Risk Predictions"
        description="Model-estimated risk for each scored student, with clear labelling of which rows were seen during training." />
      <StageGate requires="trained">
        <PredictionsContent />
      </StageGate>
    </>
  );
}
