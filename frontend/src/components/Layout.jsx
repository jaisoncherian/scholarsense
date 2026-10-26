import { Outlet } from 'react-router-dom';
import Sidebar from './Sidebar';
import ErrorBanner from './ErrorBanner';
import Loader from './Loader';
import { useAppStore } from '../hooks/AppStore';

export default function Layout() {
  const { status, error, refresh } = useAppStore();
  return (
    <div className="flex min-h-screen bg-canvas">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded-lg focus:bg-card focus:px-3 focus:py-2">
        Skip to content
      </a>
      <Sidebar />
      <main id="main" className="min-w-0 flex-1 px-4 py-6 md:px-8 lg:py-8">
        <div className="mx-auto max-w-[1600px]">
          {status === 'error' && (
            <div className="mb-4">
              <ErrorBanner title="Could not load session state" error={error} onRetry={refresh} />
            </div>
          )}
          {status === 'loading' && !error ? <Loader label="Loading session…" /> : <Outlet />}
        </div>
      </main>
    </div>
  );
}
