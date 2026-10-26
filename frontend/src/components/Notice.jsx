import { AlertTriangle, Info } from 'lucide-react';

const TONES = {
  info: { cls: 'border-line bg-canvas text-muted', icon: Info },
  mint: { cls: 'border-mint bg-mint-soft text-forest', icon: Info },
  warning: { cls: 'border-risk-medium/40 bg-risk-medium-soft text-risk-medium-text', icon: AlertTriangle },
};

export default function Notice({ tone = 'info', title, children, className = '' }) {
  const { cls, icon: Icon } = TONES[tone] || TONES.info;
  return (
    <div className={`flex items-start gap-2.5 rounded-xl border p-3 text-sm ${cls} ${className}`}>
      <Icon className="mt-0.5 h-4 w-4 flex-none" aria-hidden="true" />
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        <div className={title ? 'mt-0.5' : ''}>{children}</div>
      </div>
    </div>
  );
}
