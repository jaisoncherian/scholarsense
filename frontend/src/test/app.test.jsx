import { render, screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import App from '../App';

vi.mock('../charts/PlotlyChart', () => ({ default: () => <div data-testid="plot" /> }));

// Synthetic API payloads shaped like the backend responses.
function column(name, type, extra = {}) {
  return { name, type, dtype: 'object', missing: 0, missing_pct: 0, unique: 3, unique_ratio: 0.1, flags: [], notes: null, examples: [], ...extra };
}

function uploadedSummary(filename, rows, columns) {
  return {
    stage: 'uploaded',
    dataset: { filename, size_bytes: 2048, rows, columns: columns.length, encoding: 'utf-8', delimiter: 'comma', uploaded_at: Math.random() },
    profile: {
      columns,
      issues: [],
      type_counts: {},
      duplicate_rows: 0,
      missing_cells: 0,
      missing_cells_pct: 0,
      columns_with_missing: 0,
      target_candidates: columns.filter((c) => c.name === 'outcome').map((c) => ({ name: c.name, match: 'exact' })),
    },
    target_check: null,
    config: null,
    thresholds: { low: 0.33, high: 0.66 },
    analysis_available: false,
    training: null,
    predictions: null,
  };
}

const FIRST = uploadedSummary('first_cohort.csv', 120, [
  column('student_id', 'identifier', { flags: ['id_like'] }),
  column('grade', 'numeric'),
  column('outcome', 'categorical'),
]);
const SECOND = uploadedSummary('second_file.csv', 48, [column('score', 'numeric'), column('label', 'categorical')]);

function jsonResponse(body, status = 200) {
  return Promise.resolve(new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }));
}

// Minimal in-memory fake of the API keyed by "METHOD /path".
function installFetch(routes) {
  const calls = [];
  const fetchMock = vi.fn((url, init = {}) => {
    const method = init.method || 'GET';
    const path = new URL(url, 'http://localhost').pathname;
    const key = `${method} ${path}`;
    calls.push({ key, init });
    const handler = routes[key];
    if (!handler) return jsonResponse({ error: { code: 'not_found', message: `No mock for ${key}`, details: null } }, 404);
    const result = typeof handler === 'function' ? handler(init) : handler;
    return jsonResponse(result.body ?? result, result.status ?? 200);
  });
  vi.stubGlobal('fetch', fetchMock);
  return calls;
}

function renderAt(path) {
  return render(
    <MemoryRouter initialEntries={[path]}>
      <App />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.unstubAllGlobals();
});

describe('empty state', () => {
  it('shows a welcome message, upload button and no data or metrics', async () => {
    installFetch({ 'GET /api/dataset/summary': { stage: 'empty' } });
    renderAt('/');
    expect(await screen.findByText('Turning Student Data into Student Success')).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /upload dataset/i })).toHaveAttribute('href', '/upload');
    expect(screen.getByText('What unlocks after upload')).toBeInTheDocument();
    expect(screen.getByText('No dataset loaded')).toBeInTheDocument();
    // No KPI tiles, percentages or metrics are rendered before upload.
    const main = screen.getByRole('main');
    expect(within(main).queryByText(/%/)).toBeNull();
    expect(within(main).queryByText(/accuracy|macro-f1|recall/i)).toBeNull();
  });

  it('gates analytical pages until data exists', async () => {
    installFetch({ 'GET /api/dataset/summary': { stage: 'empty' } });
    renderAt('/performance');
    expect(await screen.findByText('No dataset uploaded')).toBeInTheDocument();
  });
});

describe('upload flow and target confirmation', () => {
  it('uploads a file, shows its profile and requires an explicit target choice', async () => {
    const user = userEvent.setup();
    const calls = installFetch({
      'GET /api/dataset/summary': { stage: 'empty' },
      'POST /api/upload': { body: FIRST, status: 201 },
      'GET /api/dataset/preview': { columns: ['student_id', 'grade', 'outcome'], rows: [['S1', '12', 'Dropout']], row_ids: [0], total_rows: 120 },
      'POST /api/dataset/target': (init) => {
        const body = JSON.parse(init.body);
        return {
          confirmed: false,
          target_info: { target: body.target, classes: ['Dropout', 'Graduate'], class_counts: { Dropout: 40, Graduate: 80 },
            missing_target_rows: 0, suggested_at_risk_class: 'Dropout', warnings: [] },
          feature_config: { features: ['grade'], feature_types: { grade: 'numeric' }, exclusions: [{ column: 'outcome', reason: 'target' }, { column: 'student_id', reason: 'student_identifier' }],
            warnings: [], timing_preset: 'all', timing_label: 'Uses all selected columns (no later-term columns detected by name)', early_prediction: false, later_term_columns: [] },
        };
      },
    });
    renderAt('/upload');
    const input = await screen.findByTestId('file-input');
    await user.upload(input, new File(['student_id,grade,outcome\nS1,12,Dropout\n'], 'first_cohort.csv', { type: 'text/csv' }));

    expect(await screen.findByText('first_cohort.csv', { selector: 'span' })).toBeInTheDocument();
    expect(screen.getAllByText('120').length).toBeGreaterThan(0);
    expect(calls.some((c) => c.key === 'POST /api/upload')).toBe(true);

    // The target is never pre-selected even though "outcome" is an exact-name candidate.
    const targetSelect = screen.getByLabelText('Target (outcome) column');
    expect(targetSelect).toHaveValue('');
    const confirm = screen.getByRole('button', { name: /confirm target and features/i });
    expect(confirm).toBeDisabled();
    expect(calls.some((c) => c.key === 'POST /api/dataset/target')).toBe(false);

    await user.selectOptions(targetSelect, 'outcome');
    expect(await screen.findByText(/Class distribution in/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByRole('button', { name: /confirm target and features/i })).toBeEnabled());
    const dryRuns = calls.filter((c) => c.key === 'POST /api/dataset/target').map((c) => JSON.parse(c.init.body));
    expect(dryRuns.every((b) => b.dry_run === true)).toBe(true);
  });

  it('blocks training until the target is confirmed', async () => {
    installFetch({ 'GET /api/dataset/summary': FIRST });
    renderAt('/performance');
    expect(await screen.findByText('Target column not confirmed')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: /train models/i })).toBeNull();
  });

  it('rejects non-CSV files on the client', async () => {
    const user = userEvent.setup({ applyAccept: false });
    const calls = installFetch({ 'GET /api/dataset/summary': { stage: 'empty' } });
    renderAt('/upload');
    await user.upload(await screen.findByTestId('file-input'), new File(['x'], 'grades.xlsx'));
    expect(await screen.findByRole('alert')).toHaveTextContent('Only .csv files are accepted.');
    expect(calls.some((c) => c.key === 'POST /api/upload')).toBe(false);
  });
});

describe('dataset replacement', () => {
  it('clears the previous dataset from the UI when a new file is uploaded', async () => {
    const user = userEvent.setup();
    let current = FIRST;
    installFetch({
      'GET /api/dataset/summary': () => current,
      'POST /api/upload': () => {
        current = SECOND;
        return { body: SECOND, status: 201 };
      },
      'GET /api/dataset/preview': () => (current === FIRST
        ? { columns: ['student_id', 'grade', 'outcome'], rows: [['S1', '12', 'Dropout']], row_ids: [0], total_rows: 120 }
        : { columns: ['score', 'label'], rows: [['3', 'p']], row_ids: [0], total_rows: 48 }),
      'POST /api/dataset/target': { body: { error: { code: 'x', message: 'unused', details: null } }, status: 422 },
    });
    renderAt('/upload');
    expect(await screen.findByText('first_cohort.csv', { selector: 'span' })).toBeInTheDocument();
    expect(await screen.findByText('S1')).toBeInTheDocument();

    await user.upload(screen.getByTestId('file-input'), new File(['score,label\n3,p\n'], 'second_file.csv', { type: 'text/csv' }));

    expect(await screen.findByText('second_file.csv', { selector: 'span' })).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByText('S1')).toBeNull());
    expect(screen.queryByText('first_cohort.csv')).toBeNull();
    expect(screen.queryByText('student_id')).toBeNull();
    expect(screen.getAllByText('48').length).toBeGreaterThan(0);
    expect(screen.getByLabelText('Target (outcome) column')).toHaveValue('');
  });
});
