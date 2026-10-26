// Pure functions turning API payloads into Plotly {data, layout}. No values are invented:
// every number comes from the payload passed in.
import { baseLayout, classColor, DIVERGING, INK, RISK_COLORS, SERIES } from './theme';

// Light end-stop keeps dark ink cell labels legible (contrast >= 4.5:1).
const CONFUSION_SCALE = [[0, '#F7FBF7'], [1, '#8CC79B']];
const pct = (v) => (v === null || v === undefined ? 'n/a' : `${v.toFixed(1)}%`);

export function targetDistribution(dist, classes) {
  const rows = dist.classes;
  return {
    data: [
      {
        type: 'bar',
        x: rows.map((r) => r.class),
        y: rows.map((r) => r.count),
        marker: { color: rows.map((r) => classColor(classes, r.class)) },
        text: rows.map((r) => `${r.count} (${pct(r.pct)})`),
        textposition: 'outside',
        cliponaxis: false,
        hovertemplate: '%{x}: %{y} rows<extra></extra>',
      },
    ],
    layout: baseLayout({ yaxis: { ...baseLayout().yaxis, title: { text: 'Rows' } }, showlegend: false }),
  };
}

export function histogram(column, h) {
  if (h.kind === 'discrete') {
    return {
      data: [{ type: 'bar', x: h.x, y: h.counts, marker: { color: SERIES[0] },
        hovertemplate: `${column} = %{x}<br>%{y} rows<extra></extra>` }],
      layout: baseLayout({ xaxis: { ...baseLayout().xaxis, type: 'category', title: { text: column } },
        yaxis: { ...baseLayout().yaxis, title: { text: 'Rows' } }, showlegend: false }),
    };
  }
  const centers = h.counts.map((_, i) => (h.edges[i] + h.edges[i + 1]) / 2);
  const widths = h.counts.map((_, i) => h.edges[i + 1] - h.edges[i]);
  return {
    data: [{
      type: 'bar', x: centers, y: h.counts, width: widths, marker: { color: SERIES[0], line: { color: '#FFFFFF', width: 1 } },
      customdata: h.counts.map((_, i) => [h.edges[i], h.edges[i + 1]]),
      hovertemplate: `${column}: %{customdata[0]:.3g} to %{customdata[1]:.3g}<br>%{y} rows<extra></extra>`,
    }],
    layout: baseLayout({ bargap: 0, xaxis: { ...baseLayout().xaxis, title: { text: column } },
      yaxis: { ...baseLayout().yaxis, title: { text: 'Rows' } }, showlegend: false }),
  };
}

export function horizontalBars(labels, values, { color = SERIES[0], valueLabel = 'Value', textFormat } = {}) {
  const n = labels.length;
  return {
    data: [{
      type: 'bar', orientation: 'h', y: labels.slice().reverse(), x: values.slice().reverse(),
      marker: { color }, text: textFormat ? values.slice().reverse().map(textFormat) : undefined,
      textposition: 'outside', cliponaxis: false,
      hovertemplate: `%{y}: %{x}<extra>${valueLabel}</extra>`,
    }],
    layout: baseLayout({ margin: { l: 160, r: 48, t: 8, b: 40 }, showlegend: false,
      xaxis: { ...baseLayout().xaxis, title: { text: valueLabel } }, height: Math.max(220, 28 * n + 60) }),
  };
}

export function categoricalCounts(entry) {
  return horizontalBars(entry.values.map((v) => v.value), entry.values.map((v) => v.count), {
    valueLabel: 'Rows', textFormat: (v) => String(v),
  });
}

export function missingChart(columns) {
  return horizontalBars(columns.map((c) => c.column), columns.map((c) => c.pct), {
    color: '#A1A75D', valueLabel: '% missing', textFormat: (v) => `${v.toFixed(1)}%`,
  });
}

export function heatmap(columns, matrix) {
  return {
    data: [{
      type: 'heatmap', x: columns, y: columns, z: matrix, zmin: -1, zmax: 1, colorscale: DIVERGING,
      hovertemplate: '%{y} × %{x}<br>r = %{z:.2f}<extra></extra>', xgap: 2, ygap: 2,
      colorbar: { thickness: 10, outlinewidth: 0, tickfont: { color: INK } },
    }],
    layout: baseLayout({ margin: { l: 140, r: 16, t: 8, b: 120 },
      xaxis: { ...baseLayout().xaxis, tickangle: -40, gridcolor: 'rgba(0,0,0,0)' },
      yaxis: { ...baseLayout().yaxis, autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } }),
  };
}

export function boxByClass(chart, classes) {
  const stats = chart.stats.filter((s) => s.n > 0);
  return {
    data: [{
      type: 'box', x: stats.map((s) => s.class), q1: stats.map((s) => s.q1), median: stats.map((s) => s.median),
      q3: stats.map((s) => s.q3), lowerfence: stats.map((s) => s.lowerfence), upperfence: stats.map((s) => s.upperfence),
      mean: stats.map((s) => s.mean), boxpoints: false, marker: { color: SERIES[1] }, line: { width: 1.5 },
      fillcolor: 'rgba(58,127,193,0.18)', hoverinfo: 'y+x',
    }],
    layout: baseLayout({ showlegend: false, yaxis: { ...baseLayout().yaxis, title: { text: chart.column } },
      xaxis: { ...baseLayout().xaxis, type: 'category', categoryorder: 'array', categoryarray: classes } }),
  };
}

export function stackedByClass(chart, classes) {
  return {
    data: chart.series.map((s) => ({
      type: 'bar', name: s.class, x: chart.categories, y: s.proportions.map((p) => (p === null ? 0 : p * 100)),
      customdata: s.counts, marker: { color: classColor(classes, s.class), line: { color: '#FFFFFF', width: 1 } },
      hovertemplate: `${s.class}: %{y:.1f}% (%{customdata} rows)<extra>%{x}</extra>`,
    })),
    layout: baseLayout({ barmode: 'stack', margin: { l: 56, r: 16, t: 36, b: 48 }, yaxis: { ...baseLayout().yaxis, title: { text: '% of category' }, range: [0, 100] },
      xaxis: { ...baseLayout().xaxis, type: 'category', title: { text: chart.column } } }),
  };
}

// Small multiples: each academic column gets its own y-axis, since their scales differ.
export function groupedMeans(academic) {
  const n = academic.columns.length;
  const cols = Math.min(4, n);
  const rows = Math.ceil(n / cols);
  const data = [];
  const axes = {};
  academic.columns.forEach((c, i) => {
    const suffix = i === 0 ? '' : String(i + 1);
    academic.classes.forEach((cls) => data.push({
      type: 'bar', name: cls, legendgroup: cls, showlegend: i === 0, x: [cls], y: [c.means[cls]],
      xaxis: `x${suffix}`, yaxis: `y${suffix}`, marker: { color: classColor(academic.classes, cls) },
      hovertemplate: `${c.column}<br>${cls}: mean %{y:.3g}<extra></extra>`,
    }));
    axes[`xaxis${suffix}`] = { ...baseLayout().xaxis, showticklabels: false, title: { text: c.column, font: { size: 11, color: INK } } };
    axes[`yaxis${suffix}`] = { ...baseLayout().yaxis, rangemode: 'tozero' };
  });
  return {
    data,
    layout: baseLayout({ ...axes, grid: { rows, columns: cols, pattern: 'independent', xgap: 0.25, ygap: 0.45 },
      margin: { l: 48, r: 16, t: 36, b: 40 }, height: 230 * rows + 60 }),
  };
}

export function confusionMatrix(cm) {
  const labels = cm.labels;
  const z = cm.matrix;
  const text = z.map((row) => row.map(String));
  return {
    data: [{
      type: 'heatmap', x: labels, y: labels, z, text, texttemplate: '%{text}', colorscale: CONFUSION_SCALE, showscale: false,
      xgap: 2, ygap: 2, hovertemplate: 'Observed %{y}<br>Predicted %{x}<br>%{z} rows<extra></extra>',
      textfont: { color: INK },
    }],
    layout: baseLayout({ margin: { l: 110, r: 16, t: 8, b: 70 },
      xaxis: { ...baseLayout().xaxis, title: { text: 'Predicted class' }, type: 'category', gridcolor: 'rgba(0,0,0,0)' },
      yaxis: { ...baseLayout().yaxis, title: { text: 'Observed class' }, type: 'category', autorange: 'reversed', gridcolor: 'rgba(0,0,0,0)' } }),
  };
}

export function importanceChart(features, limit = 20) {
  const top = features.slice(0, limit);
  const n = top.length;
  return {
    data: [{
      type: 'bar', orientation: 'h', y: top.map((f) => f.feature).reverse(), x: top.map((f) => f.importance).reverse(),
      error_x: { type: 'data', array: top.map((f) => f.std).reverse(), color: '#606060', thickness: 1.2, width: 3 },
      marker: { color: SERIES[0] }, hovertemplate: '%{y}: %{x:.4f} ± %{error_x.array:.4f}<extra></extra>',
    }],
    layout: baseLayout({ margin: { l: 170, r: 24, t: 8, b: 44 }, showlegend: false, height: Math.max(240, 26 * n + 70),
      xaxis: { ...baseLayout().xaxis, title: { text: 'Mean drop in score when shuffled' } } }),
  };
}

export function contributionChart(contributions, unit, limit = 15) {
  const items = contributions.filter((c) => c.contribution !== null && c.contribution !== 0).slice(0, limit);
  return {
    data: [{
      type: 'bar', orientation: 'h', y: items.map((c) => `${c.feature} = ${c.value}`).reverse(),
      x: items.map((c) => c.contribution).reverse(),
      marker: { color: items.map((c) => (c.contribution > 0 ? SERIES[2] : SERIES[1])).reverse() },
      hovertemplate: `%{y}<br>%{x:.4f} (${unit})<extra></extra>`,
    }],
    layout: baseLayout({ margin: { l: 220, r: 24, t: 8, b: 44 }, showlegend: false, height: Math.max(220, 26 * items.length + 70),
      xaxis: { ...baseLayout().xaxis, title: { text: `Contribution (${unit}); right = toward predicted class` }, zerolinecolor: '#9CA3AF' } }),
  };
}

export function classCounts(counts, classes) {
  const keys = Object.keys(counts);
  return {
    data: [{
      type: 'bar', x: keys, y: keys.map((k) => counts[k]), marker: { color: keys.map((k) => classColor(classes, k)) },
      text: keys.map((k) => String(counts[k])), textposition: 'outside', cliponaxis: false,
      hovertemplate: '%{x}: %{y} rows<extra>Predicted class</extra>',
    }],
    layout: baseLayout({ showlegend: false, yaxis: { ...baseLayout().yaxis, title: { text: 'Rows' } } }),
  };
}

export function riskCategoryChart(counts) {
  const keys = ['Low', 'Medium', 'High'];
  return {
    data: [{
      type: 'bar', x: keys.map((k) => `${k} risk`), y: keys.map((k) => counts[k] || 0),
      marker: { color: keys.map((k) => RISK_COLORS[k]) }, text: keys.map((k) => String(counts[k] || 0)),
      textposition: 'outside', cliponaxis: false, hovertemplate: '%{x}: %{y} rows<extra></extra>',
    }],
    layout: baseLayout({ showlegend: false, yaxis: { ...baseLayout().yaxis, title: { text: 'Rows' } } }),
  };
}

export function riskHistogram(hist, thresholds) {
  const centers = hist.counts.map((_, i) => (hist.edges[i] + hist.edges[i + 1]) / 2);
  const color = centers.map((c) => (c >= thresholds.high ? RISK_COLORS.High : c >= thresholds.low ? RISK_COLORS.Medium : RISK_COLORS.Low));
  const line = (x) => ({ type: 'line', x0: x, x1: x, yref: 'paper', y0: 0, y1: 1, line: { color: '#606060', width: 1, dash: 'dot' } });
  return {
    data: [{ type: 'bar', x: centers, y: hist.counts, width: 0.05, marker: { color, line: { color: '#FFFFFF', width: 1 } },
      hovertemplate: 'Risk score %{x:.2f}<br>%{y} rows<extra></extra>' }],
    layout: baseLayout({ bargap: 0, showlegend: false, shapes: [line(thresholds.low), line(thresholds.high)],
      xaxis: { ...baseLayout().xaxis, range: [0, 1], title: { text: 'Model-estimated risk score' } },
      yaxis: { ...baseLayout().yaxis, title: { text: 'Rows' } } }),
  };
}

