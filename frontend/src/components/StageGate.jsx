import { Link } from 'react-router-dom';
import { Lock, UploadCloud } from 'lucide-react';
import EmptyState from './EmptyState';
import { buttonClass } from './Button';
import { atLeast, useAppStore } from '../hooks/AppStore';

const REQUIREMENTS = {
  uploaded: { title: 'No dataset uploaded', description: 'Upload a CSV file to begin. Nothing is shown until data is uploaded.', to: '/upload', cta: 'Upload dataset' },
  configured: { title: 'Target column not confirmed', description: 'Choose and confirm the outcome column and feature configuration first.', to: '/upload', cta: 'Configure target' },
  trained: { title: 'Models not trained yet', description: 'Train the models on the Model Performance page to unlock this view.', to: '/performance', cta: 'Go to training' },
  predicted: { title: 'No predictions yet', description: 'Generate predictions on the Risk Predictions page to unlock this view.', to: '/predictions', cta: 'Go to predictions' },
};

// Renders children only once the session has reached `requires`; otherwise explains why not.
export default function StageGate({ requires, children }) {
  const { stage } = useAppStore();
  if (atLeast(stage, requires)) return children;
  const needed = stage === 'empty' ? 'uploaded' : stage === 'uploaded' ? 'configured' : requires === 'predicted' && !atLeast(stage, 'trained') ? 'trained' : requires;
  const req = REQUIREMENTS[needed];
  return (
    <EmptyState icon={stage === 'empty' ? UploadCloud : Lock} title={req.title} description={req.description}
      action={<Link className={buttonClass('primary')} to={req.to}>{req.cta}</Link>} />
  );
}
