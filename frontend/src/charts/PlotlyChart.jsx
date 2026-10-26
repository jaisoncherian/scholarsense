import createPlotlyComponent from 'react-plotly.js/factory';
import Plotly from 'plotly.js-dist-min';
import { BASE_CONFIG } from './theme';

const Plot = createPlotlyComponent(Plotly);

export default function PlotlyChart({ data, layout, height = 320, ariaLabel }) {
  return (
    <div role="img" aria-label={ariaLabel} className="w-full">
      <Plot
        data={data}
        layout={{ ...layout, height }}
        config={BASE_CONFIG}
        useResizeHandler
        style={{ width: '100%', height }}
      />
    </div>
  );
}
