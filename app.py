import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh

# ضبط إعدادات الصفحة
st.set_page_config(page_title="TASI COVID-19 Crisis Terminal", layout="wide")

# خريطة القطاعات والأسهم ثنائية اللغة
MARKET_SECTORS = {
    "Banking & Financials (البنوك والمالية)": {
        "Al Rajhi Bank (مصرف الراجحي)": "1120.SR",
        "SNB - AlAhli (البنك الأهلي)": "1180.SR",
        "Alinma Bank (مصرف الإنماء)": "1150.SR",
        "Bank AlBilad (بنك البلاد)": "1140.SR",
        "Riyad Bank (بنك الرياض)": "1010.SR"
    },
    "Energy & Utilities (الطاقة والمرافق)": {
        "Saudi Aramco (أرامكو السعودية)": "2222.SR",
        "Saudi Electricity (كهرباء السعودية)": "5110.SR",
        "Bahri (البحري للنقل البحري)": "4030.SR"
    },
    "Materials & Petrochem (المواد الأساسية والبتروكيماويات)": {
        "SABIC (سابك)": "2010.SR",
        "Maaden (معادن)": "1211.SR",
        "Yansab (ينساب)": "2290.SR",
        "SABIC Agri-Nutrients (سابك للمغذيات)": "2020.SR"
    },
    "Telecom & IT (الاتصالات والتقنية)": {
        "STC (إس تي سي)": "7010.SR",
        "Mobily (موبايلي)": "7020.SR",
        "Zain KSA (زين السعودية)": "7030.SR"
    },
    "Healthcare & Pharma (الرعاية الصحية)": {
        "Dr. Sulaiman Al Habib (سليمان الحبيب)": "4013.SR",
        "Mouwasat (المواساة)": "4002.SR",
        "Dallah Health (دله الصحية)": "4004.SR"
    },
    "Retail & Food (التجزئة والأغذية)": {
        "Almarai (المراعي)": "2280.SR",
        "Savola (صافولا)": "2050.SR",
        "Jarir Marketing (جرير للتسويق)": "4190.SR",
        "Othaim Markets (أسواق العثيم)": "4001.SR"
    }
}

TICKER_TO_NAME = {}
NAME_TO_TICKER = {}
SECTOR_MAP = {}
for sec_name, stocks in MARKET_SECTORS.items():
    for stock_name, ticker in stocks.items():
        TICKER_TO_NAME[ticker] = stock_name
        NAME_TO_TICKER[stock_name] = ticker
        SECTOR_MAP[stock_name] = sec_name

# الأحداث التاريخية المفصلية
HISTORICAL_NEWS = {
    "2020-01-20": "⚠️ Breaking: China confirms human-to-human transmission of coronavirus (الصين تؤكد انتقال كورونا بين البشر).",
    "2020-02-27": "🚫 Alert: KSA suspends entry for Umrah pilgrims as a preventive measure (تعليق الدخول لأغراض العمرة مؤقتاً).",
    "2020-03-02": "🚨 First Case: Saudi Ministry of Health confirms first COVID-19 infection (تسجيل أول حالة مؤكدة بالمملكة).",
    "2020-03-08": "🛑 Closures: Suspension of all schools and selective flights (تعليق الدراسة وإغلاق المنافذ لعدة دول).",
    "2020-03-09": "📉 Oil Crash: OPEC+ talks collapse, crude price war begins (فشل اتفاق أوبك+، واشتعال حرب أسعار النفط).",
    "2020-03-11": "🌍 Pandemic: WHO declares COVID-19 a global pandemic (منظمة الصحة العالمية تعلن كورونا جائحة عالمية).",
    "2020-03-20": "🏦 Stimulus: SAMA unveils SAR 50 Billion support package (ساما تطلق حزمة دعم بـ 50 مليار ريال).",
    "2020-03-23": "🔒 Curfew: Partial nationwide night curfew begins (بدء تطبيق حظر التجول المسائي الجزئي).",
    "2020-04-12": "🤝 Historic Deal: OPEC+ agrees to record oil cut of 9.7M bpd (أوبك+ تقر أضخم خفض إنتاجي بـ 9.7 مليون برميل).",
    "2020-04-20": "💥 Negative Oil: US WTI oil futures crash below zero to -$37/bbl (عقود النفط الأمريكي تهبط دون الصفر -37 دولار).",
    "2020-05-11": "💼 Fiscal Measures: Saudi VAT rate hiked to 15% (رفع ضريبة القيمة المضافة لـ 15% لدعم المالية العامة).",
    "2020-06-21": "🔓 Reopening: Full lifting of curfew and business resumption (رفع حظر التجول وعودة الأنشطة الاقتصادية).",
    "2020-11-09": "💉 Vaccine Breakthrough: Pfizer announces 90% vaccine efficacy (فايزر تعلن نجاح اللقاح بنسبة 90% والأسواق تقفز).",
    "2020-12-17": "🇸🇦 National Campaign: Saudi Arabia begins massive vaccine rollout (المملكة تبدأ حملة التطعيم الكبرى وبدء التعافي)."
}

# جلب بيانات السوق والاحتفاظ بها في الكاش
@st.cache_data
def load_all_market_data():
    all_syms = list(TICKER_TO_NAME.keys()) + ["KSA"]
    raw = yf.download(all_syms, start="2020-01-01", end="2021-05-30", progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        close_df = raw['Close'] if 'Close' in raw.columns.levels[0] else raw['Adj Close']
    else:
        close_df = raw['Close']
    close_df = close_df.ffill().bfill().dropna(how='all')
    return close_df

market_prices = load_all_market_data()
dates_list = market_prices.index.strftime('%Y-%m-%d').tolist()

# تهيئة الذاكرة وحالة التداول
if "step" not in st.session_state:
    st.session_state.step = 0
    st.session_state.is_running = False
    st.session_state.cash = 100000.0
    st.session_state.portfolio = {sym: 0 for sym in TICKER_TO_NAME.keys()}
    st.session_state.trade_history = []
    st.session_state.equity_curve = [100000.0]

is_finished = st.session_state.step >= len(dates_list) - 1

# عداد مرور الأيام التلقائي
if st.session_state.is_running and not is_finished:
    st_autorefresh(interval=1200, key="bilingual_market_tick")
    st.session_state.step += 1

current_date = dates_list[st.session_state.step]
current_slice = market_prices.iloc[st.session_state.step]
prev_slice = market_prices.iloc[max(0, st.session_state.step - 1)]

# حساب القيمة الإجمالية للمحفظة
stocks_equity = sum(st.session_state.portfolio[sym] * current_slice.get(sym, 0.0) for sym in TICKER_TO_NAME.keys())
total_equity = st.session_state.cash + stocks_equity
pnl_pct = ((total_equity - 100000.0) / 100000.0) * 100

if len(st.session_state.equity_curve) <= st.session_state.step:
    st.session_state.equity_curve.append(total_equity)

initial_index = market_prices["KSA"].iloc[0]
current_index = market_prices["KSA"].iloc[st.session_state.step]
index_return = ((current_index - initial_index) / initial_index) * 100

# ----------------- شاشة نهاية المحاكاة والتقييم السلوكي -----------------
if is_finished:
    st.session_state.is_running = False
    st.balloons()
    st.markdown("## 🏁 Crisis Simulation Complete | نهاية المحاكاة")
    st.markdown("---")
    
    eq_series = pd.Series(st.session_state.equity_curve)
    cum_max = eq_series.cummax()
    drawdown = (eq_series - cum_max) / cum_max
    max_dd = drawdown.min() * 100
    alpha = pnl_pct - index_return
    
    if alpha > 15:
        badge = "🏆 Legendary Bottom-Fisher (صائد القيعان الأسطوري)"
        analysis = "You bought March 2020 bottoms and outperformed TASI by a wide margin (استغللت الانهيار واشتريت بالقيعان وتفوقت على السوق بفارق كبير)."
    elif alpha > 0:
        badge = "📈 Prudent Alpha-Generator (مستثمر حصيف ومنضبط)"
        analysis = "Generated solid positive returns and beat the market benchmark (حققت عائداً إيجابياً وتفوقت على المؤشر بحسن إدارة المخاطر)."
    elif pnl_pct > 0:
        badge = "🛡️ Defensive Capital Preserver (مستثمر دفاعي متحفظ)"
        analysis = "Preserved capital from drawdowns, but missed parts of the recovery rally (حميت محفظتك من الهبوط لكن فوتت جزءاً من الصعود القوي)."
    else:
        badge = "⚠️ Emotional Panic-Seller (متداول انفعالي ضحية الهلع)"
        analysis = "Reactions were swayed by panic news and sold near market bottoms (تأثرت بالهلع الإخباري وبعت في القيعان)."

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("Final Net Worth (إجمالي الثروة)", f"{total_equity:,.0f} SAR")
    r2.metric("Portfolio Return (عائد المحفظة)", f"{pnl_pct:+.2f}%")
    r3.metric("TASI Benchmark (عائد السوق)", f"{index_return:+.2f}%")
    r4.metric("Alpha Generated (الألفا)", f"{alpha:+.2f}%", f"Max DD: {max_dd:.1f}%")

    st.info(f"### Investor Diagnosis (التقييم السلوكي): {badge}\n\n{analysis}")
    
    norm_eq = (eq_series / 100000.0) * 100
    norm_idx = (market_prices["KSA"].iloc[:len(eq_series)] / initial_index) * 100
    fig_comp = go.Figure()
    fig_comp.add_trace(go.Scatter(y=norm_eq, mode="lines", name="Your Portfolio (محفظتك)", line=dict(color="#27ae60", width=3)))
    fig_comp.add_trace(go.Scatter(y=norm_idx, mode="lines", name="TASI Index / KSA (مؤشر تاسي)", line=dict(color="#7f8c8d", dash="dash")))
    fig_comp.update_layout(title="Wealth Curve vs TASI Benchmark", yaxis_title="Normalized Value (Base 100)")
    st.plotly_chart(fig_comp, use_container_width=True)

    if st.button("🔄 Restart Simulation (إعادة التحدي)"):
        st.session_state.step = 0
        st.session_state.cash = 100000.0
        st.session_state.portfolio = {sym: 0 for sym in TICKER_TO_NAME.keys()}
        st.session_state.trade_history = []
        st.session_state.equity_curve = [100000.0]
        st.rerun()
    st.stop()

# ----------------- الشاشة الرئيسية للمنصة -----------------
st.markdown("### 🏛️ TASI Market Terminal: 2020 COVID Crisis Simulator")

# شريط الأخبار
if current_date in HISTORICAL_NEWS:
    st.error(HISTORICAL_NEWS[current_date])
else:
    st.info(f"📰 Market Session ({current_date}): Normal trading flow; monitoring macro developments (جلسة تداول منتظمة وترقب للأخبار).")

# أزرار التحكم ومؤشرات المحفظة
c_play, c_step, c_reset, c_cash, c_tot = st.columns([1.5, 1, 1, 1.2, 1.2])
with c_play:
    btn_text = "⏸️ Pause (إيقاف مؤقت)" if st.session_state.is_running else "▶️ Play Market (تشغيل السوق)"
    if st.button(btn_text, use_container_width=True):
        st.session_state.is_running = not st.session_state.is_running
        st.rerun()

with c_step:
    if st.button("⏩ Next Session (+1D) (جلسة تالية)", use_container_width=True):
        st.session_state.is_running = False
        if st.session_state.step < len(dates_list) - 1:
            st.session_state.step += 1
            st.rerun()

with c_reset:
    if st.button("🔄 Reset (تصفير المحفظة)", use_container_width=True):
        st.session_state.step = 0
        st.session_state.is_running = False
        st.session_state.cash = 100000.0
        st.session_state.portfolio = {sym: 0 for sym in TICKER_TO_NAME.keys()}
        st.session_state.trade_history = []
        st.session_state.equity_curve = [100000.0]
        st.rerun()

with c_cash:
    st.metric("Available Cash (السيولة المتاحة)", f"{st.session_state.cash:,.1f} SAR")

with c_tot:
    st.metric("Total Equity (إجمالي المحفظة)", f"{total_equity:,.1f} SAR", f"{pnl_pct:+.2f}%")

st.divider()

col_board, col_desk = st.columns([1.8, 2.2])

with col_board:
    st.subheader("📋 Market Watchlist (جدول الأسعار)")
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        selected_sector = st.selectbox("Filter Sector (القطاع):", ["All Sectors (جميع القطاعات)"] + list(MARKET_SECTORS.keys()))
    with f_c2:
        search_query = st.text_input("Search Stock (بحث):")

    filtered_stocks = {}
    for name, sym in NAME_TO_TICKER.items():
        sec = SECTOR_MAP[name]
        if selected_sector != "All Sectors (جميع القطاعات)" and sec != selected_sector:
            continue
        if search_query and (search_query.lower() not in name.lower() and search_query not in sym):
            continue
        filtered_stocks[name] = sym

    board_data = []
    for name, sym in filtered_stocks.items():
        p_now = current_slice.get(sym, 0.0)
        p_old = prev_slice.get(sym, 0.0)
        chg = ((p_now - p_old) / p_old) * 100 if p_old > 0 else 0.0
        shares = st.session_state.portfolio[sym]
        icon = "🟢" if chg > 0 else ("🔴" if chg < 0 else "⚪")
        board_data.append({
            "Symbol (الرمز)": sym.replace(".SR", ""),
            "Asset (الشركة)": name,
            "Price (السعر)": f"{p_now:.2f}",
            "Change (التغير)": f"{icon} {chg:+.2f}%",
            "Holdings (أسهمك)": shares
        })

    st.dataframe(pd.DataFrame(board_data), use_container_width=True, hide_index=True, height=330)

    st.markdown("#### 💼 Active Positions (المراكز المفتوحة)")
    my_stocks = [
        {"Asset (السهم)": TICKER_TO_NAME[sym], "Qty (الكمية)": qty, "Market Value (القيمة السوقية)": f"{qty * current_slice.get(sym, 0.0):,.1f} SAR"}
        for sym, qty in st.session_state.portfolio.items() if qty > 0
    ]
    if my_stocks:
        st.dataframe(pd.DataFrame(my_stocks), use_container_width=True, hide_index=True)
    else:
        st.caption("100% Cash Position (أنت في وضع الكاش بالكامل).")

with col_desk:
    st.subheader("⚡ Order Execution Desk (شاشة التحليل والأوامر)")
    available_names = list(filtered_stocks.keys()) if filtered_stocks else list(NAME_TO_TICKER.keys())
    target_name = st.selectbox("Select Asset (اختر السهم):", available_names)
    target_sym = NAME_TO_TICKER[target_name]
    
    price_today = current_slice.get(target_sym, 0.0)
    shares_held = st.session_state.portfolio[target_sym]

    sub_hist = market_prices[target_sym].iloc[:st.session_state.step + 1]
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=sub_hist.index, y=sub_hist.values, mode="lines", name=target_name, line=dict(color="#2980b9", width=2.5)))
    fig.update_layout(title=f"{target_name} ({target_sym})", height=280, margin=dict(l=10, r=10, t=35, b=10))
    st.plotly_chart(fig, use_container_width=True)

    ord_c1, ord_c2 = st.columns(2)
    with ord_c1:
        st.markdown(f"**Execution Price:** `{price_today:.2f}` SAR")
        max_buy = int(st.session_state.cash // price_today) if price_today > 0 else 0
        buy_qty = st.number_input(f"Buy Qty (Max {max_buy})", min_value=0, max_value=max_buy, step=100)
        if st.button(f"🟢 Buy / شراء ({target_sym.replace('.SR','')})", use_container_width=True):
            st.session_state.is_running = False
            cost = buy_qty * price_today
            if cost <= st.session_state.cash and buy_qty > 0:
                st.session_state.cash -= cost
                st.session_state.portfolio[target_sym] += buy_qty
                st.session_state.trade_history.append({"Date": current_date, "Type": "BUY", "Symbol": target_sym.replace(".SR",""), "Qty": buy_qty, "Price": price_today})
                st.success(f"Executed BUY {buy_qty} shares in {target_name}")
                st.rerun()

    with ord_c2:
        st.markdown(f"**Shares Owned:** `{shares_held}` shares")
        sell_qty = st.number_input(f"Sell Qty (Max {shares_held})", min_value=0, max_value=shares_held, step=100)
        if st.button(f"🔴 Sell / بيع ({target_sym.replace('.SR','')})", use_container_width=True):
            st.session_state.is_running = False
            if sell_qty > 0:
                rev = sell_qty * price_today
                st.session_state.cash += rev
                st.session_state.portfolio[target_sym] -= sell_qty
                st.session_state.trade_history.append({"Date": current_date, "Type": "SELL", "Symbol": target_sym.replace(".SR",""), "Qty": sell_qty, "Price": price_today})
                st.warning(f"Executed SELL {sell_qty} shares in {target_name}")
                st.rerun()

# سجل العمليات في أسفل الصفحة
if st.session_state.trade_history:
    with st.expander("📜 Trade Execution Log (سجل العمليات التاريخية)"):
        st.dataframe(pd.DataFrame(st.session_state.trade_history).iloc[::-1], use_container_width=True)
