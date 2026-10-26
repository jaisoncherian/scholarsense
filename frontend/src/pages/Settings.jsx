import { useState } from 'react';
import { Trash2 } from 'lucide-react';
import TopBar from '../components/TopBar';
import Card from '../components/Card';
import Button from '../components/Button';
import ErrorBanner from '../components/ErrorBanner';
import Notice from '../components/Notice';
import { useAppStore } from '../hooks/AppStore';
import { useAction } from '../hooks/useApi';

export default function Settings() {
  const { stage, summary, clearSession } = useAppStore();
  const [done, setDone] = useState(false);
  const clear = useAction(async () => {
    await clearSession();
    setDone(true);
  });
  return (
    <>
      <TopBar eyebrow="Session" title="Settings" description="ScholarSense has no accounts. Data lives only in this browser session on the local server." />
      <div className="grid gap-6 xl:grid-cols-2">
        <Card title="Session and data" subtitle="Uploaded files are stored under a random name in a temporary folder and deleted when replaced, when the session is cleared, after 60 idle minutes (default) or when the server stops.">
          <p className="text-sm text-ink">Current stage: <span className="font-semibold">{stage}</span></p>
          {summary?.dataset && <p className="mt-1 text-sm text-muted">Dataset: {summary.dataset.filename}</p>}
          <Button className="mt-4" variant="danger" icon={Trash2} loading={clear.pending} onClick={clear.run} disabled={stage === 'empty'}>
            Clear session and delete data
          </Button>
          {done && stage === 'empty' && <Notice tone="mint" className="mt-3">Session cleared. The temporary file and all results were deleted.</Notice>}
          {clear.error && <div className="mt-3"><ErrorBanner error={clear.error} /></div>}
        </Card>
        <Card title="Responsible use">
          <ul className="list-disc space-y-1 pl-5 text-sm text-muted">
            <li>Risk scores are model estimates, not calibrated probabilities or decisions.</li>
            <li>Support suggestions are for staff review only and never trigger automatic actions.</li>
            <li>Explanations describe model behaviour, not causes.</li>
            <li>Upload only data you are authorised to process; no data leaves this machine.</li>
          </ul>
        </Card>
      </div>
    </>
  );
}
