import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { Search } from 'lucide-react';
import TopBar from '../components/TopBar';
import StageGate from '../components/StageGate';
import Card from '../components/Card';
import Button from '../components/Button';
import Badge, { SplitBadge } from '../components/Badge';
import Notice from '../components/Notice';
import ErrorBanner from '../components/ErrorBanner';
import Loader from '../components/Loader';
import DataTable from '../components/DataTable';
import PlotCard from '../components/PlotCard';
import { SelectField, TextField } from '../components/Field';
import { formatScore } from '../components/KpiCard';
import { useAppStore } from '../hooks/AppStore';
import { useApiData } from '../hooks/useApi';
import { api } from '../services/api';
import { contributionChart, importanceChart } from '../charts/builders';

function GlobalImportance({ model }) {
  const { resultsVersion, metrics } = useAppStore();
  const [scoring, setScoring] = useState('f1_macro');
  const q = useApiData(() => api.globalExplanation({ model, scoring }), [model, scoring, resultsVersion]);
  const exp = q.data?.explanation;
  return (
    <Card title="Global feature importance" subtitle="Permutation importance on the held-out test set, computed on the original columns."
      actions={<SelectField label="Score" value={scoring} onChange={setScoring} className="w-56"
        options={[{ value: 'f1_macro', label: 'Macro-F1' }, { value: 'at_risk_recall', label: `Recall for “${metrics.at_risk_class}”` }]} />}>
      {q.loading && <Loader label="Computing permutation importance…" rows={2} />}
      {q.error && <ErrorBanner error={q.error} onRetry={q.reload} />}
      {exp && (
        <>
          <Notice tone="info" className="mb-4">
            {exp.note} Each column was shuffled {exp.n_repeats} times (seed {exp.random_state}) on {exp.rows_used} {exp.evaluated_on} rows{exp.sampled ? ' (a stratified sample of the test set)' : ''}; bars show the mean drop in {exp.scoring_label}, whiskers ± 1 standard deviation.
          </Notice>
          <PlotCard title={`${exp.model_label}: importance by column`} className="shadow-none" figure={importanceChart(exp.features)}
            table={{ columns: [{ key: 'feature', header: 'Column' }, { key: 'importance', header: 'Mean drop', align: 'right', render: (r) => r.importance?.toFixed(4) }, { key: 'std', header: '± std', align: 'right', render: (r) => r.std?.toFixed(4) }], rows: exp.features }} />
        </>
      )}
    </Card>
  );
}

function LocalExplanation({ model, rowId }) {
  const { resultsVersion } = useAppStore();
  const q = useApiData(() => api.localExplanation(rowId, { model }), [model, rowId, resultsVersion], rowId !== null);
  if (rowId === null) {
    return <Notice tone="info">Enter a row number, or choose “View details” on the Risk Predictions page, to explain one student's prediction.</Notice>;
  }
  if (q.loading) return <Loader label="Explaining prediction…" rows={2} />;
  if (q.error) return <ErrorBanner error={q.error} onRetry={q.reload} />;
  const exp = q.data?.explanation;
  if (!exp) return null;
  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-center gap-2">
        <h3 className="font-display text-lg font-semibold text-ink">{exp.identifier}</h3>
        <SplitBadge split={exp.split} />
        <Badge tone="mint">Predicted: {exp.predicted_class}</Badge>
        <Badge>Model: {exp.model_label}</Badge>
      </div>
      {exp.in_sample && <Notice tone="warning">This row was used to train the model, so its prediction is in-sample and likely more confident than for a new student.</Notice>}
      <div className="flex flex-wrap gap-2 text-sm">
        {Object.entries(exp.probabilities).map(([c, p]) => (
          <span key={c} className={`rounded-lg border px-3 py-1.5 tabular-nums ${c === exp.at_risk_class ? 'border-risk-high/40 bg-risk-high-soft text-risk-high-text' : 'border-line bg-canvas text-ink'}`}>
            P({c}) = {formatScore(p)}
          </span>
        ))}
      </div>
      <Notice tone="mint" title="How this explanation was computed">
        <p>{exp.method}</p>
        <p className="mt-1"><span className="font-semibold">Limits:</span> {exp.limitations}</p>
      </Notice>
      <Card title="In plain language" className="shadow-none">
        <ul className="list-disc space-y-1 pl-5 text-sm text-ink">
          {exp.summary.map((line) => <li key={line}>{line}</li>)}
        </ul>
        <p className="mt-2 text-xs text-muted">These statements describe how the model arrived at its estimate for this student. They are not causes and not an assessment of the student.</p>
      </Card>
      <PlotCard title="Contribution by feature" subtitle={`Unit: ${exp.unit}. Right of zero pushed toward “${exp.predicted_class}”, left pushed away.`} className="shadow-none"
        figure={contributionChart(exp.contributions, exp.unit)} />
      {exp.missing_features.length > 0 && (
        <Notice tone="warning">No explanation is given for features whose value is missing in the file: {exp.missing_features.join(', ')}.</Notice>
      )}
      <DataTable caption="Feature contributions" dense maxHeight={420} rowKey={(r) => r.feature} rows={exp.contributions}
        columns={[
          { key: 'feature', header: 'Feature', render: (r) => <span className="font-medium">{r.feature}</span> },
          { key: 'value', header: 'Student value', render: (r) => (r.value_missing ? <span className="text-subtle">Missing</span> : r.value) },
          ...(exp.model === 'random_forest' ? [{ key: 'reference', header: 'Typical value (reference)' }] : []),
          { key: 'contribution', header: `Contribution (${exp.unit})`, align: 'right', render: (r) => (r.contribution === null ? 'Not explained' : r.contribution.toFixed(4)) },
          { key: 'effect', header: 'Direction', render: (r) => ({ toward: 'Toward prediction', away: 'Away from prediction', none: 'No change', not_explained: 'Not explained' }[r.effect]) },
        ]} />
    </div>
  );
}

function ExplainContent() {
  const { metrics } = useAppStore();
  const [params, setParams] = useSearchParams();
  const rowParam = params.get('row');
  const rowId = rowParam !== null && rowParam !== '' && !Number.isNaN(Number(rowParam)) ? Number(rowParam) : null;
  const [model, setModel] = useState('selected');
  const [rowInput, setRowInput] = useState(rowId !== null ? String(rowId + 1) : '');
  useEffect(() => { setRowInput(rowId !== null ? String(rowId + 1) : ''); }, [rowId]);
  const options = [{ value: 'selected', label: `Selected model (${metrics.models[metrics.selection.selected].label})` },
    ...Object.keys(metrics.models).map((k) => ({ value: k, label: metrics.models[k].label }))];
  const resolvedModel = model === 'selected' ? metrics.selection.selected : model;

  const lookup = (e) => {
    e.preventDefault();
    const n = Number(rowInput);
    if (Number.isInteger(n) && n >= 1) setParams({ row: String(n - 1) });
  };

  return (
    <div className="space-y-6">
      <div className="max-w-sm">
        <SelectField label="Model to explain" value={model} onChange={setModel} options={options} />
      </div>
      <GlobalImportance model={resolvedModel} />
      <Card title="Individual student explanation" subtitle="Why the model produced its estimate for one student. Global importance is never used as an individual reason.">
        <form onSubmit={lookup} className="mb-5 flex flex-wrap items-end gap-3">
          <TextField label="Row number in the file (1 = first data row)" type="number" min={1} value={rowInput} onChange={setRowInput} className="w-64" />
          <Button type="submit" variant="secondary" icon={Search}>Explain</Button>
        </form>
        <LocalExplanation model={resolvedModel} rowId={rowId} />
      </Card>
    </div>
  );
}

export default function Explainability() {
  return (
    <>
      <TopBar eyebrow="Step 5 · Explain" title="Explainability"
        description="How the models use each column overall, and how one student's estimate was formed. Explanations describe the model, not causes." />
      <StageGate requires="trained">
        <ExplainContent />
      </StageGate>
    </>
  );
}
