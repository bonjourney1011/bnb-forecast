// Chart.js builders. Colors are read from CSS variables so light and dark mode each use
// their own validated steps.
import { addDays, cssVar, shortDate, usd, withAlpha } from "./format-helpers.js";

const charts = {};

function baseOptions(yType) {
  const ink3 = cssVar("--ink-3");
  const grid = cssVar("--line");
  return {
    responsive: true,
    maintainAspectRatio: false,
    animation: false,
    interaction: { mode: "index", intersect: false },
    scales: {
      x: { grid: { display: false }, ticks: { color: ink3, maxTicksLimit: 7, maxRotation: 0 }, border: { color: grid } },
      y: { type: yType, grid: { color: grid }, ticks: { color: ink3, maxTicksLimit: 6 }, border: { display: false } },
    },
    plugins: {
      legend: { display: false },
      tooltip: { backgroundColor: cssVar("--ink"), titleColor: cssVar("--paper"), bodyColor: cssVar("--paper"), padding: 10 },
    },
  };
}

function draw(id, config) {
  charts[id]?.destroy();
  charts[id] = new Chart(document.getElementById(id), config);
}

/** History line, plus (when `fan` is given) the median and the 50% and 80% ranges. */
export function drawFan(data, fan) {
  const hist = data.history;
  const future = fan ? fan.q0_5.slice(1).map((_, i) => addDays(data.as_of, i + 1)) : [];
  const labels = [...hist.dates, ...future].map(shortDate);
  const pad = new Array(hist.dates.length - 1).fill(null);
  const accent = cssVar("--series-1");
  const line = (label, values, extra) => ({ label, data: values, pointRadius: 0, pointHoverRadius: 4, borderWidth: 2, tension: 0, ...extra });

  const datasets = [line("Daily close", hist.close, { borderColor: cssVar("--history"), borderWidth: 1.5 })];
  if (fan) {
    const band = (label, key, fill, alpha) =>
      line(label, [...pad, ...fan[key]], { borderWidth: 0, pointHoverRadius: 0, fill, backgroundColor: withAlpha(accent, alpha) });
    datasets.push(
      line("Median", [...pad, ...fan.q0_5], { borderColor: accent }),
      band("90th percentile", "q0_9", false, 0),
      band("10th percentile", "q0_1", "-1", 0.16),
      band("75th percentile", "q0_75", false, 0),
      band("25th percentile", "q0_25", "-1", 0.22),
    );
  }
  const options = baseOptions("linear");
  options.scales.y.ticks.callback = (v) => usd(v);
  options.plugins.tooltip.callbacks = { label: (c) => (c.parsed.y == null ? null : `${c.dataset.label}: ${usd(c.parsed.y)}`) };
  options.plugins.tooltip.filter = (item) => item.parsed.y != null;
  draw("fan-chart", { type: "line", data: { labels, datasets }, options });
}

/** Growth of 1 unit on a log axis: the rule versus buy and hold. Two series, so a legend. */
export function drawEquity(trading, modelLabel) {
  const s1 = cssVar("--series-1");
  const s2 = cssVar("--series-2");
  const series = (label, values, color, dash) => ({
    label, data: values, borderColor: color, backgroundColor: color, borderWidth: 2, borderDash: dash, pointRadius: 0, pointHoverRadius: 4,
  });
  const options = baseOptions("logarithmic");
  options.scales.y.ticks.callback = (v) => v + "×";
  options.plugins.legend = { display: true, position: "top", align: "start", labels: { color: cssVar("--ink-2"), boxWidth: 18, boxHeight: 2 } };
  options.plugins.tooltip.callbacks = { label: (c) => `${c.dataset.label}: ${c.parsed.y.toFixed(2)}×` };
  draw("equity-chart", {
    type: "line",
    data: {
      labels: trading.equity_dates.map(shortDate),
      datasets: [
        series(`Rule on ${modelLabel}`, trading.equity_strategy, s1, []),
        series("Buy and hold", trading.equity_buy_and_hold, s2, [6, 4]),
      ],
    },
    options,
  });
}
