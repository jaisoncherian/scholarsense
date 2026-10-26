import { useState } from 'react';
import { Link } from 'react-router-dom';
import { Award, Cpu, Scale, Target } from 'lucide-react';
import TopBar from '../components/TopBar';
import StageGate from '../components/StageGate';
import Card from '../components/Card';
import Button, { buttonClass } from '../components/Button';
import Badge from '../components/Badge';
import Notice from '../components/Notice';
import ErrorBanner from '../components/ErrorBanner';
import KpiCard, { formatNumber, formatScore } from '../components/KpiCard';
import DataTable from '../components/DataTable';
import PlotCard from '../components/PlotCard';
import FeatureListCard from '../components/FeatureListCard';
import { SelectField, TextField } from '../components/Field';
import { useAppStore } from '../hooks/AppStore';
import { useAction } from '../hooks/useApi';
import { confusionMatrix } from '../charts/builders';

const MODEL_ORDER = ['logistic_regression', 'random_forest'];

export function TrainPanel({ compact = false }) {
  const { train, metrics } = useAppStore();
  const prev = metrics?.params;
  const [testSize, setTestSize] = useState(String(prev?.test_size ?? 0.2));
  const [lrWeight, setLrWeight] = useState(prev?.lr_class_weight ?? 'balanced');
  const [rfWeight, setRfWeight] = useState(prev?.rf_class_weight ?? 'balanced');
  const [trees, setTrees] = useState(prev?.rf_n_estimators ? String(prev.rf_n_estimators) : '');
  const action = useAction(train);
  const weightOptions = [{ value: 'balanced', label: 'Balanced (reweights rare classes)' }, { value: 'none', label: 'None' }];
  const submit = () => action.run({
    test_size: Number(testSize), lr_class_weight: lrWeight, rf_class_weight: rfWeight,
    ...(trees ? { rf_n_estimators: Number(trees) } : {}),
  });
  return (
    <Card title={metrics ? 'Retrain models' : 'Train models'}
      subtitle="Logistic Regression and Random Forest are trained on the same stratified training split and evaluated on the same untouched test split.">
      {!compact && (
        <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <SelectField label="Test set size" value={testSize} onChange={setTestSize}
            options={['0.1', '0.15', '0.2', '0.25', '0.3', '0.4', '0.5'].map((v) => ({ value: v, label: `${Math.round(Number(v) * 100)}% held out` }))} />
          <SelectField label="Logistic Regression class weight" value={lrWeight} onChange={setLrWeight} options={weightOptions} />
          <SelectField label="Random Forest class weight" value={rfWeight} onChange={setRfWeight} options={weightOptions} />
          <TextField label="Random Forest trees (10–300)" type="number" min={10} max={300} value={trees} onChange={setTrees}
            placeholder="Automatic" hint="Blank = 200 (100 for very large data)." />
        </div>
      )}
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <Button icon={Cpu} onClick={submit} loading={action.pending}>{action.pending ? 'Training…' : metrics ? 'Retrain models' : 'Train models'}</Button>
        <span className="text-xs text-muted">Random seed 42 · preprocessing is fitted inside each pipeline on training rows only.</span>
      </div>
      {action.error && <div className="mt-3"><ErrorBanner title="Training failed" error={action.error} onDismiss={action.clearError} /></div>}
    </Card>
  );
}

export function SelectionCard({ metrics }) {
  const sel = metrics.selection;
  return (
    <Card title="Model selection" subtitle="Transparent criteria applied to the held-out test results."
      actions={sel.selected && <Badge tone="mint"><Award className="h-3.5 w-3.5" aria-hidden="true" /> Selected: {metrics.models[sel.selected].label}</Badge>}>
      <p className="text-sm text-ink"><span className="font-semibold">Criteria:</span> {sel.criteria}</p>
      <ol className="mt-3 list-decimal space-y-1 pl-5 text-sm text-muted">
        {sel.steps.map((s) => <li key={s}>{s}</li>)}
      </ol>
      <div className="mt-4">
        <DataTable caption="Model comparison on the test set" dense rowKey={(r) => r.model} rows={sel.comparison}
          highlightRow={(r) => r.model === sel.selected}
          columns={[
            { key: 'label', header: 'Model', render: (r) => <span className="font-semibold">{r.label}</span> },
            { key: 'at_risk_recall', header: `Recall (${metrics.at_risk_class})`, align: 'right', render: (r) => formatScore(r.at_risk_recall) },
            { key: 'at_risk_precision', header: `Precision (${metrics.at_risk_class})`, align: 'right', render: (r) => formatScore(r.at_risk_precision) },
            { key: 'macro_f1', header: 'Macro-F1', align: 'right', render: (r) => formatScore(r.macro_f1) },
            { key: 'weighted_f1', header: 'Weighted F1', align: 'right', render: (r) => formatScore(r.weighted_f1) },
            { key: 'accuracy', header: 'Accuracy', align: 'right', render: (r) => formatScore(r.accuracy) },
          ]} />
      </div>
      {Object.entries(metrics.failures || {}).map(([k, msg]) => <Notice key={k} tone="warning" className="mt-3">{msg}</Notice>)}
    </Card>
  );
}

function ModelDetail({ modelKey, m, metrics }) {
  const ar = m.at_risk;
  return (
    <Card title={m.label} subtitle={`${formatNumber(m.n_train)} training rows · ${formatNumber(m.n_test)} test rows`}
      actions={metrics.selection.selected === modelKey && <Badge tone="mint">Selected</Badge>}>
      <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
        <KpiCard label="Accuracy" value={formatScore(m.accuracy)} />
        <KpiCard label="Macro precision" value={formatScore(m.macro_precision)} />
        <KpiCard label="Macro recall" value={formatScore(m.macro_recall)} />
        <KpiCard label="Macro-F1" value={formatScore(m.macro_f1)} hint={`Weighted F1 ${formatScore(m.weighted_f1)}`} />
      </div>
      <div className="mt-4 rounded-xl border border-mint bg-mint-soft p-4">
        <p className="flex items-center gap-2 text-sm font-semibold text-forest"><Target className="h-4 w-4" aria-hidden="true" /> At-risk class “{ar.class}” ({ar.support} test rows)</p>
        <dl className="mt-2 grid grid-cols-2 gap-3 text-sm md:grid-cols-4">
          <div><dt className="text-muted">Recall (share found)</dt><dd className="font-display text-xl font-bold tabular-nums">{formatScore(ar.recall)}</dd></div>
          <div><dt className="text-muted">Precision</dt><dd className="font-display text-xl font-bold tabular-nums">{formatScore(ar.precision)}</dd></div>
          <div><dt className="text-muted">False alarms</dt><dd className="font-display text-xl font-bold tabular-nums">{ar.false_alarms} of {ar.flagged} flagged</dd></div>
          <div><dt className="text-muted">Missed</dt><dd className="font-display text-xl font-bold tabular-nums">{ar.missed} of {ar.support}</dd></div>
        </dl>
      </div>
      <p className="mt-3 flex items-start gap-2 text-xs text-muted"><Scale className="mt-0.5 h-3.5 w-3.5 flex-none" aria-hidden="true" />{m.averaging}</p>
      <div className="mt-4 grid gap-4 xl:grid-cols-2">
        <DataTable caption={`Per-class metrics for ${m.label}`} dense rowKey={(r) => r.class} rows={m.per_class}
          highlightRow={(r) => r.class === ar.class}
          columns={[
            { key: 'class', header: 'Class', render: (r) => <span className="font-medium">{r.class}</span> },
            { key: 'precision', header: 'Precision', align: 'right', render: (r) => formatScore(r.precision) },
            { key: 'recall', header: 'Recall', align: 'right', render: (r) => formatScore(r.recall) },
            { key: 'f1', header: 'F1', align: 'right', render: (r) => formatScore(r.f1) },
            { key: 'support', header: 'Support', align: 'right' },
          ]} />
        <PlotCard title="Confusion matrix" subtitle={m.confusion_matrix.axes} className="shadow-none" height={300}
          figure={confusionMatrix(m.confusion_matrix)} />
      </div>
      <details className="mt-4 rounded-xl border border-line p-3 text-sm">
        <summary className="cursor-pointer font-semibold text-ink">Full classification report</summary>
        <DataTable caption="Classification report" dense
          rows={Object.entries(m.classification_report).filter(([, v]) => typeof v === 'object').map(([k, v]) => ({ name: k, ...v }))}
          columns={[
            { key: 'name', header: 'Row' },
            { key: 'precision', header: 'Precision', align: 'right', render: (r) => formatScore(r.precision) },
            { key: 'recall', header: 'Recall', align: 'right', render: (r) => formatScore(r.recall) },
            { key: 'f1-score', header: 'F1', align: 'right', render: (r) => formatScore(r['f1-score']) },
            { key: 'support', header: 'Support', align: 'right' },
          ]} />
        {'accuracy' in m.classification_report && <p className="mt-2 text-muted">Accuracy: {formatScore(m.classification_report.accuracy)}</p>}
      </details>
    </Card>
  );
}

function PerformanceContent() {
  const { metrics } = useAppStore();
  if (!metrics) return <TrainPanel />;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Labelled rows used" value={formatNumber(metrics.labelled_rows)} hint={metrics.dropped_missing_target ? `${metrics.dropped_missing_target} row(s) without a target were dropped` : 'No rows dropped for missing target'} />
        <KpiCard label="Training rows" value={formatNumber(metrics.n_train)} hint={metrics.stratified ? 'Stratified split' : 'Random split (stratification not possible)'} />
        <KpiCard label="Test rows (held out)" value={formatNumber(metrics.n_test)} hint={`Classes: ${metrics.classes.join(', ')}`} />
        <KpiCard label="At-risk class" value={metrics.at_risk_class} hint="Emphasised in selection and risk scores" />
      </div>
      {metrics.warnings.map((w) => <Notice key={w} tone="warning">{w}</Notice>)}
      <SelectionCard metrics={metrics} />
      <FeatureListCard features={metrics.features} timingLabel={metrics.timing_label} earlyPrediction={metrics.early_prediction} />
      {MODEL_ORDER.filter((k) => metrics.models[k]).map((k) => <ModelDetail key={k} modelKey={k} m={metrics.models[k]} metrics={metrics} />)}
      <div className="flex flex-wrap gap-3">
        <Link className={buttonClass('primary')} to="/predictions">Generate predictions</Link>
        <Link className={buttonClass('secondary')} to="/explainability">View explanations</Link>
      </div>
      <TrainPanel />
    </div>
  );
}

export default function ModelPerformance() {
  return (
    <>
      <TopBar eyebrow="Step 3 · Train and compare" title="Model Performance"
        description="Every metric below is computed on the held-out test split of your uploaded data." />
      <StageGate requires="configured">
        <PerformanceContent />
      </StageGate>
    </>
  );
}
