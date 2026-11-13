// Number and DOM helpers shared by the page modules.

export const usd = (v) => "$" + Number(v).toLocaleString("en-US", { maximumFractionDigits: v >= 100 ? 0 : 2 });
export const pct = (v, digits = 0) => (v * 100).toFixed(digits) + "%";
export const signedPct = (v, digits = 1) => (v >= 0 ? "+" : "−") + Math.abs(v * 100).toFixed(digits) + "%";
export const shortDate = (iso) =>
  new Date(iso + "T00:00:00Z").toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });

export function addDays(iso, n) {
  const d = new Date(iso + "T00:00:00Z");
  d.setUTCDate(d.getUTCDate() + n);
  return d.toISOString().slice(0, 10);
}

export const cssVar = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

export function withAlpha(hex, alpha) {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${n >> 16}, ${(n >> 8) & 255}, ${n & 255}, ${alpha})`;
}

/** Fill a table from a header list and rows of cell strings. Text only, never HTML. */
export function fillTable(table, headers, rows, emptyText) {
  table.replaceChildren();
  const head = table.createTHead().insertRow();
  headers.forEach((h) => {
    const th = document.createElement("th");
    th.scope = "col";
    th.textContent = h;
    head.append(th);
  });
  const body = table.createTBody();
  if (!rows.length) {
    const td = body.insertRow().insertCell();
    td.colSpan = headers.length;
    td.className = "empty";
    td.textContent = emptyText;
    return;
  }
  rows.forEach((cells) => {
    const tr = body.insertRow();
    cells.forEach((c) => (tr.insertCell().textContent = c));
  });
}

export async function loadJson(name) {
  const res = await fetch(`data/${name}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`${name}: HTTP ${res.status}`);
  return res.json();
}
