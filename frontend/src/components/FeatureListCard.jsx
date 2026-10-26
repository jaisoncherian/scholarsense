import { useState } from 'react';
import Card from './Card';
import Badge from './Badge';
import Notice from './Notice';

// Shows exactly which features and which prediction-timing setting the models were trained with.
export default function FeatureListCard({ features, timingLabel, earlyPrediction, title = 'Features used for training' }) {
  const [open, setOpen] = useState(false);
  const shown = open ? features : features.slice(0, 12);
  return (
    <Card title={title} subtitle={`${features.length} feature column(s). Target and identifier columns are never included.`}>
      <Notice tone={earlyPrediction ? 'mint' : 'warning'} title={earlyPrediction ? 'Early-prediction setting' : 'Not an early-prediction setting'}>
        {timingLabel}
      </Notice>
      <ul className="mt-3 flex flex-wrap gap-1.5" aria-label="Feature columns">
        {shown.map((f) => <li key={f}><Badge>{f}</Badge></li>)}
      </ul>
      {features.length > 12 && (
        <button type="button" onClick={() => setOpen((v) => !v)} className="mt-2 text-xs font-semibold text-forest hover:underline">
          {open ? 'Show fewer' : `Show all ${features.length}`}
        </button>
      )}
    </Card>
  );
}
