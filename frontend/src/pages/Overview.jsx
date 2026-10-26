import { Link } from 'react-router-dom';
import {
  AlertTriangle, BarChart3, Cpu, Download, Eye, HandHeart, Lock, Target, UploadCloud,
} from 'lucide-react';
import TopBar from '../components/TopBar';
import Card from '../components/Card';
import Button, { buttonClass } from '../components/Button';
import Badge, { RiskBadge } from '../components/Badge';
import ErrorBanner from '../components/ErrorBanner';
import Loader from '../components/Loader';
import KpiCard, { formatScore } from '../components/KpiCard';
import PlotCard from '../components/PlotCard';
import DataTable from '../components/DataTable';
import TargetSetup from '../components/TargetSetup';
import { DatasetKpis, IssueList } from '../components/DatasetProfile';
import { EdaKpis, TargetDistributionCard } from './StudentAnalytics';
import { SelectionCard, TrainPanel } from './ModelPerformance';
import { GeneratePanel } from './RiskPredictions';
import { useAppStore } from '../hooks/AppStore';
import { useAction, useApiData } from '../hooks/useApi';
import { api } from '../services/api';
import * as charts from '../charts/builders';

const WORKFLOW = ['Upload CSV', 'Validate', 'Select target', 'Explore', 'Train models', 'Compare', 'Predict', 'Explain', 'Recommend support', 'Export'];

const UNLOCKS = [
  { icon: BarChart3, title: 'Student Analytics', text: 'Distributions, missing values, correlations and outcome comparisons, after you confirm a target column.' },
  { icon: Cpu, title: 'Model Performance', text: 'Logistic Regression and Random Forest metrics on a held-out test split, after training.' },
  { icon: AlertTriangle, title: 'Risk Predictions', text: 'Per-student model-estimated risk with configurable thresholds, after generating predictions.' },
  { icon: Eye, title: 'Explainability', text: 'Global permutation importance and per-student explanations, after training.' },
  { icon: HandHeart, title: 'Interventions', text: 'Rule-based support suggestions for staff review, using only columns present in your data.' },
  { icon: Download, title: 'Export', text: 'CSV downloads of predictions and suggestions, generated from your session.' },
];

// State A: no dataset at all. Nothing data-related is shown.
function WelcomeState() {
  return (
    <div className="space-y-6">
      <section className="rounded-card border border-line bg-card p-8 shadow-card">
        <p className="text-xs font-bold uppercase tracking-wide text-forest">Welcome to ScholarSense</p>
        <h2 className="mt-2 font-display text-2xl font-bold tracking-tight text-ink">Turning Student Data into Student Success</h2>
        <p className="mt-2 max-w-2xl text-muted">
          Upload a CSV of student records to explore it, train two transparent models, estimate dropout risk,
          understand each prediction and plan supportive follow-up. Every number you will see is computed from your file.
        </p>
        <Link to="/upload" className={buttonClass('primary', 'lg', 'mt-5')}>
          <UploadCloud className="h-4 w-4" aria-hidden="true" /> Upload Dataset
        </Link>
        <ol className="mt-6 flex flex-wrap gap-2" aria-label="Workflow">
          {WORKFLOW.map((step, i) => (
            <li key={step} className="flex items-center gap-2 rounded-full border border-line bg-canvas px-3 py-1 text-xs font-semibold text-muted">
              <span className="flex h-5 w-5 items-center justify-center rounded-full bg-mint-soft text-forest">{i + 1}</span>{step}
            </li>
          ))}
        </ol>
      </section>
      <div>
        <h2 className="mb-3 font-display text-lg font-semibold text-ink">What unlocks after upload</h2>
        <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
          {UNLOCKS.map(({ icon: Icon, title, text }) => (
            <li key={title} className="rounded-card border border-dashed border-line-strong bg-card p-5">
              <p className="flex items-center gap-2 font-semibold text-ink">
                <Icon className="h-4 w-4 text-forest" aria-hidden="true" /> {title}
                <Lock className="ml-auto h-3.5 w-3.5 text-subtle" aria-label="Locked" />
              </p>
              <p className="mt-1 text-sm text-muted">{text}</p>
            </li>
          ))}
        </ul>
      </div>
    </div>
  );
}

// State B: uploaded, not analysed.
function UploadedState() {
  const { summary, stage, runAnalysis, datasetVersion } = useAppStore();
  const analyze = useAction(runAnalysis);
  return (
    <div className="space-y-6">
      <DatasetKpis summary={summary} />
      <Card title="Data quality" subtitle={`From ${summary.dataset.filename}`}>
        <IssueList issues={summary.profile.issues} />
      </Card>
      <TargetSetup key={datasetVersion} />
      <Card title="Analyse the dataset" subtitle={stage === 'uploaded' ? 'Confirm the target column above to enable analysis.' : 'Compute statistics and charts for every detected column.'}>
        <Button icon={BarChart3} onClick={analyze.run} loading={analyze.pending} disabled={stage === 'uploaded'}>Analyze</Button>
        {analyze.error && <div className="mt-3"><ErrorBanner error={analyze.error} onDismiss={analyze.clearError} /></div>}
      </Card>
    </div>
  );
}

// State C: analysed, not trained.
function AnalyzedState() {
  const { analysis } = useAppStore();
  const assoc = analysis.association.slice(0, 8);
  return (
    <div className="space-y-6">
      <EdaKpis analysis={analysis} />
      <div className="grid gap-6 xl:grid-cols-2">
        <TargetDistributionCard analysis={analysis} />
        <PlotCard title="Strongest associations with the target" subtitle="Descriptive only (η² numeric, Cramér's V categorical). Not causation."
          unavailable={assoc.length ? null : { reason: 'No feature had enough data to compute an association.' }}
          figure={assoc.length ? charts.horizontalBars(assoc.map((a) => a.column), assoc.map((a) => a.score), { valueLabel: 'Association', textFormat: (v) => v.toFixed(2) }) : null} />
      </div>
      <TrainPanel />
      <Link className={buttonClass('secondary')} to="/analytics">Open full Student Analytics</Link>
    </div>
  );
}

// State D: trained, not predicted.
function TrainedState() {
  const { metrics } = useAppStore();
  const sel = metrics.models[metrics.selection.selected];
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label={`Recall · ${metrics.at_risk_class}`} value={formatScore(sel.at_risk.recall)} icon={Target} hint={`${sel.label}, held-out test set`} tone="accent" />
        <KpiCard label={`Precision · ${metrics.at_risk_class}`} value={formatScore(sel.at_risk.precision)} hint={`${sel.at_risk.false_alarms} false alarm(s) of ${sel.at_risk.flagged} flagged`} />
        <KpiCard label="Macro-F1" value={formatScore(sel.macro_f1)} hint="Unweighted mean over classes" />
        <KpiCard label="Accuracy" value={formatScore(sel.accuracy)} hint={`${metrics.n_test} test rows`} />
      </div>
      <SelectionCard metrics={metrics} />
      <div className="grid gap-6 xl:grid-cols-2">
        <GeneratePanel />
        <Card title="Explain the models" subtitle="See which columns matter overall and why individual estimates were made.">
          <Link className={buttonClass('secondary')} to="/explainability"><Eye className="h-4 w-4" aria-hidden="true" /> Open Explainability</Link>
        </Card>
      </div>
    </div>
  );
}

// State E: predictions generated.
function PredictedState() {
  const { resultsVersion, summary } = useAppStore();
  const split = summary.predictions?.scope === 'test' ? 'test' : 'all';
  const q = useApiData(() => api.listPredictions({ split, page_size: 10, sort: 'risk_desc' }), [resultsVersion, split]);
  if (q.error) return <ErrorBanner error={q.error} onRetry={q.reload} />;
  if (!q.data) return <Loader label="Loading predictions…" />;
  const { meta, summary: s, rows } = q.data;
  return (
    <div className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <KpiCard label="Students scored" value={s.total.toLocaleString()} hint={split === 'test' ? 'Held-out test rows' : 'All scored rows (includes in-sample)'} />
        <KpiCard label="High risk" value={(s.by_risk_category.High || 0).toLocaleString()} icon={AlertTriangle} hint={`Risk score ≥ ${meta.thresholds.high}`} />
        <KpiCard label="Medium risk" value={(s.by_risk_category.Medium || 0).toLocaleString()} hint={`${meta.thresholds.low} to ${meta.thresholds.high}`} />
        <KpiCard label="Mean risk score" value={formatScore(s.mean_risk_score)} hint={`P(${meta.at_risk_class}), uncalibrated`} />
      </div>
      <div className="grid gap-6 xl:grid-cols-2">
        <PlotCard title="Predicted class distribution" subtitle={`${meta.model_label} · model estimates, not confirmed outcomes`} figure={charts.classCounts(s.by_predicted_class, meta.classes)} />
        <PlotCard title="Risk categories" subtitle="Model-estimated risk, not a calibrated probability" figure={charts.riskCategoryChart(s.by_risk_category)} />
      </div>
      <Card title="Highest estimated risk" subtitle="Top 10 by risk score."
        actions={<Link className={buttonClass('secondary', 'sm')} to="/predictions">Search all predictions</Link>}>
        <DataTable caption="Highest estimated risk" rowKey={(r) => r.row_id} rows={rows}
          columns={[
            { key: 'identifier', header: meta.id_column || 'Row', render: (r) => <span className="font-medium">{r.identifier}</span> },
            { key: 'predicted_class', header: 'Predicted class', render: (r) => <Badge>{r.predicted_class}</Badge> },
            { key: 'risk_score', header: 'Risk score', align: 'right', render: (r) => formatScore(r.risk_score) },
            { key: 'risk', header: 'Risk', render: (r) => <RiskBadge category={r.risk_category} /> },
            { key: 'links', header: 'Next steps', render: (r) => (
              <span className="flex gap-3 text-xs font-semibold">
                <Link className="text-forest hover:underline" to={`/explainability?row=${r.row_id}`}>Explanation</Link>
                <Link className="text-forest hover:underline" to={`/interventions?row=${r.row_id}`}>Support</Link>
              </span>
            ) },
          ]} />
      </Card>
    </div>
  );
}

const STATE_COPY = {
  empty: 'Upload a dataset to get started.',
  uploaded: 'Your file is loaded. Review data quality and confirm the target column.',
  configured: 'Target confirmed. Run the analysis to explore the data.',
  analyzed: 'Analysis ready. Train the models next.',
  trained: 'Models trained. Generate predictions or explore explanations.',
  predicted: 'Predictions ready. Review risk, explanations and support suggestions.',
};

export default function Overview() {
  const { stage, summary, analysis, metrics } = useAppStore();
  let content;
  if (stage === 'empty') content = <WelcomeState />;
  else if (stage === 'uploaded' || stage === 'configured') content = <UploadedState />;
  else if (stage === 'analyzed' && analysis) content = <AnalyzedState />;
  else if (stage === 'trained' && metrics) content = <TrainedState />;
  else if (stage === 'predicted' && metrics) content = <PredictedState />;
  else content = <Loader />;
  return (
    <>
      <TopBar eyebrow={summary?.dataset ? `Dataset · ${summary.dataset.filename}` : 'Overview'} title="Student Analytics Overview"
        description={STATE_COPY[stage]}
        actions={stage !== 'empty' && (
          <Link to="/upload" className={buttonClass('secondary')}><UploadCloud className="h-4 w-4" aria-hidden="true" /> Upload new dataset</Link>
        )} />
      {content}
    </>
  );
}
