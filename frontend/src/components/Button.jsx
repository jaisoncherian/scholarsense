import { Loader2 } from 'lucide-react';

const VARIANTS = {
  primary: 'bg-forest text-white hover:bg-forest-dark disabled:bg-forest/40',
  secondary: 'bg-card text-ink border border-line-strong hover:bg-canvas disabled:text-subtle',
  soft: 'bg-mint-soft text-forest hover:bg-mint-tint disabled:text-subtle',
  ghost: 'bg-transparent text-muted hover:bg-canvas hover:text-ink disabled:text-subtle',
  danger: 'bg-card text-risk-high-text border border-risk-high/40 hover:bg-risk-high-soft',
};
const SIZES = { sm: 'h-8 px-3 text-xs', md: 'h-10 px-4 text-sm', lg: 'h-11 px-5 text-sm' };

export const buttonClass = (variant = 'primary', size = 'md', extra = '') =>
  `inline-flex items-center justify-center gap-2 rounded-lg font-semibold transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-mint focus-visible:ring-offset-2 disabled:cursor-not-allowed ${VARIANTS[variant]} ${SIZES[size]} ${extra}`;

export default function Button({ variant = 'primary', size = 'md', icon: Icon, loading = false, disabled, className = '', children, type = 'button', ...rest }) {
  return (
    <button type={type} className={buttonClass(variant, size, className)} disabled={disabled || loading} aria-busy={loading || undefined} {...rest}>
      {loading ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : Icon ? <Icon className="h-4 w-4" aria-hidden="true" /> : null}
      {children}
    </button>
  );
}
