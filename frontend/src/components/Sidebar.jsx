import { NavLink } from 'react-router-dom';
import {
  AlertTriangle, BarChart3, Cpu, Eye, GraduationCap, HandHeart, LayoutGrid, Settings, UploadCloud,
} from 'lucide-react';
import { useAppStore } from '../hooks/AppStore';
import { formatNumber } from './KpiCard';

export const NAV_ITEMS = [
  { to: '/', label: 'Overview', icon: LayoutGrid, end: true },
  { to: '/upload', label: 'Dataset Upload', icon: UploadCloud },
  { to: '/analytics', label: 'Student Analytics', icon: BarChart3 },
  { to: '/predictions', label: 'Risk Predictions', icon: AlertTriangle },
  { to: '/performance', label: 'Model Performance', icon: Cpu },
  { to: '/explainability', label: 'Explainability', icon: Eye },
  { to: '/interventions', label: 'Interventions', icon: HandHeart },
  { to: '/settings', label: 'Settings', icon: Settings },
];

const STAGE_LABELS = {
  empty: 'No dataset',
  uploaded: 'Uploaded · target needed',
  configured: 'Target confirmed',
  analyzed: 'Analysed',
  trained: 'Models trained',
  predicted: 'Predictions ready',
};

export default function Sidebar() {
  const { summary, stage } = useAppStore();
  const ds = summary?.dataset;
  return (
    <aside className="sticky top-0 flex h-screen w-16 flex-none flex-col border-r border-line bg-card lg:w-64" aria-label="Primary">
      <div className="flex items-center gap-3 px-3 py-5 lg:px-5">
        <span className="flex h-10 w-10 flex-none items-center justify-center rounded-xl bg-forest text-white" aria-hidden="true">
          <GraduationCap className="h-5 w-5" />
        </span>
        <div className="hidden min-w-0 lg:block">
          <p className="font-display text-lg font-bold leading-tight text-ink">ScholarSense</p>
          <p className="text-xs text-muted">Student Success Intelligence</p>
        </div>
      </div>
      <nav className="flex-1 space-y-1 px-2 lg:px-3">
        {NAV_ITEMS.map(({ to, label, icon: Icon, end }) => (
          <NavLink key={to} to={to} end={end} title={label}
            className={({ isActive }) =>
              `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-mint ${
                isActive ? 'bg-mint-soft text-forest' : 'text-muted hover:bg-canvas hover:text-ink'}`}>
            <Icon className="h-5 w-5 flex-none" aria-hidden="true" />
            <span className="hidden lg:inline">{label}</span>
          </NavLink>
        ))}
      </nav>
      <div className="hidden p-3 lg:block">
        <div className="rounded-xl border border-line bg-canvas p-3 text-xs">
          <p className="font-semibold uppercase tracking-wide text-subtle">Current dataset</p>
          {ds ? (
            <>
              <p className="mt-1 truncate text-sm font-semibold text-ink" title={ds.filename}>{ds.filename}</p>
              <p className="text-muted">{formatNumber(ds.rows)} rows · {formatNumber(ds.columns)} columns</p>
            </>
          ) : (
            <p className="mt-1 text-muted">No dataset loaded</p>
          )}
          <p className="mt-2 inline-flex rounded-full bg-mint-soft px-2 py-0.5 font-semibold text-forest">{STAGE_LABELS[stage] || stage}</p>
        </div>
      </div>
    </aside>
  );
}
