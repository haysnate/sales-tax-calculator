"use strict";

// ============================================================
//  Sales Tax Calculator: all math runs locally in the browser.
//  Rates as of July 1, 2026 (Tax Foundation midyear table).
//  Estimates only. Local rates vary by city and county.
// ============================================================

// state: statutory state rate (%). local: population-weighted average
// local rate (%). none: no statewide sales tax. mandatoryLocal: the state
// rate shown includes a mandatory statewide local add-on.
const STATES = {
  AL: { name: "Alabama", slug: "alabama", state: 4.00, local: 5.46 },
  AK: { name: "Alaska", slug: "alaska", state: 0, local: 1.82, none: true },
  AZ: { name: "Arizona", slug: "arizona", state: 5.60, local: 2.94 },
  AR: { name: "Arkansas", slug: "arkansas", state: 6.50, local: 2.98 },
  CA: { name: "California", slug: "california", state: 7.25, local: 1.78, mandatoryLocal: 1.25 },
  CO: { name: "Colorado", slug: "colorado", state: 2.90, local: 4.99 },
  CT: { name: "Connecticut", slug: "connecticut", state: 6.35, local: 0 },
  DE: { name: "Delaware", slug: "delaware", state: 0, local: 0, none: true },
  DC: { name: "District of Columbia", slug: "district-of-columbia", state: 6.00, local: 0 },
  FL: { name: "Florida", slug: "florida", state: 6.00, local: 0.98 },
  GA: { name: "Georgia", slug: "georgia", state: 4.00, local: 3.56 },
  HI: { name: "Hawaii", slug: "hawaii", state: 4.00, local: 0.50, get: true },
  ID: { name: "Idaho", slug: "idaho", state: 6.00, local: 0.03 },
  IL: { name: "Illinois", slug: "illinois", state: 6.25, local: 2.73 },
  IN: { name: "Indiana", slug: "indiana", state: 7.00, local: 0 },
  IA: { name: "Iowa", slug: "iowa", state: 6.00, local: 0.94 },
  KS: { name: "Kansas", slug: "kansas", state: 6.50, local: 2.21 },
  KY: { name: "Kentucky", slug: "kentucky", state: 6.00, local: 0 },
  LA: { name: "Louisiana", slug: "louisiana", state: 5.00, local: 5.13 },
  ME: { name: "Maine", slug: "maine", state: 5.50, local: 0 },
  MD: { name: "Maryland", slug: "maryland", state: 6.00, local: 0 },
  MA: { name: "Massachusetts", slug: "massachusetts", state: 6.25, local: 0 },
  MI: { name: "Michigan", slug: "michigan", state: 6.00, local: 0 },
  MN: { name: "Minnesota", slug: "minnesota", state: 6.875, local: 1.26 },
  MS: { name: "Mississippi", slug: "mississippi", state: 7.00, local: 0.06 },
  MO: { name: "Missouri", slug: "missouri", state: 4.225, local: 4.22 },
  MT: { name: "Montana", slug: "montana", state: 0, local: 0, none: true },
  NE: { name: "Nebraska", slug: "nebraska", state: 5.50, local: 1.48 },
  NV: { name: "Nevada", slug: "nevada", state: 6.85, local: 1.39 },
  NH: { name: "New Hampshire", slug: "new-hampshire", state: 0, local: 0, none: true },
  NJ: { name: "New Jersey", slug: "new-jersey", state: 6.625, local: 0, uez: true },
  NM: { name: "New Mexico", slug: "new-mexico", state: 4.875, local: 2.80 },
  NY: { name: "New York", slug: "new-york", state: 4.00, local: 4.54 },
  NC: { name: "North Carolina", slug: "north-carolina", state: 4.75, local: 2.35 },
  ND: { name: "North Dakota", slug: "north-dakota", state: 5.00, local: 2.09 },
  OH: { name: "Ohio", slug: "ohio", state: 5.75, local: 1.54 },
  OK: { name: "Oklahoma", slug: "oklahoma", state: 4.50, local: 4.56 },
  OR: { name: "Oregon", slug: "oregon", state: 0, local: 0, none: true },
  PA: { name: "Pennsylvania", slug: "pennsylvania", state: 6.00, local: 0.34 },
  RI: { name: "Rhode Island", slug: "rhode-island", state: 7.00, local: 0 },
  SC: { name: "South Carolina", slug: "south-carolina", state: 6.00, local: 1.49 },
  SD: { name: "South Dakota", slug: "south-dakota", state: 4.20, local: 1.91 },
  TN: { name: "Tennessee", slug: "tennessee", state: 7.00, local: 2.61 },
  TX: { name: "Texas", slug: "texas", state: 6.25, local: 1.95 },
  UT: { name: "Utah", slug: "utah", state: 6.10, local: 1.32, mandatoryLocal: 1.25 },
  VT: { name: "Vermont", slug: "vermont", state: 6.00, local: 0.43 },
  VA: { name: "Virginia", slug: "virginia", state: 5.30, local: 0.47, mandatoryLocal: 1.00 },
  WA: { name: "Washington", slug: "washington", state: 6.50, local: 3.07 },
  WV: { name: "West Virginia", slug: "west-virginia", state: 6.00, local: 0.60 },
  WI: { name: "Wisconsin", slug: "wisconsin", state: 5.00, local: 0.72 },
  WY: { name: "Wyoming", slug: "wyoming", state: 4.00, local: 1.39 },
};

// ---- helpers ----
const $ = (id) => document.getElementById(id);
const el = {
  modeAdd: $("modeAdd"), modeReverse: $("modeReverse"),
  amount: $("amount"), amountLabel: $("amountLabel"),
  state: $("state"), localRate: $("localRate"), localHint: $("localHint"),
  resultLabel: $("resultLabel"), resultValue: $("resultValue"),
  donut: $("donut"),
  legPriceLabel: $("legPriceLabel"), legPrice: $("legPrice"), legState: $("legState"),
  legLocal: $("legLocal"), legLocalRow: $("legLocalRow"),
  rBaseLabel: $("rBaseLabel"), rBase: $("rBase"),
  rState: $("rState"), rStateRate: $("rStateRate"),
  rLocal: $("rLocal"), rLocalRate: $("rLocalRate"), rLocalRow: $("rLocalRow"),
  rTax: $("rTax"), rCombined: $("rCombined"),
  rTotalLabel: $("rTotalLabel"), rTotal: $("rTotal"),
  taxNote: $("taxNote"),
  stateLinks: $("stateLinks"),
};
let mode = "add";

function num(node) {
  const v = String(node.value).replace(/[^0-9.]/g, "");
  const n = parseFloat(v);
  return isFinite(n) && n >= 0 ? n : 0;
}
function money(n) {
  if (!isFinite(n)) n = 0;
  return new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(n);
}
function pct(n) {
  return (Math.round(n * 1000) / 1000) + "%";
}

const COLORS = {};
["price", "state", "local"].forEach((k) => {
  COLORS[k] = getComputedStyle(document.documentElement).getPropertyValue("--c-" + k).trim();
});

function calc() {
  const s = STATES[el.state.value];
  const amount = num(el.amount);
  const stateRate = s.state / 100;
  const localRate = Math.min(num(el.localRate), 25) / 100;
  const combined = stateRate + localRate;

  let base, total;
  if (mode === "add") {
    base = amount;
    total = amount * (1 + combined);
  } else {
    total = amount;
    base = combined > 0 ? amount / (1 + combined) : amount;
  }
  const stateTax = base * stateRate;
  const localTax = base * localRate;
  const tax = stateTax + localTax;

  // ---- render ----
  el.resultLabel.textContent = mode === "add" ? "Total price with tax" : "Price before tax";
  el.resultValue.textContent = money(mode === "add" ? total : base);
  el.legPrice.textContent = money(base);
  el.legState.textContent = money(stateTax);
  el.legLocal.textContent = money(localTax);
  el.legLocalRow.hidden = localRate <= 0;
  el.rBase.textContent = money(base);
  el.rState.textContent = money(stateTax);
  el.rStateRate.textContent = pct(s.state);
  el.rLocal.textContent = money(localTax);
  el.rLocalRate.textContent = pct(Math.round(localRate * 100000) / 1000);
  el.rLocalRow.hidden = localRate <= 0;
  el.rTax.textContent = money(tax);
  el.rCombined.textContent = pct(Math.round(combined * 100000) / 1000);
  el.rTotal.textContent = money(total);

  const segs = [
    { color: COLORS.price, v: base },
    { color: COLORS.state, v: stateTax },
    { color: COLORS.local, v: localTax },
  ];
  const sum = segs.reduce((a, x) => a + x.v, 0);
  let acc = 0; const stops = [];
  for (const x of segs) {
    const p = sum > 0 ? (x.v / sum) * 100 : 0;
    if (p <= 0.01) continue;
    stops.push(`${x.color} ${acc.toFixed(2)}% ${(acc + p).toFixed(2)}%`);
    acc += p;
  }
  el.donut.style.background = acc > 0 ? `conic-gradient(${stops.join(", ")})` : "conic-gradient(rgba(148,163,184,.25) 0 100%)";

  let note = "Rates as of July 1, 2026 (state rate plus the population-weighted average local rate). Your exact local rate depends on your city and county. ";
  if (s.none && s.local > 0) note += s.name + " has no statewide sales tax, but local governments levy their own. ";
  else if (s.none) note += s.name + " has no state or local sales tax. ";
  if (s.mandatoryLocal) note += "The " + s.name + " state rate shown includes a mandatory statewide local rate of " + s.mandatoryLocal + "%. ";
  if (s.get) note += "Hawaii technically levies a general excise tax on businesses rather than a sales tax; it works out similarly at the register. ";
  if (s.uez) note += "Some New Jersey urban enterprise zones charge half the state rate. ";
  note += "Groceries, clothing, and medicine are taxed differently in many states. Estimates only. Not tax or financial advice.";
  el.taxNote.textContent = note;
}

function setMode(m) {
  mode = m;
  el.modeAdd.classList.toggle("active", m === "add");
  el.modeReverse.classList.toggle("active", m === "reverse");
  el.amountLabel.textContent = m === "add" ? "Price before tax" : "Total price (tax included)";
  el.rBaseLabel.textContent = "Price before tax";
  el.rTotalLabel.textContent = "Total price";
  calc();
}

// ---- init state dropdown ----
Object.keys(STATES).sort((a, b) => STATES[a].name.localeCompare(STATES[b].name)).forEach((code) => {
  const o = document.createElement("option");
  o.value = code; o.textContent = STATES[code].name;
  el.state.appendChild(o);
});
el.state.value = (typeof window.PRESET_STATE === "string" && STATES[window.PRESET_STATE]) ? window.PRESET_STATE : "TX";
el.localRate.value = String(STATES[el.state.value].local);

// ---- state links (only on pages with the placeholder empty; static links are baked into index) ----

// ---- events ----
el.modeAdd.addEventListener("click", () => setMode("add"));
el.modeReverse.addEventListener("click", () => setMode("reverse"));
el.state.addEventListener("change", () => {
  el.localRate.value = String(STATES[el.state.value].local);
  calc();
});
[el.amount, el.localRate].forEach((n) => {
  n.addEventListener("input", calc);
  n.addEventListener("focus", () => n.select());
});

calc();
