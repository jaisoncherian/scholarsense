import { useEffect, useMemo, useState } from 'react';
import { CheckCircle2, Target } from 'lucide-react';
import Card from './Card';
import Button from './Button';
import Badge from './Badge';
import Notice from './Notice';
import ErrorBanner from './ErrorBanner';
import { SelectField } from './Field';
import { Spinner } from './Loader';
import { api } from '../services/api';
import { useAppStore } from '../hooks/AppStore';
import { useAction } from '../hooks/useApi';

const REASON_LABELS = {
  target: 'Target column',
  student_identifier: 'Student identifier (display only)',
  constant: 'Single value: no information',
  datetime_not_supported: 'Date column: not used as a feature',
  id_like: 'Looks like an ID: excluded by default',
  user_excluded: 'Excluded by you',
  later_term: 'Not available at prediction time',
};
const LOCKED_REASONS = ['target', 'student_identifier', 'constant', 'datetime_not_supported', 'later_term'];

function sameConfig(a, b) {
  return JSON.stringify(a) === JSON.stringify(b);
}

// Target confirmation + feature selection with explicit leakage / prediction-timing controls.
// The target is never auto-selected: suggestions are shown, the user must pick and confirm.
export default function TargetSetup({ onConfirmed }) {
  const { summary, confirmTarget } = useAppStore();
  const columns = summary.profile.columns;
  const existing = summary.config;
  const firstId = columns.find((c) => c.type === 'identifier');

  const [target, setTarget] = useState(existing?.target || '');
  const [idColumn, setIdColumn] = useState(existing ? existing.id_column || '' : firstId?.name || '');
  const [excluded, setExcluded] = useState(existing?.excluded_columns || []);
  const [includeIdLike, setIncludeIdLike] = useState(existing?.include_id_like || []);
  const [timing, setTiming] = useState(existing?.timing_preset || 'all');
  const [atRisk, setAtRisk] = useState(existing?.at_risk_class || '');
  const [check, setCheck] = useState(null);
  const [checkError, setCheckError] = useState(null);
  const [checking, setChecking] = useState(false);
  const confirm = useAction(confirmTarget);

  const body = useMemo(() => ({
    target, id_column: idColumn || null, excluded_columns: excluded, include_id_like: includeIdLike,
    timing_preset: timing,
  }), [target, idColumn, excluded, includeIdLike, timing]);

  useEffect(() => {
    if (!target) {
      setCheck(null);
      setCheckError(null);
      return undefined;
    }
    let cancelled = false;
    setChecking(true);
    api.checkTarget(body)
      .then((res) => {
        if (cancelled) return;
        setCheck(res);
        setCheckError(null);
        const classes = res.target_info.classes;
        setAtRisk((current) => (classes.includes(current) ? current : res.target_info.suggested_at_risk_class || ''));
      })
      .catch((err) => { if (!cancelled) { setCheck(null); setCheckError(err); } })
      .finally(() => { if (!cancelled) setChecking(false); });
    return () => { cancelled = true; };
  }, [body]);

  const chooseTarget = (value) => {
    setTarget(value);
    setExcluded((list) => list.filter((c) => c !== value));
    setIncludeIdLike((list) => list.filter((c) => c !== value));
    if (idColumn === value) setIdColumn('');
  };

  const confirmedNow = existing && sameConfig(
    { ...body, at_risk_class: atRisk },
    { target: existing.target, id_column: existing.id_column, excluded_columns: existing.excluded_columns,
      include_id_like: existing.include_id_like, timing_preset: existing.timing_preset, at_risk_class: existing.at_risk_class },
  );

  const info = check?.target_info;
  const features = check?.feature_config;
  const exclusionReason = Object.fromEntries((features?.exclusions || []).map((e) => [e.column, e.reason]));
  const featureSet = new Set(features?.features || []);
  const candidates = summary.profile.target_candidates || [];
  const laterTerm = columns.filter((c) => c.flags.includes('later_term') && c.name !== target).map((c) => c.name);

  const toggleFeature = (col) => {
    const reason = exclusionReason[col.name];
    if (reason === 'id_like' || (col.type === 'identifier' && featureSet.has(col.name))) {
      setIncludeIdLike((list) => (list.includes(col.name) ? list.filter((c) => c !== col.name) : [...list, col.name]));
    } else {
      setExcluded((list) => (list.includes(col.name) ? list.filter((c) => c !== col.name) : [...list, col.name]));
    }
  };

  const submit = async () => {
    const res = await confirm.run({ ...body, at_risk_class: atRisk });
    if (res && onConfirmed) onConfirmed(res);
  };

  return (
    <Card id="target-setup" title="Target and feature configuration"
      subtitle="Choose the outcome column you want to predict, the class that means 'at risk', and which columns the models may use."
      actions={confirmedNow ? <Badge tone="mint"><CheckCircle2 className="h-3.5 w-3.5" aria-hidden="true" /> Confirmed</Badge> : existing ? <Badge tone="warning">Unsaved changes</Badge> : <Badge tone="warning">Not confirmed</Badge>}>
      <div className="space-y-5">
        <div className="grid gap-4 md:grid-cols-3">
          <SelectField label="Target (outcome) column" value={target} onChange={chooseTarget} placeholder="Select the outcome column…"
            options={columns.map((c) => ({ value: c.name, label: c.name }))}
            hint="Required. Nothing is selected automatically." />
          <SelectField label="At-risk class" value={atRisk} onChange={setAtRisk} disabled={!info} placeholder={info ? 'Choose the at-risk class…' : 'Select a target first'}
            options={(info?.classes || []).map((c) => ({ value: c, label: c === info?.suggested_at_risk_class ? `${c} (suggested by name)` : c }))}
            hint="Risk score = predicted probability of this class." />
          <SelectField label="Student identifier (display only)" value={idColumn} onChange={setIdColumn} placeholder="None (use row numbers)"
            options={columns.filter((c) => c.name !== target).map((c) => ({ value: c.name, label: c.type === 'identifier' ? `${c.name} (ID-like)` : c.name }))}
            hint="Shown in predictions; never used as a feature." />
        </div>

        {candidates.length > 0 && !target && (
          <div className="flex flex-wrap items-center gap-2 text-sm text-muted">
            <span>Suggested by column name:</span>
            {candidates.map((c) => (
              <button key={c.name} type="button" onClick={() => chooseTarget(c.name)}
                className="rounded-full border border-line-strong bg-card px-3 py-1 text-xs font-semibold text-forest hover:bg-mint-soft focus:outline-none focus-visible:ring-2 focus-visible:ring-mint">
                Use “{c.name}” {c.match === 'exact' ? '(exact match)' : '(partial match)'}
              </button>
            ))}
          </div>
        )}

        {checking && <Spinner label="Validating target…" />}
        {checkError && <ErrorBanner title="This configuration cannot be used" error={checkError} />}

        {info && (
          <div className="rounded-xl border border-line bg-canvas p-4">
            <p className="text-xs font-semibold uppercase tracking-wide text-muted">Class distribution in “{info.target}”</p>
            <ul className="mt-2 flex flex-wrap gap-2">
              {info.classes.map((cls) => (
                <li key={cls}>
                  <Badge tone={cls === atRisk ? 'High' : 'neutral'}>{cls}: {info.class_counts[cls]} rows{cls === atRisk ? ' · at-risk class' : ''}</Badge>
                </li>
              ))}
            </ul>
            {info.warnings.map((w) => <Notice key={w.code} tone="warning" className="mt-3">{w.message}{w.classes ? ` (${w.classes.join(', ')})` : ''}</Notice>)}
          </div>
        )}

        {features && (
          <>
            <fieldset className="rounded-xl border border-line p-4">
              <legend className="px-1 text-sm font-semibold text-ink">Prediction timing</legend>
              <div className="mt-1 grid gap-3 md:grid-cols-2">
                {[
                  { value: 'all', title: 'Use all columns', text: 'Every selected column is used, including any that may only be known later in the programme.' },
                  { value: 'exclude_later', title: 'Exclude columns not available at prediction time', text: 'Removes columns flagged as possible later-term information (names containing 2nd, second, semester 2, sem2, final).' },
                ].map((opt) => (
                  <label key={opt.value} className={`flex cursor-pointer gap-3 rounded-xl border p-3 ${timing === opt.value ? 'border-forest bg-mint-soft' : 'border-line-strong bg-card'}`}>
                    <input type="radio" name="timing" value={opt.value} checked={timing === opt.value} onChange={() => setTiming(opt.value)} className="mt-1 accent-[#2E5A44]" />
                    <span>
                      <span className="block text-sm font-semibold text-ink">{opt.title}</span>
                      <span className="block text-xs text-muted">{opt.text}</span>
                    </span>
                  </label>
                ))}
              </div>
              {laterTerm.length > 0 && (
                <Notice tone="warning" className="mt-3" title="Possible later-term information">
                  These columns look like they are only known later (e.g. second-semester or final results): {laterTerm.join(', ')}.
                  Results are only described as early prediction when they are excluded.
                </Notice>
              )}
              <p className="mt-3 text-sm text-ink"><span className="font-semibold">Timing label used for training:</span> {features.timing_label}</p>
            </fieldset>

            <div>
              <div className="mb-2 flex flex-wrap items-baseline justify-between gap-2">
                <h3 className="text-sm font-semibold text-ink">Feature selection</h3>
                <p className="text-sm text-muted">{features.features.length} of {columns.length - 1} columns will be used as features</p>
              </div>
              {features.warnings.map((w) => (
                <Notice key={w.code + (w.column || '')} tone="warning" className="mb-2">{w.message}{w.columns ? ` (${w.columns.join(', ')})` : ''}</Notice>
              ))}
              <div className="max-h-96 overflow-y-auto rounded-xl border border-line">
                <ul className="divide-y divide-line">
                  {columns.filter((c) => c.name !== target).map((col) => {
                    const reason = exclusionReason[col.name];
                    const included = featureSet.has(col.name);
                    const locked = LOCKED_REASONS.includes(reason);
                    return (
                      <li key={col.name} className="flex flex-wrap items-center gap-3 px-3 py-2">
                        <input id={`feat-${col.name}`} type="checkbox" checked={included} disabled={locked}
                          onChange={() => toggleFeature(col)} className="h-4 w-4 accent-[#2E5A44]" />
                        <label htmlFor={`feat-${col.name}`} className="min-w-0 flex-1 truncate text-sm text-ink">{col.name}</label>
                        <Badge>{col.type}</Badge>
                        {col.flags.includes('later_term') && <Badge tone="warning">Possible later-term info</Badge>}
                        {col.flags.includes('high_cardinality') && <Badge tone="olive">Many categories</Badge>}
                        {col.flags.includes('mostly_missing') && <Badge tone="olive">Mostly missing</Badge>}
                        {reason && <span className="text-xs text-muted">{REASON_LABELS[reason]}</span>}
                        {!reason && col.type === 'identifier' && <span className="text-xs font-semibold text-risk-medium-text">ID-like column included</span>}
                      </li>
                    );
                  })}
                </ul>
              </div>
            </div>
          </>
        )}

        {confirm.error && <ErrorBanner title="Could not confirm the configuration" error={confirm.error} onDismiss={confirm.clearError} />}
        <div className="flex flex-wrap items-center gap-3">
          <Button icon={Target} onClick={submit} loading={confirm.pending} disabled={!info || !atRisk || !!checkError || checking || confirmedNow}>
            {existing ? 'Save configuration' : 'Confirm target and features'}
          </Button>
          {existing && !confirmedNow && (
            <p className="text-xs text-muted">Saving a changed configuration clears the analysis, models and predictions built on the previous one.</p>
          )}
          {!atRisk && info && <p className="text-xs text-muted">Choose the at-risk class to continue.</p>}
        </div>
      </div>
    </Card>
  );
}
