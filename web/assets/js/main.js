import { drawEquity, drawFan } from "./charts.js";
import { addDays, fillTable, loadJson, pct, shortDate, signedPct, usd } from "./format-helpers.js";

const $ = (id) => document.getElementById(id);
const state = { forecast: null, summary: null, log: null, model: null, revealed: false };

const fanOf = (model) =>
  Object.fromEntries(Object.entries(state.forecast.models[model].fan).map(([k, v]) => [k.replace(".", "_"), v]));

function verdictText(model) {
  const s = state.summary?.models[model];
  if (model === "random_walk") return "This is the baseline itself: the price stays put and the range comes from the last two years of returns.";
  if (!s) return "This model has no backtest yet, so its range is unverified. Read it with the random walk beside it.";
  const skill = s.mean_skill_vs_rw;
  const cov = s.by_horizon["30"].coverage_80;
  const head = skill > 0.01
    ? `In the backtest this model beat the random walk by ${pct(skill, 1)}.`
    : `In the backtest this model did not beat the random walk (skill ${signedPct(skill)}).`;
  return `${head} Its 80% range held the real 30-day outcome ${pct(cov)} of the time over ${s.origins} forecasts. Use the range to size risk; do not read the median as a call on direction.`;
}

function renderForecast() {
  const f = state.forecast;
  const fan = fanOf(state.model);
  const last = (key) => fan[key][fan[key].length - 1];
  $("t-median").textContent = usd(last("q0_5"));
  $("t-median-sub").textContent = `${signedPct(last("q0_5") / f.price - 1)} vs today, by ${shortDate(addDays(f.as_of, 30))}`;
  $("t-range").textContent = `${usd(last("q0_1"))} – ${usd(last("q0_9"))}`;
  $("t-up").textContent = pct(f.models[state.model].p_up_30);
  $("verdict").textContent = verdictText(state.model);
  [...$("model-tabs").children].forEach((b) => b.setAttribute("aria-selected", String(b.dataset.model === state.model)));
  drawFan(f, fan);
  const days = [1, 3, 7, 14, 21, 30];
  fillTable(
    $("fan-table"),
    ["Date", "5%", "10%", "25%", "Median", "75%", "90%", "95%"],
    days.map((d) => [shortDate(addDays(f.as_of, d)), ...["q0_05", "q0_1", "q0_25", "q0_5", "q0_75", "q0_9", "q0_95"].map((k) => usd(fan[k][d]))]),
  );
  $("fan-table-wrap").hidden = false;
}

function renderTabs() {
  const order = ["tabpfn", "chronos2", "random_walk_drift", "random_walk"].filter((m) => state.forecast.models[m]);
  $("model-tabs").replaceChildren(
    ...order.map((m) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "tab";
      b.role = "tab";
      b.dataset.model = m;
      b.textContent = state.forecast.labels[m];
      b.addEventListener("click", () => { state.model = m; renderForecast(); });
      return b;
    }),
  );
}

function renderScoreboard() {
  const s = state.summary;
  const models = Object.entries(s.models);
  const any = models[0][1];
  $("score-sub").textContent = `${any.origins} weekly forecast dates, ${shortDate(any.first_origin)} to ${shortDate(any.last_origin)}.`;
  fillTable(
    $("score-table"),
    ["Model", "Verdict", "Skill vs random walk", "30-day skill", "80% range held", "50% range held", "30-day direction", "Forecasts"],
    models.map(([m, v]) => {
      const h = v.by_horizon["30"];
      const d = v.direction_30d;
      const verdict = m === "random_walk" ? "Baseline" : v.mean_skill_vs_rw > 0.01 ? "✓ Beats baseline" : "✗ Does not beat baseline";
      const dir = d.accuracy == null ? "no view" : `${pct(d.accuracy)} (${pct(d.ci_low)}–${pct(d.ci_high)}, n=${d.n})`;
      return [s.labels[m], verdict, signedPct(v.mean_skill_vs_rw), signedPct(h.skill_vs_rw), pct(h.coverage_80), pct(h.coverage_50), dir, String(v.origins)];
    }),
  );
  if (!s.models.tabpfn || s.models.tabpfn.origins < any.origins) {
    const p = document.createElement("p");
    p.className = "muted";
    p.textContent = "TabPFN backtest not complete yet: it runs through a hosted API with a daily quota. Rows with fewer forecasts are not comparable.";
    $("score-table").parentElement.after(p);
  }
}

function renderLive() {
  const log = state.log;
  const track = state.forecast.track_model;
  const m = log.models[track];
  const rows = (m?.matured_30d ?? []).slice().reverse().map((r) => [
    shortDate(r.made_on), shortDate(r.target_date), `${usd(r.low)} – ${usd(r.high)}`, usd(r.median), usd(r.actual),
    r.actual >= r.low && r.actual <= r.high ? "✓ inside" : "✗ outside",
  ]);
  const due = log.first_forecast ? shortDate(addDays(log.first_forecast, 30)) : "";
  $("live-sub").textContent = m
    ? `${state.forecast.labels[track]}: 80% range held ${pct(m.coverage_80)} of ${m.matured} matured forecasts (all horizons).`
    : `Logging started ${log.first_forecast ? shortDate(log.first_forecast) : "today"}.`;
  fillTable($("live-table"), ["Forecast made", "Target date", "80% range", "Median", "Actual", "Result"], rows,
    `No 30-day forecast has matured yet. The first result is due on ${due}.`);
}

function renderTrading() {
  const full = state.summary.models.random_walk.origins;
  const pick = ["tabpfn", "chronos2", "random_walk_drift"].find((m) => {
    const s = state.summary.models[m];
    return s && s.trading && s.origins === full; // never promote a partial backtest
  });
  if (!pick) { $("trade-title").closest("section").hidden = true; return; }
  const t = state.summary.models[pick].trading;
  const label = state.summary.labels[pick];
  $("trade-sub").textContent = `${t.periods} four-week periods, ${shortDate(t.from)} to ${shortDate(t.to)}. The rule was in the market ${pct(t.share_in_market)} of the time and switched ${t.switches} times.`;
  drawEquity(t, label);
  const row = (name, s) => [name, signedPct(s.total_return, 0), signedPct(s.annual_return, 0), s.sharpe.toFixed(2), signedPct(s.max_drawdown, 0)];
  fillTable($("trade-table"), ["", "Total return", "Per year", "Sharpe", "Worst drawdown"],
    [row(`Rule on ${label}`, t.strategy), row("Buy and hold", t.buy_and_hold)]);
}

function redrawCharts() {
  if (state.revealed) renderForecast(); else drawFan(state.forecast, null);
  renderTrading();
}

async function init() {
  try {
    [state.forecast, state.summary, state.log] = await Promise.all(
      ["latest-forecast.json", "backtest-summary.json", "forecast-log.json"].map(loadJson));
  } catch (e) {
    $("as-of").textContent = "Could not load the forecast data. Please try again later.";
    console.error(e);
    return;
  }
  const f = state.forecast;
  state.model = f.primary;
  $("price").textContent = usd(f.price);
  $("as-of").textContent = `Close of ${shortDate(f.as_of)} (UTC) · forecast generated ${f.generated_at.replace("T", " ").replace("Z", " UTC")}`;
  renderTabs();
  renderScoreboard();
  renderLive();
  redrawCharts();
  const btn = $("forecast-btn");
  btn.disabled = false;
  btn.addEventListener("click", () => {
    state.revealed = true;
    $("forecast").hidden = false;
    btn.textContent = `Forecast to ${shortDate(addDays(f.as_of, 30))}`;
    btn.disabled = true;
    renderForecast();
  });
  if (location.hash === "#forecast") btn.click(); // shareable link straight to the forecast
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", redrawCharts);
}

init();
