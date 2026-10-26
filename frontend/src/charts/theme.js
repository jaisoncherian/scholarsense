// Chart tokens. Categorical order validated for CVD separation and contrast
// (dataviz validator, light mode): assign by entity index, never by rank.
export const SERIES = ['#2F8A57', '#3A7FC1', '#C8642B', '#6250D6', '#8C9431', '#D0457A'];
export const OTHER_COLOR = '#9CA3AF';
export const RISK_COLORS = { Low: '#529E72', Medium: '#DCA54C', High: '#D95D5D' };
export const SEQUENTIAL = [
  [0, '#F3FAF3'],
  [0.5, '#8CC79B'],
  [1, '#1F4D36'],
];
export const DIVERGING = [
  [0, '#3A7FC1'],
  [0.5, '#F2F2F2'],
  [1, '#C8642B'],
];
export const INK = '#1C1C1C';
export const MUTED = '#606060';
export const GRID = '#EEEEEE';

export function classColor(classes, cls) {
  const i = classes.indexOf(cls);
  return i >= 0 && i < SERIES.length ? SERIES[i] : OTHER_COLOR;
}

export function baseLayout(overrides = {}) {
  return {
    autosize: true,
    paper_bgcolor: 'rgba(0,0,0,0)',
    plot_bgcolor: 'rgba(0,0,0,0)',
    font: { family: 'Inter, ui-sans-serif, system-ui, Segoe UI, sans-serif', size: 12, color: MUTED },
    margin: { l: 56, r: 16, t: 12, b: 48 },
    hoverlabel: { bgcolor: '#FFFFFF', bordercolor: '#E5E7EB', font: { color: INK, size: 12 } },
    xaxis: { gridcolor: GRID, zerolinecolor: GRID, linecolor: '#E5E7EB', automargin: true, tickfont: { color: MUTED } },
    yaxis: { gridcolor: GRID, zerolinecolor: GRID, linecolor: '#E5E7EB', automargin: true, tickfont: { color: MUTED } },
    legend: { orientation: 'h', x: 0, y: 1.02, yanchor: 'bottom', font: { color: INK } },
    bargap: 0.25,
    ...overrides,
  };
}

export const BASE_CONFIG = {
  displaylogo: false,
  responsive: true,
  modeBarButtonsToRemove: ['lasso2d', 'select2d', 'autoScale2d', 'toggleSpikelines'],
};
