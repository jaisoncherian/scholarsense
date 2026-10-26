import { lazy, Suspense } from 'react';
import { Skeleton } from '../components/Loader';

// Plotly is large; it is only downloaded when the first chart renders.
const PlotlyChart = lazy(() => import('./PlotlyChart'));

export default function LazyPlot(props) {
  return (
    <Suspense fallback={<Skeleton className="w-full" style={{ height: props.height || 320 }} />}>
      <PlotlyChart {...props} />
    </Suspense>
  );
}
