import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCircle2, Download, HandHeart, Plus, Trash2, XCircle } from 'lucide-react';
import TopBar from '../components/TopBar';
import StageGate from '../components/StageGate';
import Card from '../components/Card';
import Button, { buttonClass } from '../components/Button';
import Badge, { RiskBadge, SplitBadge } from '../components/Badge';
import Notice from '../components/Notice';
import ErrorBanner from '../components/ErrorBanner';
import Loader from '../components/Loader';
import EmptyState from '../components/EmptyState';
import { Pagination } from '../components/DataTable';
import { SelectField, TextField } from '../components/Field';
import { formatScore } from '../components/KpiCard';
import { useAppStore } from '../hooks/AppStore';
import { useAction, useApiData } from '../hooks/useApi';
import { api } from '../services/api';

const STATUSES = ['Not reviewed', 'In review', 'Actioned', 'Dismissed'];
const DIRECTION_LABELS = {
  low: 'Low values are a concern',
  high: 'High values are a concern',
  truthy: 'Yes / 1 is a concern',
  falsy: 'No / 0 is a concern',
};
const CATEGORY_LABELS = { performance: 'Academic performance', attendance: 'Attendance', financial: 'Financial' };

function ReviewControl({ record, onSaved }) {
  const [status, setStatus] = useState(record.review.status);
  const action = useAction((value) => api.reviewIntervention(record.row_id, { status: value, note: record.review.note }));
  useEffect(() => setStatus(record.review.status), [record.review.status]);
  const change = async (value) => {
    setStatus(value);
    const res = await action.run(value);
    if (res) onSaved && onSaved(res.review);
    else setStatus(record.review.status);
  };
  return (
    <div className="w-48">
      <SelectField label="Review status" value={status} onChange={change} options={STATUSES.map((s) => ({ value: s, label: s }))} />
      {action.error && <p role="alert" className="mt-1 text-xs text-risk-high-text">{action.error.message}</p>}
    </div>
  );
}

function RecordCard({ record, highlighted, onSaved }) {
  return (
    <article className={`rounded-card border bg-card p-5 shadow-card ${highlighted ? 'border-forest ring-2 ring-mint' : 'border-line'}`} aria-label={`Support suggestions for ${record.identifier}`}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-wrap items-center gap-2">
          <h3 className="font-display text-base font-semibold text-ink">{record.identifier}</h3>
          <SplitBadge split={record.split} />
        </div>
        <ReviewControl record={record} onSaved={onSaved} />
      </div>
      <div className="mt-3 grid gap-4 lg:grid-cols-3">
        <section className="rounded-xl border border-line bg-canvas p-3 lg:col-span-2" aria-label="Observed evidence">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">Observed in the uploaded data</p>
          {record.evidence.length === 0 ? <p className="mt-2 text-sm text-muted">{record.message}</p> : (
            <ul className="mt-2 space-y-1 text-sm text-ink">
              {record.evidence.map((e) => (
                <li key={e.column}>
                  <Badge tone="olive" className="mr-2">{e.category_label}</Badge>
                  <span className="font-medium">{e.column}</span> = {e.value}: {e.comparison}{e.source === 'user' ? ' (staff mapping)' : ''}
                </li>
              ))}
            </ul>
          )}
        </section>
        <section className="rounded-xl border border-dashed border-line-strong p-3" aria-label="Model output">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{record.model_output.label}</p>
          <div className="mt-2 flex flex-wrap items-center gap-2 text-sm">
            <Badge>Predicted: {record.model_output.predicted_class}</Badge>
            <RiskBadge category={record.model_output.risk_category} />
          </div>
          <p className="mt-1 text-xs text-muted">Risk score {formatScore(record.model_output.risk_score)} (uncalibrated)</p>
        </section>
      </div>
      {record.suggestions.length > 0 && (
        <ul className="mt-3 space-y-2">
          {record.suggestions.map((s) => (
            <li key={s.rule_id} className="flex gap-2 rounded-xl bg-mint-soft p-3 text-sm text-ink">
              <HandHeart className="mt-0.5 h-4 w-4 flex-none text-forest" aria-hidden="true" />
              <span><span className="font-semibold text-forest">{s.title}.</span> {s.text} <span className="text-xs text-muted">(based on: {s.evidence_columns.join(', ')})</span></span>
            </li>
          ))}
        </ul>
      )}
    </article>
  );
}

function MappingPanel({ onChanged }) {
  const { resultsVersion } = useAppStore();
  const q = useApiData(() => api.getMapping(), [resultsVersion]);
  const [rows, setRows] = useState(null);
  const save = useAction((body) => api.putMapping(body));
  useEffect(() => { if (q.data) setRows(q.data.indicators.map((i) => ({ ...i, threshold: i.threshold ?? '' }))); }, [q.data]);
  if (q.loading || !rows) return <Loader label="Loading indicator mapping…" rows={1} />;
  if (q.error) return <ErrorBanner error={q.error} onRetry={q.reload} />;
  const candidates = q.data.candidates;
  const update = (i, key, value) => setRows((r) => r.map((row, j) => (j === i ? { ...row, [key]: value } : row)));
  const submit = async (body) => {
    const res = await save.run(body);
    if (res) { q.reload(); onChanged(); }
  };
  return (
    <div className="space-y-3">
      <p className="text-sm text-muted">
        Mode: <Badge tone={q.data.mode === 'user' ? 'olive' : 'mint'}>{q.data.mode === 'user' ? 'Staff mapping' : 'Auto-detected by column name'}</Badge>{' '}
        {q.data.note} Leave the threshold empty to use the dataset quartile (lower quartile for “low”, upper quartile for “high”).
      </p>
      {rows.length === 0 && <p className="text-sm text-muted">No indicator columns are mapped.</p>}
      {rows.map((row, i) => {
        const cand = candidates.find((c) => c.column === row.column);
        const directions = cand?.binary ? ['truthy', 'falsy'] : ['low', 'high'];
        return (
          <div key={i} className="grid items-end gap-3 rounded-xl border border-line p-3 md:grid-cols-[2fr_1.5fr_1.5fr_1fr_auto]">
            <SelectField label="Column" value={row.column} onChange={(v) => {
              const c = candidates.find((x) => x.column === v);
              update(i, 'column', v);
              update(i, 'direction', c?.binary ? 'truthy' : 'low');
            }} options={candidates.map((c) => ({ value: c.column, label: c.column }))} />
            <SelectField label="Area" value={row.category} onChange={(v) => update(i, 'category', v)}
              options={q.data.categories.map((c) => ({ value: c, label: CATEGORY_LABELS[c] }))} />
            <SelectField label="Concern when" value={row.direction} onChange={(v) => update(i, 'direction', v)}
              options={directions.map((d) => ({ value: d, label: DIRECTION_LABELS[d] }))} />
            <TextField label="Threshold" type="number" value={row.threshold} onChange={(v) => update(i, 'threshold', v)} disabled={cand?.binary} placeholder="Quartile" />
            <Button variant="ghost" icon={Trash2} aria-label={`Remove ${row.column}`} onClick={() => setRows((r) => r.filter((_, j) => j !== i))} />
          </div>
        );
      })}
      <div className="flex flex-wrap gap-2">
        <Button variant="secondary" size="sm" icon={Plus} disabled={!candidates.length}
          onClick={() => setRows((r) => [...r, { column: candidates[0].column, category: 'performance', direction: candidates[0].binary ? 'truthy' : 'low', threshold: '' }])}>
          Add indicator
        </Button>
        <Button size="sm" loading={save.pending} onClick={() => submit({ indicators: rows.map((r) => ({ ...r, threshold: r.threshold === '' ? null : Number(r.threshold) })) })}>Save mapping</Button>
        <Button variant="ghost" size="sm" onClick={() => submit({ reset: true })}>Reset to auto-detection</Button>
      </div>
      {save.error && <ErrorBanner error={save.error} onDismiss={save.clearError} />}
    </div>
  );
}

function InterventionsContent() {
  const { resultsVersion } = useAppStore();
  const [params] = useSearchParams();
  const focusRow = params.get('row');
  const [filters, setFilters] = useState({ risk: '', status: '', rule: '', q: '', page: 1 });
  const [nonce, setNonce] = useState(0);
  const q = useApiData(() => api.interventions({ ...filters, page_size: 10 }), [JSON.stringify(filters), resultsVersion, nonce]);
  const focus = useApiData(() => api.intervention(focusRow), [focusRow, resultsVersion, nonce], focusRow !== null);
  const setFilter = (key) => (value) => setFilters((f) => ({ ...f, [key]: value, page: 1 }));
  const refresh = () => setNonce((n) => n + 1);

  if (q.error) return <ErrorBanner error={q.error} onRetry={q.reload} />;
  if (!q.data) return <Loader label="Building support suggestions…" />;
  const d = q.data;
  return (
    <div className="space-y-6">
      <Notice tone="warning" title={d.disclaimer}>
        Rules use only columns found in this dataset and fire on observed values. Model output is shown separately and is an estimate, not a fact.
        Demographic attributes are never used to trigger suggestions. Please use supportive, non-punitive outreach.
      </Notice>

      <Card title="Support rules" subtitle={`${d.summary.students_with_suggestions} of ${d.summary.scored_rows} scored students have at least one suggestion.`}
        actions={<a className={buttonClass('secondary', 'sm')} href={api.exportUrl('interventions')} download><Download className="h-4 w-4" aria-hidden="true" /> Export CSV</a>}>
        <ul className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          {d.rules.map((r) => (
            <li key={r.id} className={`rounded-xl border p-3 text-sm ${r.available ? 'border-mint bg-mint-soft' : 'border-line bg-canvas'}`}>
              <p className="flex items-center gap-1.5 font-semibold text-ink">
                {r.available ? <CheckCircle2 className="h-4 w-4 text-forest" aria-hidden="true" /> : <XCircle className="h-4 w-4 text-subtle" aria-hidden="true" />}
                {r.title}
              </p>
              <p className="mt-1 text-muted">{r.available ? `${d.summary.by_rule[r.id] || 0} student(s)` : `Not shown: ${r.reason}`}</p>
            </li>
          ))}
        </ul>
        <details className="mt-4 rounded-xl border border-line p-3">
          <summary className="cursor-pointer text-sm font-semibold text-ink">Indicator column mapping ({d.indicators.length} column(s), {d.mapping_mode === 'user' ? 'staff mapping' : 'auto-detected'})</summary>
          <div className="mt-3"><MappingPanel onChanged={refresh} /></div>
        </details>
      </Card>

      {focusRow !== null && focus.data && (
        <div>
          <h2 className="mb-2 font-display text-lg font-semibold text-ink">Selected student</h2>
          <RecordCard record={focus.data.record} highlighted onSaved={refresh} />
        </div>
      )}
      {focusRow !== null && focus.error && <ErrorBanner error={focus.error} />}

      <Card title="Students with suggestions" subtitle="Sorted by model-estimated risk (highest first).">
        <div className="mb-4 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
          <SelectField label="Risk category" value={filters.risk} onChange={setFilter('risk')} placeholder="All" options={['High', 'Medium', 'Low'].map((c) => ({ value: c, label: `${c} risk` }))} />
          <SelectField label="Review status" value={filters.status} onChange={setFilter('status')} placeholder="All" options={STATUSES.map((s) => ({ value: s, label: `${s} (${d.summary.by_status[s]})` }))} />
          <SelectField label="Suggestion" value={filters.rule} onChange={setFilter('rule')} placeholder="All" options={d.rules.filter((r) => r.available).map((r) => ({ value: r.id, label: r.title }))} />
          <TextField label="Search identifier" value={filters.q} onChange={setFilter('q')} placeholder="Type to search…" />
        </div>
        {d.records.length === 0 ? (
          <EmptyState compact icon={HandHeart} title="No suggestions match"
            description={d.indicators.length === 0 ? 'No performance, attendance or financial indicator columns were detected. Map columns above if they exist under other names.' : 'Try different filters.'} />
        ) : (
          <div className="space-y-4">
            {d.records.map((r) => <RecordCard key={r.row_id} record={r} highlighted={String(r.row_id) === focusRow} onSaved={refresh} />)}
          </div>
        )}
        <Pagination page={d.page} pages={d.pages} total={d.total} label="students" onPage={(p) => setFilters((f) => ({ ...f, page: p }))} />
      </Card>
    </div>
  );
}

export default function Interventions() {
  return (
    <>
      <TopBar eyebrow="Step 6 · Support" title="Interventions"
        description="Rule-based support suggestions for staff review, grounded in observed data and shown alongside, but separate from, the model's estimate." />
      <StageGate requires="predicted">
        <InterventionsContent />
      </StageGate>
    </>
  );
}
