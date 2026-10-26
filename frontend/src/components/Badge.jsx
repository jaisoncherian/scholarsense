const TONES = {
  neutral: 'bg-canvas text-muted border border-line',
  mint: 'bg-mint-soft text-forest',
  olive: 'bg-olive-soft text-olive-dark',
  High: 'bg-risk-high-soft text-risk-high-text',
  Medium: 'bg-risk-medium-soft text-risk-medium-text',
  Low: 'bg-risk-low-soft text-risk-low-text',
  warning: 'bg-risk-medium-soft text-risk-medium-text',
  danger: 'bg-risk-high-soft text-risk-high-text',
};

export default function Badge({ tone = 'neutral', children, className = '', title }) {
  return (
    <span title={title} className={`inline-flex items-center gap-1 whitespace-nowrap rounded-full px-2.5 py-0.5 text-xs font-semibold ${TONES[tone] || TONES.neutral} ${className}`}>
      {children}
    </span>
  );
}

export function RiskBadge({ category }) {
  if (!category) return <Badge>Not available</Badge>;
  return <Badge tone={category}>{category} risk</Badge>;
}

const SPLIT_LABELS = { test: 'Held-out test', train: 'Training (in-sample)', unlabeled: 'No target value' };

export function SplitBadge({ split }) {
  return (
    <Badge tone={split === 'test' ? 'mint' : split === 'train' ? 'olive' : 'neutral'}>
      {SPLIT_LABELS[split] || split}
    </Badge>
  );
}
