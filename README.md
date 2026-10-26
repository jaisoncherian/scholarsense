# ScholarSense

**Turning Student Data into Student Success.**

ScholarSense is a local web app for predicting student dropout and planning early support. You upload a CSV and the app walks through the workflow:

Upload CSV → Validate → Select target → Explore → Train models → Compare → Predict → Explain → Recommend support → Export

The app ships with **no data**. Every statistic, chart, metric, prediction, explanation and suggestion is computed at runtime from the file you upload. When something can't be computed, the UI says "Not available" and gives the reason.

| Layer | Stack |
|---|---|
| Frontend | React 18, Vite 5, Tailwind CSS 3, react-plotly.js (Plotly loaded lazily), lucide-react, React Router 6 |
| Backend | Python 3.11, Flask 3, Flask-CORS, pandas, numpy, scikit-learn, joblib |
| Tests | pytest (backend), Vitest and React Testing Library (frontend) |

There is no database, no authentication, no cloud service and no generative-AI API.

---

## Setup

Prerequisites: Python 3.11 and Node.js 18 or newer.

```bash
# Backend
cd backend
py -3.11 -m venv .venv                 # macOS/Linux: python3.11 -m venv .venv
.venv/Scripts/python -m pip install -r requirements.txt   # macOS/Linux: .venv/bin/python -m pip ...

# Frontend
cd ../frontend
npm install
```

All dependency versions are pinned in `backend/requirements.txt` and `frontend/package.json`.

## Running

Open two terminals:

```bash
# 1. API on http://127.0.0.1:5000
cd backend && .venv/Scripts/python app.py

# 2. UI on http://localhost:5173 (Vite proxies /api to the backend)
cd frontend && npm run dev
```

Then open http://localhost:5173. To try the app, upload `sample_data/synthetic_students.csv`. That file is randomly generated synthetic data and is never loaded automatically. You can regenerate it with `python sample_data/generate_synthetic.py [rows] [seed]`.

A `Makefile` wraps these steps (`make install`, `make backend`, `make frontend`, `make test`). Its default interpreter path is the Windows venv layout; override it with `make PY=backend/.venv/bin/python test`.

## Environment variables

| Variable | Default | Purpose |
|---|---|---|
| `SCHOLARSENSE_MAX_UPLOAD_MB` | `20` | Maximum upload size |
| `SCHOLARSENSE_MAX_ROWS` | `200000` | Maximum data rows |
| `SCHOLARSENSE_MAX_COLUMNS` | `500` | Maximum columns |
| `SCHOLARSENSE_UPLOAD_DIR` | `<system temp>/scholarsense_uploads` | Temporary upload folder (outside any served path) |
| `SCHOLARSENSE_SESSION_TTL_MINUTES` | `60` | Idle time before a session and its file are deleted |
| `SCHOLARSENSE_RISK_LOW` / `SCHOLARSENSE_RISK_HIGH` | `0.33` / `0.66` | Default risk-category thresholds |
| `SCHOLARSENSE_RF_N_JOBS` | `4` | CPU cores used by Random Forest |
| `SCHOLARSENSE_CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed CORS origins (fallback; the Vite proxy is the main path) |
| `SCHOLARSENSE_COOKIE_SECURE` | `0` | Set to `1` behind HTTPS |
| `SCHOLARSENSE_PORT` | `5000` | API port |
| `SCHOLARSENSE_API_URL` (frontend) | `http://127.0.0.1:5000` | Proxy target used by the Vite dev server |

## Tests

```bash
cd backend && .venv/Scripts/python -m pytest      # 85 tests
cd frontend && npm test                           # 6 tests
# or: make test
```

The backend tests use only synthetic data generated inside the tests. They cover:

- **Upload:** valid, non-CSV, binary, oversized, empty, header-only, malformed, BOM, semicolon (with decimal comma), tab, and row/column limits.
- **Profiling:** missing values and duplicate rows; duplicate and blank column names; constant, high-cardinality and ID-like columns.
- **Target validation:** missing column, constant, single-class, ID-like, rare-class, mostly-missing and numeric targets.
- **Leakage controls:** target and ID columns kept out of features; later-term flags and the timing preset; the demographic-feature warning.
- **Preprocessing:** missing values and unseen categories.
- **Training:**
  - binary and multiclass metrics;
  - one identical split shared by both models;
  - imputer statistics fitted on training rows only;
  - stratification;
  - too-few-rows and rare-class errors, and rows with a missing target being dropped;
  - one model failing while the other still returns.
- **Model selection:** every tie-break branch.
- **Predictions:** output shape, probabilities summing to 1, risk thresholds (including server-side re-application), filters, search and pagination.
- **Export:** CSV content and CSV-injection neutralisation.
- **Explainability:** permutation importance runs only on held-out rows and original columns; Logistic Regression contributions sum to the centred logit; Random Forest perturbation; missing values are never explained.
- **Interventions:** rules shown or hidden depending on which columns exist; demographic columns never used; review status; staff mapping.
- **Sessions:**
  - replacing a dataset resets all state and deletes the old temp file;
  - re-configuring clears downstream results;
  - `DELETE /api/session`, TTL expiry and shutdown cleanup;
  - unknown session ids are never adopted;
  - sessions are isolated from each other;
  - stage progression.

The frontend tests cover the empty state, prerequisite gating, the upload flow, confirmation gating (the target is never pre-selected), client-side rejection of non-CSV files, and the UI resetting when a dataset is replaced.

---

## API reference

All endpoints are under `/api` and return JSON. Errors always use this envelope:

```json
{"error": {"code": "rare_class", "message": "Every class needs at least 2 rows ...", "details": {...}}}
```

Status codes: 400 (bad parameter), 404 (no dataset / row not found), 409 (prerequisite step missing), 413 (too large), 415 (not a CSV), 422 (valid request, unusable data), 500 (unexpected error).

| Method & path | Purpose |
|---|---|
| `GET /api/health` | Liveness check |
| `POST /api/upload` | Multipart `file` field. Validates, parses and profiles the file, and **replaces** any previous dataset in the session. |
| `GET /api/dataset/summary` | Current `stage` (`empty`, `uploaded`, `configured`, `analyzed`, `trained`, `predicted`), dataset info, column profile, issues, target candidates, confirmed config, thresholds |
| `GET /api/dataset/preview?rows=20` | First N rows (max 100) |
| `POST /api/dataset/target` | `{target, at_risk_class, id_column?, excluded_columns?, include_id_like?, timing_preset: "all" \| "exclude_later", dry_run?}`. With `dry_run: true` it only validates and previews the feature config. Without `dry_run`, it confirms the config and clears downstream results. |
| `POST /api/analysis` / `GET /api/analysis` | Run or fetch the exploratory analysis |
| `POST /api/models/train` | `{test_size?, lr_class_weight?: "balanced" \| "none", rf_class_weight?, rf_n_estimators?}` |
| `GET /api/models/metrics` | Metrics, selection rationale, features and timing label |
| `POST /api/predictions` | `{model?: "selected" \| "logistic_regression" \| "random_forest", scope?: "test" \| "all"}` |
| `GET /api/predictions` | Query params: `split` (`test` default, `train`, `unlabeled`, `all`), `predicted_class`, `risk` (`Low`/`Medium`/`High`), `q` (identifier search), `sort` (`risk_desc`, `risk_asc`, `row`), `page`, `page_size` (≤200), optional `low`/`high` to re-apply thresholds |
| `PUT /api/predictions/thresholds` | `{low, high}`; requires `0 < low < high < 1` |
| `GET /api/explanations/global?model=&scoring=f1_macro\|at_risk_recall` | Permutation importance on the held-out test set |
| `GET /api/explanations/local/<row_id>?model=` | Explanation for one row (`row_id` = 0-based data row) |
| `GET /api/interventions` | Rule availability, indicator columns, per-student suggestions. Filters: `risk`, `status`, `rule`, `split`, `q`, `page`, `page_size` |
| `GET /api/interventions/<row_id>` | One student's evidence and suggestions, even if no rule fired |
| `PATCH /api/interventions/<row_id>/review` | `{status: "Not reviewed" \| "In review" \| "Actioned" \| "Dismissed", note?}` |
| `GET` / `PUT /api/interventions/mapping` | Read the indicator mapping, or set it with `{indicators: [{column, category, direction, threshold?}]}` or `{reset: true}` |
| `GET /api/export?type=predictions\|interventions` | CSV download |
| `DELETE /api/session` | Delete the session, its temp file and all results |

## Session and temp-file lifecycle

- **Session id.** The server generates a random 128-bit id and sends it in the httpOnly `ss_session` cookie (SameSite=Lax). Non-browser clients can send the same value in an `X-Session-Id` header. Ids the server didn't issue are never adopted; the client gets a fresh session instead.
- **In-memory store.** Each session holds its DataFrame, profile, config, analysis, fitted pipelines, metrics, predictions, cached explanations, indicator mapping and review statuses. A store-level lock guards the session map, and a per-session lock guards mutation. Models live only in memory and are never written to disk.
- **Temp files.** Uploaded bytes are written to `SCHOLARSENSE_UPLOAD_DIR` under a random `<uuid>.upload` name; the client filename is never used on disk. The file is deleted when:
  1. the dataset is replaced (a failed upload leaves the previous dataset untouched);
  2. `DELETE /api/session` is called (also available as **Settings → Clear session**);
  3. the session sits idle past the TTL (checked at most once a minute, on incoming requests);
  4. the process shuts down (`atexit`).
- **Logging.** Only metadata is logged: session-id prefix, data shape and timings. Row contents are never logged.

## Leakage and prediction-timing guidance

- The target is never selected automatically. Columns named `target`, `outcome`, `dropout`, `status`, `label` or `class` are offered as suggestions only, and the user must confirm.
- The target column and the student-identifier column are always excluded from features. Likely ID columns (almost every value unique) are excluded by default; you can include one, but the app shows a warning.
- Constant and date columns are never used as features.
- Columns whose names contain `2nd`, `second`, `semester 2`, `sem2` or `final` are flagged as **possible later-term information**. The *Prediction timing* control can exclude them. The app only labels a run as an "early-prediction setting" when flagged columns existed and were all excluded. The Model Performance and Risk Predictions pages always show the exact feature list and timing label used.
- If demographic attributes (gender, age, nationality and similar) are used as features, a warning is shown. They are never used to trigger support suggestions.
- All preprocessing (imputation, scaling, one-hot encoding) is fitted inside each sklearn `Pipeline` on the training split only.

## Models, evaluation and selection

- **Models.** `LogisticRegression` (max_iter 2000) and `RandomForestClassifier` (seed 42; 200 trees by default, 100 above 50k rows, capped at 300). Class weight is configurable for each model and defaults to `balanced`.
- **Preprocessing.** Numeric columns get median imputation, plus `StandardScaler` for Logistic Regression only. Categorical columns get constant "missing" imputation and `OneHotEncoder(handle_unknown="ignore", max_categories=50)`.
- **Rows used.** Rows with a missing target are dropped and the count is reported.
- **Split.** One stratified `train_test_split` (default 80/20, `random_state=42`) is shared by both models. If stratifying isn't possible, the app falls back to a random split and shows a warning.
- **Errors.** Clear 422 errors are returned for fewer than 30 labelled rows, any class with fewer than 2 rows, fewer than 2 classes, or no features.
- **Metrics.** All metrics come from the untouched test split: accuracy, macro precision/recall/F1, weighted F1, per-class metrics, classification report and confusion matrix. Recall, precision, false alarms and misses for the at-risk class are highlighted. *Macro* is the unweighted mean across classes, so it weights each class equally and exposes weak performance on small classes.
- **Selection.** The criteria are shown in the UI:
  1. highest recall for the at-risk class;
  2. if recalls are within 0.01, highest macro-F1 (a difference within 0.01 also counts as a tie);
  3. then highest accuracy;
  4. a complete tie goes to Logistic Regression.

## Risk definition

**Risk score = the model's predicted probability for the at-risk class you selected.** This is a *model-estimated risk, not a calibrated real-world probability*.

Categories:

- **Low:** score < low
- **Medium:** low ≤ score < high
- **High:** score ≥ high

The default thresholds are 0.33 and 0.66. You can change them on the Risk Predictions page; the server re-applies them to predictions, interventions and exports.

A predicted non-at-risk class (for example "Enrolled") is shown only as the predicted class. It is never treated as a confirmed non-dropout.

Each scored row carries a `split` label:

- `test`: held out, so its prediction is unbiased. The table shows these rows by default.
- `train`: in-sample, so its prediction is optimistic; a warning is shown.
- `unlabeled`: the row has no target value.

## Explainability and its limits

- **Global.** `permutation_importance` runs on the held-out test set (stratified sample of at most 5,000 rows). It shuffles each **original** column through the full pipeline, with 5 repeats and seed 42, and the scoring is macro-F1 or recall for the at-risk class. The chart shows mean ± standard deviation. It describes model behaviour, not causation, and is never presented as the reason for an individual prediction.
- **Local, Logistic Regression.** Each feature's contribution is `coefficient × (encoded value − training mean of that encoded column)`, summed back to the original column. The unit is log-odds of the predicted class. This is exact for the linear model but still describes the model, not causes. Centring on the training mean makes contributions read as "relative to an average training student".
- **Local, Random Forest.** A perturbation approximation: each original feature is replaced, one at a time, with its training median (numeric) or mode (categorical), and the change in the predicted-class probability is reported. It ignores interactions and depends on the reference value.
- **Missing values.** Features whose value is missing are labelled "not explained" and left out of the plain-language summary.

## Interventions

Suggestions are rule-based. No AI API is involved.

- **Indicator columns.** These are detected by name keywords plus numeric or boolean type:
  - performance: grade, GPA, score, marks, exam, approved, passed, credits earned;
  - attendance: attend*, absen*, presence;
  - financial: debt, owed, arrears, overdue, balance, fee up-to-date or paid flags.
- **Exclusions.** Demographic columns, the target, the identifier, constant and date columns, and columns excluded as not available at prediction time are never used.
- **Staff mapping.** An optional mapping panel lets staff choose their own columns, areas, directions and thresholds.
- **When a rule fires.** Only on observed evidence: below the dataset's lower quartile (or above the upper quartile for absences and debt amounts), a yes/no flag, or a staff-set threshold.
- **Rules.**
  - academic support (performance);
  - supportive attendance conversation (attendance);
  - financial-aid referral (financial);
  - advisor/counselor review, when indicators appear in two or more different areas.

  A rule is not shown when no matching column exists, and the UI explains why.
- **What each suggestion shows.** The evidence (column, value, comparison basis), the model output labelled separately as an estimate, and a review status (*Not reviewed / In review / Actioned / Dismissed*) held in session memory. Every view states: *suggestions for staff review, not automated decisions.*

## Security and privacy

- **Upload checks.** The server enforces the `.csv` extension, rejects binary content (signature or NUL bytes), and caps the size twice: `MAX_CONTENT_LENGTH` plus an explicit byte check. Row and column limits also apply.
- **Parsing.** Content is parsed only as data by pandas and is never executed or `eval`'d. Encoding handles a UTF-8 BOM, with a Latin-1 fallback that triggers a warning. Delimiters `,` `;` and tab are detected with `csv.Sniffer`, with a safe fallback.
- **Exports.** Cells starting with `=`, `+`, `-`, `@`, tab or carriage return are prefixed with `'` to neutralise CSV injection.
- **Response headers.** `nosniff`, `X-Frame-Options: DENY`, `Referrer-Policy: no-referrer`, `Cache-Control: no-store`, and a restrictive CSP on API responses.
- **CORS.** Limited to the dev origin.
- **Frontend.** React escaping only; `dangerouslySetInnerHTML` is never used. Filenames are sanitised for display.
- **No third-party requests.** Fonts fall back to system fonts and Plotly is bundled locally, so no data or IP address leaves the machine.

---

## Design decisions

1. **Repository layout.** The repository root is the `scholarsense/` project root. The original design files moved to `docs/`, with the screenshot at `docs/design-reference.png`. The design reference informed layout and style only; no numbers, names or records were copied from it.
2. **Theme colours.** The palette from the spec is defined as Tailwind tokens: `canvas #F8F8F8`, `ink #1C1C1C`, `muted #606060`, `mint #B9E8B9`, `olive #A1A75D`, `card #FFFFFF`. A deep `forest #2E5A44` (from `docs/DESIGN.md`) is used for primary buttons and active states so white text stays readable. Mint is used for highlights.
3. **Chart colours.** A categorical palette was derived from the brand hues and checked with a colour-vision-deficiency validator (all checks pass). Colour follows the class, never its rank. The academic chart uses small multiples so columns with different scales never share an axis.
4. **Target validation.** A target with more than 20 distinct values is rejected as "not a classification target". Mostly-missing means more than 50% missing.
5. **Analysis prerequisite.** Analysis requires a confirmed target, because target-aware charts need it. Training also requires a confirmed target but does not require running the analysis first.
6. **Blank and duplicate column names** are renamed (`unnamed_<n>`, `name (2)`) and reported, rather than rejected. Completely empty rows are dropped and reported.
7. **Datetime columns** are not used as features (there is no date feature engineering).
8. **High-cardinality text columns** stay as features, but one-hot encoding is capped at the 50 most frequent categories.
9. **Default scoring scope.** `POST /api/predictions` scores held-out test rows by default. "All rows" is opt-in and comes with an in-sample warning.
10. **Upload failures.** A failed upload never destroys the current dataset; replacement happens only after the new file parses successfully.
11. **Configuration changes.** Confirming a changed target or feature config clears the analysis, models, predictions, explanations, reviews and indicator mapping.
12. **Advisor/counselor review** fires on indicators from two or more *different areas*, not on two columns from the same area, so several low grades don't escalate on their own.
13. **Session state.** The frontend store is a React Context. It is rebuilt from `GET /api/dataset/summary` on load, so a page refresh restores the correct view, and it is cleared on every upload.

## Project structure

```
backend/
  app.py                 # app factory, blueprints, security headers, error handlers
  config.py              # limits, seeds, TTL, thresholds (env-overridable)
  errors.py              # ApiError + uniform error envelope
  routes/                # upload, analysis, training, predictions, explanations, interventions, export
  services/              # session_store, dataset_service, data_validation, eda, preprocessing,
                         # train_models, evaluation, predictions, explainability, recommendations
  tests/                 # pytest suite (synthetic fixtures only)
frontend/
  src/components/        # Sidebar, TopBar, Card, KpiCard, EmptyState, DataTable, Loader, ErrorBanner, PlotCard, …
  src/pages/             # Overview, DatasetUpload, StudentAnalytics, RiskPredictions, ModelPerformance,
                         # Explainability, Interventions, Settings
  src/charts/            # lazy Plotly wrapper, theme tokens, chart builders
  src/services/api.js    # fetch wrapper with consistent error parsing
  src/hooks/             # AppStore (context), useApi helpers
sample_data/             # synthetic generator + synthetic_students.csv (not loaded by default)
docs/                    # design reference
```
