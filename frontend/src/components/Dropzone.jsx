import { useRef, useState } from 'react';
import { AlertTriangle, UploadCloud } from 'lucide-react';
import Button from './Button';

// Drag-and-drop + keyboard-accessible file picker. Only the extension is checked here;
// the server validates type, size and content.
export default function Dropzone({ onFile, busy = false, hasDataset = false, error }) {
  const inputRef = useRef(null);
  const [dragging, setDragging] = useState(false);
  const [localError, setLocalError] = useState(null);

  const pick = (files) => {
    const file = files && files[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setLocalError('Only .csv files are accepted.');
      return;
    }
    setLocalError(null);
    onFile(file);
  };
  const browse = () => inputRef.current && inputRef.current.click();

  return (
    <div>
      <div
        role="button"
        tabIndex={0}
        aria-label="Upload a CSV file. Drop a file here or press Enter to browse."
        aria-disabled={busy}
        onClick={() => !busy && browse()}
        onKeyDown={(e) => {
          if ((e.key === 'Enter' || e.key === ' ') && !busy) {
            e.preventDefault();
            browse();
          }
        }}
        onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => { e.preventDefault(); setDragging(false); if (!busy) pick(e.dataTransfer.files); }}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-card border-2 border-dashed p-8 text-center transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-mint ${
          dragging ? 'border-forest bg-mint-soft' : 'border-line-strong bg-card hover:bg-canvas'}`}
      >
        <span className="mb-3 rounded-full bg-mint-soft p-3 text-forest" aria-hidden="true">
          <UploadCloud className="h-6 w-6" />
        </span>
        <p className="font-display text-base font-semibold text-ink">Drag and drop a CSV file here</p>
        <p className="mt-1 text-sm text-muted">or</p>
        <Button className="mt-2" variant="secondary" loading={busy} onClick={(e) => { e.stopPropagation(); browse(); }}>
          {busy ? 'Uploading…' : 'Browse files'}
        </Button>
        <p className="mt-3 text-xs text-muted">.csv only · comma, semicolon or tab delimited · size, row and column limits are enforced by the server</p>
        <input ref={inputRef} type="file" accept=".csv,text/csv" className="sr-only" tabIndex={-1} aria-label="Choose a CSV file"
          data-testid="file-input" onChange={(e) => { pick(e.target.files); e.target.value = ''; }} />
      </div>
      {hasDataset && (
        <p className="mt-2 flex items-center gap-1.5 text-xs text-risk-medium-text">
          <AlertTriangle className="h-3.5 w-3.5" aria-hidden="true" />
          Uploading a new file replaces the current dataset and clears all analysis, models, predictions and review notes.
        </p>
      )}
      {(localError || error) && (
        <p role="alert" className="mt-2 text-sm font-semibold text-risk-high-text">{localError || error}</p>
      )}
    </div>
  );
}
