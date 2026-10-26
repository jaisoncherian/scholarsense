import { Link } from 'react-router-dom';
import { BarChart3 } from 'lucide-react';
import TopBar from '../components/TopBar';
import Card from '../components/Card';
import Dropzone from '../components/Dropzone';
import ErrorBanner from '../components/ErrorBanner';
import Loader from '../components/Loader';
import Button, { buttonClass } from '../components/Button';
import TargetSetup from '../components/TargetSetup';
import { ColumnTable, DatasetKpis, IssueList, PreviewTable } from '../components/DatasetProfile';
import { atLeast, useAppStore } from '../hooks/AppStore';
import { useAction, useApiData } from '../hooks/useApi';
import { api } from '../services/api';

export default function DatasetUpload() {
  const store = useAppStore();
  const { summary, stage, datasetVersion } = store;
  const upload = useAction(store.uploadDataset);
  const analyze = useAction(store.runAnalysis);
  const hasData = stage !== 'empty';
  const preview = useApiData(() => api.preview(20), [datasetVersion, summary?.dataset?.uploaded_at], hasData);

  return (
    <>
      <TopBar eyebrow="Step 1 · Upload and validate" title="Dataset Upload"
        description="Upload a CSV of student records. The file is validated, profiled and kept only in this session's temporary storage." />
      <div className="space-y-6">
        <Card title={hasData ? 'Replace dataset' : 'Upload a dataset'}>
          <Dropzone onFile={upload.run} busy={upload.pending} hasDataset={hasData} />
          {upload.error && <div className="mt-3"><ErrorBanner title="Upload failed" error={upload.error} onDismiss={upload.clearError} /></div>}
        </Card>

        {hasData && (
          <>
            <div>
              <p className="mb-3 text-sm text-muted">
                Loaded <span className="font-semibold text-ink">{summary.dataset.filename}</span>
              </p>
              <DatasetKpis summary={summary} />
            </div>
            <div className="grid gap-6 xl:grid-cols-2">
              <Card title="Validation report" subtitle="Structural checks run on the uploaded file.">
                <IssueList issues={summary.profile.issues} />
              </Card>
              <Card title="Columns and detected types" subtitle="Types are inferred from the values; identifiers and constants are flagged.">
                <ColumnTable columns={summary.profile.columns} />
              </Card>
            </div>
            {preview.loading && <Loader label="Loading preview…" rows={1} />}
            {preview.error && <ErrorBanner error={preview.error} onRetry={preview.reload} />}
            {preview.data && <PreviewTable preview={preview.data} />}

            <TargetSetup key={datasetVersion} />

            {atLeast(stage, 'configured') && (
              <Card title="Next: explore the data">
                <div className="flex flex-wrap items-center gap-3">
                  <Button icon={BarChart3} onClick={analyze.run} loading={analyze.pending}>
                    {summary.analysis_available ? 'Re-run analysis' : 'Run analysis'}
                  </Button>
                  {summary.analysis_available && <Link className={buttonClass('secondary')} to="/analytics">Open Student Analytics</Link>}
                  <Link className={buttonClass('ghost')} to="/performance">Go to model training</Link>
                </div>
                {analyze.error && <div className="mt-3"><ErrorBanner error={analyze.error} onDismiss={analyze.clearError} /></div>}
              </Card>
            )}
          </>
        )}
      </div>
    </>
  );
}
