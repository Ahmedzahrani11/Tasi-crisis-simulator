"use strict";

const INITIAL_CAPITAL = 100000;
const STATE_KEY = "tasi2020_state_v1";
const LOCAL_BOARD_KEY = "tasi2020_leaderboard_v1";
const DISCLOSURE_BADGE_DAYS = 10;

const STOCKS = SECTORS.flatMap(sec => sec.stocks.map(s => ({ ...s, sector: sec.name })));
const NAME_OF = Object.fromEntries(STOCKS.map(s => [s.symbol, s.name]));

let market = null;      // { dates, benchmark, series }
let state = null;
let timer = null;
let priceChart = null;
let reportChart = null;
let selectedSymbol = STOCKS[0].symbol;

// ---------------- Helpers ----------------
const $ = id => document.getElementById(id);
const fmt0 = new Intl.NumberFormat("en-US", { maximumFractionDigits: 0 });
const fmt2 = new Intl.NumberFormat("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
const sar = v => `${fmt0.format(v)} ريال`;
// LTR isolates (U+2066..U+2069) keep the sign and % in place inside RTL text
const pct = v => `\u2066${v >= 0 ? "+" : ""}${fmt2.format(v)}%\u2069`;
const signClass = v => (v > 0 ? "up" : v < 0 ? "down" : "");
const escapeHtml = s => String(s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

function freshState(player) {
  return {
    player,
    step: 0,
    cash: INITIAL_CAPITAL,
    portfolio: Object.fromEntries(STOCKS.map(s => [s.symbol, 0])),
    trades: [],
    curve: [INITIAL_CAPITAL],
    scoreSaved: false,
  };
}

function saveState() {
  try { localStorage.setItem(STATE_KEY, JSON.stringify(state)); } catch (e) { /* storage unavailable */ }
}

function loadState() {
  try { return JSON.parse(localStorage.getItem(STATE_KEY)); } catch (e) { return null; }
}

const lastStep = () => market.dates.length - 1;
const currentDate = () => market.dates[state.step];
const isUnlisted = (sym, date) => sym in LISTING_DATES && date < LISTING_DATES[sym];

function priceAt(sym, step) {
  const v = market.series[sym] ? market.series[sym][step] : null;
  return v != null && v > 0 ? v : null;
}

function totalEquity() {
  const date = currentDate();
  let stocks = 0;
  for (const [sym, qty] of Object.entries(state.portfolio)) {
    const px = priceAt(sym, state.step);
    if (qty && px && !isUnlisted(sym, date)) stocks += qty * px;
  }
  return state.cash + stocks;
}

function indexReturn(step) {
  const base = market.series.TASI[0];
  return ((market.series.TASI[step] - base) / base) * 100;
}

// One equity point per session, overwritten so same-day trades are reflected
function recordEquity() {
  while (state.curve.length <= state.step) state.curve.push(state.curve[state.curve.length - 1]);
  state.curve[state.step] = totalEquity();
}

function hasRecentDisclosure(sym, date) {
  const fin = FINANCIALS[sym];
  if (!fin) return false;
  const now = new Date(date);
  return fin.quarters.some(q => q.date <= date && (now - new Date(q.date)) / 86400000 <= DISCLOSURE_BADGE_DAYS);
}

function flash(kind, msg) {
  const el = $("flash");
  el.className = `alert ${kind}`;
  el.textContent = msg;
  clearTimeout(flash.t);
  flash.t = setTimeout(() => el.classList.add("hidden"), 4000);
}

// ---------------- Leaderboard ----------------
const useSupabase = () => Boolean(SUPABASE_URL && SUPABASE_ANON_KEY);
const sbHeaders = () => ({ apikey: SUPABASE_ANON_KEY, Authorization: `Bearer ${SUPABASE_ANON_KEY}`, "Content-Type": "application/json" });

async function fetchLeaderboard() {
  if (useSupabase()) {
    try {
      const res = await fetch(`${SUPABASE_URL}/rest/v1/leaderboard?select=player,final_value,pnl,benchmark_pnl,alpha&order=pnl.desc&limit=10`, { headers: sbHeaders() });
      if (res.ok) return await res.json();
    } catch (e) { /* fall through to local board */ }
  }
  try { return JSON.parse(localStorage.getItem(LOCAL_BOARD_KEY)) || []; } catch (e) { return []; }
}

async function submitScore(entry) {
  if (useSupabase()) {
    try {
      const res = await fetch(`${SUPABASE_URL}/rest/v1/leaderboard`, { method: "POST", headers: sbHeaders(), body: JSON.stringify(entry) });
      if (res.ok) return;
    } catch (e) { /* fall through to local board */ }
  }
  try {
    const board = JSON.parse(localStorage.getItem(LOCAL_BOARD_KEY)) || [];
    board.push(entry);
    board.sort((a, b) => b.pnl - a.pnl);
    localStorage.setItem(LOCAL_BOARD_KEY, JSON.stringify(board.slice(0, 50)));
  } catch (e) { /* storage unavailable */ }
}

async function renderLeaderboard(containerId) {
  const rows = await fetchLeaderboard();
  const el = $(containerId);
  if (!rows.length) {
    el.innerHTML = `<p class="muted">لا توجد نتائج مسجلة حتى الآن.. كن أول من يحقق عائداً ويسجل اسمه!</p>`;
    return;
  }
  el.innerHTML = `<div class="table-wrap"><table>
    <thead><tr><th>#</th><th>المتداول</th><th>القيمة النهائية</th><th>العائد</th><th>تاسي</th><th>ألفا</th></tr></thead>
    <tbody>${rows.slice(0, 10).map((r, i) => `<tr>
      <td>${i + 1}</td><td>${escapeHtml(r.player)}</td><td>${fmt0.format(r.final_value)}</td>
      <td class="${signClass(r.pnl)}">${pct(+r.pnl)}</td><td>${pct(+r.benchmark_pnl)}</td>
      <td class="${signClass(r.alpha)}">${pct(+r.alpha)}</td></tr>`).join("")}</tbody>
  </table></div>`;
}

// ---------------- Screens ----------------
function showScreen(name) {
  for (const s of ["onboarding", "terminal", "report"]) $(`screen-${s}`).classList.toggle("hidden", s !== name);
  window.scrollTo(0, 0);
}

function startGame(player) {
  state = freshState(player);
  saveState();
  enterTerminal();
}

function enterTerminal() {
  $("player-label").textContent = state.player;
  $("m-index-label").textContent = market.benchmark === "^TASI.SR" ? "📈 مؤشر تاسي (TASI)" : "📈 مؤشر السوق (MSCI KSA)";
  showScreen("terminal");
  renderAll();
  if (priceChart) priceChart.resize();
}

// ---------------- Clock ----------------
function setRunning(on) {
  clearInterval(timer);
  timer = on ? setInterval(advance, +$("speed").value) : null;
  $("btn-play").textContent = on ? "⏸️ إيقاف التداول مؤقتاً" : "▶️ بدء تشغيل الجلسات";
}

function advance() {
  if (state.step >= lastStep()) return finish();
  state.step += 1;
  recordEquity();
  saveState();
  if (state.step >= lastStep()) return finish();
  renderAll();
}

// ---------------- Terminal rendering ----------------
function renderAll() {
  recordEquity();
  renderMetrics();
  renderNews();
  renderWatchlist();
  renderPositions();
  renderDesk();
  renderTrades();
}

function renderMetrics() {
  const step = state.step;
  const prev = Math.max(0, step - 1);
  $("m-date").textContent = currentDate();
  $("m-session").textContent = `الجلسة ${step + 1} من ${market.dates.length}`;

  const brent = priceAt("BRENT", step), brentPrev = priceAt("BRENT", prev);
  const brentChg = brent && brentPrev ? ((brent - brentPrev) / brentPrev) * 100 : 0;
  $("m-brent").textContent = brent ? `${fmt2.format(brent)} $` : "—";
  $("m-brent-chg").textContent = pct(brentChg);
  $("m-brent-chg").className = signClass(brentChg);

  const idxRet = indexReturn(step);
  $("m-index").textContent = fmt2.format(market.series.TASI[step]);
  $("m-index-chg").textContent = `${pct(idxRet)} منذ بداية العام`;
  $("m-index-chg").className = signClass(idxRet);

  const eq = totalEquity();
  const pnl = ((eq - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100;
  $("m-cash").textContent = sar(state.cash);
  $("m-equity").textContent = sar(eq);
  $("m-pnl").textContent = pct(pnl);
  $("m-pnl").className = signClass(pnl);
}

function renderNews() {
  const date = currentDate();
  const past = NEWS.filter(n => n.date <= date);
  const latest = past[past.length - 1];
  $("headline").textContent = latest ? `${latest.date}: ${latest.text}` : "جلسة تداول منتظمة؛ وترقب لحركة السيولة والنتائج المالية.";
  $("news-summary").textContent = `📜 شريط الأحداث التاريخية المتراكمة (${past.length} حدثاً مسجلاً)`;
  $("news-list").innerHTML = past.slice().reverse().map(n => `<li><b>${n.date}</b>: ${escapeHtml(n.text)}</li>`).join("");
}

function filteredStocks() {
  const sector = $("sector-filter").value;
  const q = $("search").value.trim().toLowerCase();
  return STOCKS.filter(s => (!sector || s.sector === sector) && (!q || s.name.toLowerCase().includes(q) || s.symbol.includes(q)));
}

function renderWatchlist() {
  const date = currentDate();
  const step = state.step;
  $("watchlist").innerHTML = filteredStocks().map(s => {
    let price, change, cls = "";
    const now = priceAt(s.symbol, step);
    if (isUnlisted(s.symbol, date)) {
      price = "🔒 لم يُدرج بعد"; change = "ما قبل الطرح";
    } else if (now == null) {
      price = "—"; change = "لا تتوفر بيانات";
    } else {
      const old = priceAt(s.symbol, Math.max(0, step - 1));
      const chg = old ? ((now - old) / old) * 100 : 0;
      price = fmt2.format(now); change = pct(chg); cls = signClass(chg);
    }
    const bell = hasRecentDisclosure(s.symbol, date) ? "🔔 " : "";
    const sel = s.symbol === selectedSymbol ? " selected" : "";
    return `<tr class="clickable${sel}" data-symbol="${s.symbol}">
      <td>${s.symbol.replace(".SR", "")}</td><td>${bell}${s.name}</td><td>${price}</td>
      <td class="${cls}">${change}</td><td>${state.portfolio[s.symbol]}</td></tr>`;
  }).join("");
}

function renderPositions() {
  const held = Object.entries(state.portfolio).filter(([, q]) => q > 0);
  if (!held.length) {
    $("positions").innerHTML = `<p class="muted">المحفظة خالية من الأسهم حالياً (مركز كاش بالكامل بنسبة 100%).</p>`;
    return;
  }
  const eq = totalEquity();
  $("positions").innerHTML = `<div class="table-wrap"><table>
    <thead><tr><th>الشركة</th><th>الكمية</th><th>متوسط التكلفة</th><th>القيمة السوقية</th><th>الربح/الخسارة</th><th>الوزن</th></tr></thead>
    <tbody>${held.map(([sym, qty]) => {
      const value = qty * (priceAt(sym, state.step) || 0);
      const cost = avgCost(sym);
      const pl = cost ? ((value - cost * qty) / (cost * qty)) * 100 : 0;
      return `<tr><td>${NAME_OF[sym]}</td><td>${fmt0.format(qty)}</td><td>${fmt2.format(cost)}</td>
        <td>${fmt0.format(value)}</td><td class="${signClass(pl)}">${pct(pl)}</td><td>${fmt2.format((value / eq) * 100)}%</td></tr>`;
    }).join("")}</tbody></table></div>`;
}

// Weighted average cost of the shares still held (sells reduce quantity at the running average)
function avgCost(sym) {
  let qty = 0, cost = 0;
  for (const t of state.trades) {
    if (t.symbol !== sym) continue;
    if (t.side === "buy") { cost += t.qty * t.price; qty += t.qty; }
    else if (qty > 0) { cost -= (cost / qty) * t.qty; qty -= t.qty; }
  }
  return qty > 0 ? cost / qty : 0;
}

function renderStockSelect() {
  const sel = $("stock-select");
  sel.innerHTML = SECTORS.map(sec => `<optgroup label="${sec.name}">${sec.stocks.map(s =>
    `<option value="${s.symbol}">${s.name} (${s.symbol.replace(".SR", "")})</option>`).join("")}</optgroup>`).join("");
  sel.value = selectedSymbol;
}

function renderDesk() {
  const sym = selectedSymbol;
  const date = currentDate();
  const price = priceAt(sym, state.step);
  const locked = isUnlisted(sym, date) ? `⚠️ شركة ${NAME_OF[sym]} غير متاحة للتداول حالياً. موعد بدء التداول الرسمي في تاسي: ${LISTING_DATES[sym]}`
    : price == null ? `⚠️ لا تتوفر بيانات سعرية لسهم ${NAME_OF[sym]} في هذه الجلسة.` : "";
  $("order-locked").textContent = locked;
  $("order-locked").classList.toggle("hidden", !locked);
  $("order-desk").classList.toggle("hidden", Boolean(locked));
  renderFinancials();
  if (locked) return;

  const maxBuy = Math.floor(state.cash / price);
  const held = state.portfolio[sym];
  $("exec-price").textContent = `${fmt2.format(price)} ريال`;
  $("buy-max").textContent = `(الحد الأقصى ${fmt0.format(maxBuy)})`;
  $("held-qty").textContent = `${fmt0.format(held)} سهم`;
  $("buy-qty").max = maxBuy;
  $("sell-qty").max = held;
  updateOrderPreview();
  renderPriceChart();
}

function updateOrderPreview() {
  const price = priceAt(selectedSymbol, state.step) || 0;
  const b = Math.max(0, Math.floor(+$("buy-qty").value || 0));
  const s = Math.max(0, Math.floor(+$("sell-qty").value || 0));
  $("buy-cost").textContent = `التكلفة: ${sar(b * price)}`;
  $("sell-rev").textContent = `العائد: ${sar(s * price)}`;
}

function chartColors() {
  const css = getComputedStyle(document.documentElement);
  return { accent: css.getPropertyValue("--accent").trim(), muted: css.getPropertyValue("--muted").trim(), border: css.getPropertyValue("--border").trim(), up: css.getPropertyValue("--up").trim() };
}

function renderPriceChart() {
  const sym = selectedSymbol;
  const from = sym in LISTING_DATES ? market.dates.findIndex(d => d >= LISTING_DATES[sym]) : 0;
  const labels = market.dates.slice(from, state.step + 1);
  const data = market.series[sym].slice(from, state.step + 1);
  const c = chartColors();
  if (!priceChart) {
    priceChart = new Chart($("price-chart"), {
      type: "line",
      data: { labels, datasets: [{ data, borderColor: c.accent, borderWidth: 2, pointRadius: 0, tension: 0.15 }] },
      options: {
        animation: false, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
        plugins: { legend: { display: false } },
        scales: { x: { ticks: { maxTicksLimit: 6, color: c.muted }, grid: { display: false } }, y: { position: "right", ticks: { color: c.muted }, grid: { color: c.border } } },
      },
    });
  } else {
    priceChart.data.labels = labels;
    priceChart.data.datasets[0].data = data;
    priceChart.update("none");
  }
}

function renderFinancials() {
  const sym = selectedSymbol;
  const fin = FINANCIALS[sym];
  const el = $("tab-fin");
  if (!fin) {
    el.innerHTML = `<p class="alert info">البيانات والقوائم المالية المفصلة لهذا السهم قيد المراجعة والتدقيق.</p>`;
    return;
  }
  const date = currentDate();
  const f = fin.fy2019;
  const metric = (label, v) => `<div class="metric"><span>${label}</span><b>${v || "غير متوفر"}</b></div>`;
  const quarters = fin.quarters.filter(q => q.date <= date);
  el.innerHTML = `
    <h3>📋 القوائم السنوية المدققة لعام 2019 (الأساس قبل الأزمة)</h3>
    <div class="fin-grid">
      ${metric("إجمالي الإيرادات / الدخل", f.revenue)}${metric("صافي الدخل السنوي", f.netIncome)}${metric("ربحية السهم (EPS)", f.eps)}
      ${metric("مكرر الأرباح (P/E)", f.pe)}${f.roe ? metric("العائد على حقوق المساهمين", f.roe) : ""}${f.dividends ? metric("توزيعات الأرباح", f.dividends) : ""}
    </div>
    <p>📌 <b>الملاحظة المحاسبية:</b> ${f.note || ""}</p>
    <h3>📢 إفصاحات الأرباح الربعية المعلنة لعام 2020</h3>
    ${quarters.length ? `<div class="table-wrap"><table>
      <thead><tr><th>الفترة</th><th>تاريخ النشر</th><th>الدخل التشغيلي</th><th>صافي الربح</th><th>النمو السنوي</th><th>الأثر المالي</th></tr></thead>
      <tbody>${quarters.map(q => `<tr><td>${q.period}</td><td>${q.date}</td><td>${q.revenue}</td><td>${q.netIncome}</td><td>${q.yoy}</td><td class="wrap">${q.comment}</td></tr>`).join("")}</tbody>
    </table></div>` : `<p class="alert warn">لم تعلن الشركة عن أي نتائج مالية لعام 2020 حتى تاريخ جلسة اليوم (${date}). يبدأ موسم إفصاحات الربع الأول تدريجياً في أبريل ومايو 2020.</p>`}`;
}

function renderTrades() {
  $("trades-box").classList.toggle("hidden", !state.trades.length);
  $("trades").innerHTML = state.trades.slice().reverse().map(t => `<tr>
    <td>${t.date}</td><td class="${t.side === "buy" ? "up" : "down"}">${t.side === "buy" ? "شراء" : "بيع"}</td>
    <td>${NAME_OF[t.symbol]}</td><td>${fmt0.format(t.qty)}</td><td>${fmt2.format(t.price)}</td><td>${fmt0.format(t.qty * t.price)}</td></tr>`).join("");
}

// ---------------- Orders ----------------
function placeOrder(side) {
  setRunning(false);
  const sym = selectedSymbol;
  const price = priceAt(sym, state.step);
  if (price == null || isUnlisted(sym, currentDate())) return;
  const input = side === "buy" ? $("buy-qty") : $("sell-qty");
  const qty = Math.floor(+input.value || 0);
  if (qty <= 0) return flash("warn", "يرجى إدخال كمية أكبر من صفر.");

  if (side === "buy") {
    if (qty * price > state.cash + 1e-6) return flash("warn", "السيولة النقدية غير كافية لتنفيذ هذا الأمر.");
    state.cash -= qty * price;
    state.portfolio[sym] += qty;
  } else {
    if (qty > state.portfolio[sym]) return flash("warn", "الكمية المطلوبة أكبر من الأسهم المملوكة.");
    state.cash += qty * price;
    state.portfolio[sym] -= qty;
  }
  state.trades.push({ date: currentDate(), side, symbol: sym, qty, price });
  input.value = 0;
  saveState();
  flash(side === "buy" ? "ok" : "warn", `تم تنفيذ أمر ${side === "buy" ? "شراء" : "بيع"} ${fmt0.format(qty)} سهم من ${NAME_OF[sym]} بسعر ${fmt2.format(price)} ريال.`);
  renderAll();
}

function selectStock(sym) {
  selectedSymbol = sym;
  $("stock-select").value = sym;
  $("buy-qty").value = 0;
  $("sell-qty").value = 0;
  renderWatchlist();
  renderDesk();
}

// ---------------- End of year ----------------
async function finish() {
  setRunning(false);
  state.step = lastStep();
  recordEquity();
  const final = totalEquity();
  const pnl = ((final - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100;
  const idx = indexReturn(state.step);
  const alpha = pnl - idx;

  showScreen("report");
  $("report-player").textContent = state.player;
  $("r-final").textContent = sar(final);
  $("r-pnl").textContent = pct(pnl);
  $("r-pnl").className = signClass(pnl);
  $("r-index-label").textContent = market.benchmark === "^TASI.SR" ? "عائد مؤشر تاسي 2020" : "عائد مؤشر السوق 2020 (MSCI KSA)";
  $("r-index").textContent = pct(idx);
  $("r-alpha").textContent = pct(alpha);
  $("r-alpha").className = signClass(alpha);
  const verdict = $("r-verdict");
  verdict.className = `alert ${alpha > 0 ? "ok" : "info"}`;
  verdict.textContent = alpha > 0
    ? `أداء مالي استثنائي: أغلقت العام بعائد يتفوق على أداء مؤشر السوق بفارق إيجابي قدره ${pct(alpha)}.`
    : "أغلقت تداولات العام بنجاح؛ وقد أبرزت التجربة أهمية قراءة القوائم المالية وإدارة السيولة وقت الصدمات.";

  renderReportChart();
  if (!state.scoreSaved) {
    state.scoreSaved = true;
    saveState();
    await submitScore({ player: state.player, final_value: Math.round(final), pnl: +pnl.toFixed(2), benchmark_pnl: +idx.toFixed(2), alpha: +alpha.toFixed(2) });
  }
  renderLeaderboard("report-board");
}

function renderReportChart() {
  const c = chartColors();
  const base = market.series.TASI[0];
  const n = state.curve.length;
  const data = {
    labels: market.dates.slice(0, n),
    datasets: [
      { label: "محفظتك الاستثمارية", data: state.curve.map(v => (v / INITIAL_CAPITAL) * 100), borderColor: c.up, borderWidth: 3, pointRadius: 0 },
      { label: "مؤشر السوق", data: market.series.TASI.slice(0, n).map(v => (v / base) * 100), borderColor: c.muted, borderDash: [6, 4], borderWidth: 2, pointRadius: 0 },
    ],
  };
  if (reportChart) reportChart.destroy();
  reportChart = new Chart($("report-chart"), {
    type: "line", data,
    options: {
      animation: false, maintainAspectRatio: false, interaction: { mode: "index", intersect: false },
      plugins: { title: { display: true, text: "منحنى نمو الثروة مقابل مؤشر السوق (الأساس 100)", color: c.muted } },
      scales: { x: { ticks: { maxTicksLimit: 8, color: c.muted }, grid: { display: false } }, y: { position: "right", ticks: { color: c.muted }, grid: { color: c.border } } },
    },
  });
}

// ---------------- Wiring ----------------
function bindEvents() {
  $("start-form").addEventListener("submit", e => {
    e.preventDefault();
    const name = $("player-name").value.trim();
    if (name && market) startGame(name);
  });
  $("btn-play").addEventListener("click", () => setRunning(!timer));
  $("btn-next").addEventListener("click", () => { setRunning(false); advance(); });
  $("speed").addEventListener("change", () => { if (timer) setRunning(true); });
  $("btn-reset").addEventListener("click", () => {
    if (!confirm("سيتم تصفير المحفظة والعودة لأول جلسة. هل أنت متأكد؟")) return;
    setRunning(false);
    state = freshState(state.player);
    saveState();
    renderAll();
  });
  $("btn-restart").addEventListener("click", () => {
    try { localStorage.removeItem(STATE_KEY); } catch (e) { /* storage unavailable */ }
    state = null;
    showScreen("onboarding");
    renderLeaderboard("onboarding-board");
  });

  $("sector-filter").innerHTML = `<option value="">كافة القطاعات</option>` + SECTORS.map(s => `<option>${s.name}</option>`).join("");
  $("sector-filter").addEventListener("change", renderWatchlist);
  $("search").addEventListener("input", renderWatchlist);
  $("watchlist").addEventListener("click", e => {
    const row = e.target.closest("tr[data-symbol]");
    if (row) selectStock(row.dataset.symbol);
  });
  $("stock-select").addEventListener("change", e => selectStock(e.target.value));

  document.querySelectorAll(".tab").forEach(tab => tab.addEventListener("click", () => {
    document.querySelectorAll(".tab").forEach(t => t.classList.toggle("active", t === tab));
    $("tab-order").classList.toggle("hidden", tab.dataset.tab !== "order");
    $("tab-fin").classList.toggle("hidden", tab.dataset.tab !== "fin");
  }));

  $("buy-qty").addEventListener("input", updateOrderPreview);
  $("sell-qty").addEventListener("input", updateOrderPreview);
  $("buy-all").addEventListener("click", () => { $("buy-qty").value = $("buy-qty").max; updateOrderPreview(); });
  $("sell-all").addEventListener("click", () => { $("sell-qty").value = $("sell-qty").max; updateOrderPreview(); });
  $("btn-buy").addEventListener("click", () => placeOrder("buy"));
  $("btn-sell").addEventListener("click", () => placeOrder("sell"));
}

async function init() {
  bindEvents();
  renderStockSelect();
  renderLeaderboard("onboarding-board");
  try {
    const res = await fetch("data/prices.json", { cache: "no-cache" });
    if (!res.ok) throw new Error(res.status);
    market = await res.json();
  } catch (e) {
    const err = $("load-error");
    err.textContent = "تعذر تحميل بيانات الأسعار (data/prices.json). يرجى المحاولة لاحقاً.";
    err.classList.remove("hidden");
    return;
  }

  // Resume an unfinished game saved in this browser
  const saved = loadState();
  if (saved && saved.player && saved.step < market.dates.length && !saved.scoreSaved) {
    state = saved;
    enterTerminal();
  }
}

init();
