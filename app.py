import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import os

st.set_page_config(page_title="TASI 2020 Market Simulator", layout="wide")

# 1. قائمة القطاعات والأسهم
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
        "Bahri (البحري)": "4030.SR"
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
for sec, stocks in MARKET_SECTORS.items():
    for name, sym in stocks.items():
        TICKER_TO_NAME[sym] = name
        NAME_TO_TICKER[name] = sym
        SECTOR_MAP[name] = sec

LISTING_DATES = {
    "4013.SR": "2020-03-17"  # إدراج الحبيب
}

# 2. خط زمني مفصل للأحداث حتى نهاية 2020
HISTORICAL_NEWS = {
    "2020-01-05": "📅 السوق يفتتح عام 2020 بتفاؤل مستمر بعد الطرح التاريخي لأرامكو.",
    "2020-01-20": "⚠️ الصين تؤكد انتقال فيروس كورونا المستجد بين البشر، والأسواق الآسيوية تضطرب.",
    "2020-02-03": "📉 تصاعد المخاوف العالمية من تعطل سلاسل الإمداد الصينية وتراجع واردات النفط.",
    "2020-02-27": "🚫 المملكة تقرر تعليق الدخول لأغراض العمرة وزيارة المسجد النبوي مؤقتاً كإجراء احترازي.",
    "2020-03-02": "🚨 وزارة الصحة تعلن تسجيل أول حالة إصابة مؤكدة بالفيروس قادمة من الخارج.",
    "2020-03-08": "🛑 تعليق الدراسة في كافة المدارس والجامعات، وإغلاق المنافذ لـ 9 دول.",
    "2020-03-09": "💥 فشل محادثات أوبك+ وبدء حرب أسعار نفطية.. خام برنت يهوي وتاسي يسجل هبوطاً حاداً.",
    "2020-03-11": "🌍 منظمة الصحة العالمية تصنف رسمياً تفشي كورونا كـ (جائحة عالمية).",
    "2020-03-14": "✈️ تعليق الرحلات الجوية الدولية بالكامل لمدة أسبوعين.",
    "2020-03-17": "🔔 إدراج وبدء تداول أسهم مجموعة د. سليمان الحبيب (4013) بسعر 50 ريالاً والسهم يرتفع بالنسبة القصوى.",
    "2020-03-20": "🏦 مؤسسة النقد (ساما) تطلق حزمة دعم تاريخية بقيمة 50 مليار ريال للقطاع الخاص والمنشآت الصغيرة.",
    "2020-03-23": "🔒 بدء تطبيق حظر التجول الجزئي المسائي من السابعة مساءً حتى السادسة صباحاً.",
    "2020-04-06": "🛑 فرض حظر تجول شامل على مدار 24 ساعة في عدد من المدن الرئيسية.",
    "2020-04-12": "🤝 اتفاق تاريخي: أوبك+ تقر أضخم خفض إنتاجي في تاريخ صناعة النفط (9.7 مليون برميل/يوم).",
    "2020-04-20": "💥 سابقة تاريخية لم تحدث قط: العقود الآجلة للنفط الأمريكي تهبط إلى ما دون الصفر (-37$).",
    "2020-05-03": "📊 بدء موسم إفصاحات الربع الأول 2020 وتراجع حاد في نتائج قطاع البتروكيماويات.",
    "2020-05-11": "💼 إقرار إجراءات مالية لضبط الميزانية شملت رفع ضريبة القيمة المضافة لـ 15%.",
    "2020-05-28": "🔓 بدء خطة العودة الحذرة وتخفيف أوقات حظر التجول تدريجياً.",
    "2020-06-21": "🎉 رفع حظر التجول بالكامل واستئناف جميع الأنشطة التجارية في عموم مدن المملكة.",
    "2020-08-05": "📊 إفصاحات الربع الثاني 2020 تعكس قاع التأثير المالي للحظر وتفوق قطاعي الرعاية والتجزئة الغذائية.",
    "2020-10-15": "📈 تحسن مؤشرات الطلب المحلي ونمو قياسي في عمليات نقاط البيع بعد إعادة الفتح.",
    "2020-11-09": "💉 فايزر وبيونتيك تعلنان نجاح لقاح كورونا بنسبة تفوق 90%، والأسواق العالمية تنفجر صعوداً.",
    "2020-12-17": "🇸🇦 انطلاق أكبر حملة تطعيم وطنية مجانية في المملكة وبدء مسار التعافي الصاروخي لتاسي.",
    "2020-12-31": "🏁 نهاية تداولات عام 2020 وإغلاق سنوي إيجابي لتاسي معوضاً كامل خسائر الجائحة."
}

# 3. القوائم والإفصاحات المالية
FINANCIAL_DISCLOSURES = {
    "1120.SR": {
        "Base_2019": {"Rev": "19.5 B", "Net": "10.2 B", "EPS": "4.08", "P/E": "16.1", "Notes": "نتائج مدققة لعام 2019 بنمو سنوي +13%"},
        "Q1_2020": {"Date": "2020-05-04", "Net": "2.38 B", "YoY": "-7.3%", "Notes": "ارتفاع المخصصات الائتمانية تحوطاً من الجائحة"},
        "Q2_2020": {"Date": "2020-08-04", "Net": "2.44 B", "YoY": "-5.4%", "Notes": "مرونة عالية في قطاع الأفراد ونمو محفظة التمويل"},
        "Q3_2020": {"Date": "2020-11-02", "Net": "2.66 B", "YoY": "+3.1%", "Notes": "تحول إيجابي ونمو واضح مع انحسار الإغلاقات"}
    },
    "2010.SR": {
        "Base_2019": {"Rev": "139.7 B", "Net": "5.6 B", "EPS": "1.87", "P/E": "49.5", "Notes": "انخفاض الأرباح لعام 2019 جراء تباطؤ قطاع البتروكيماويات عالمياً"},
        "Q1_2020": {"Date": "2020-05-10", "Net": "-0.95 B", "YoY": "خسائر", "Notes": "تسجيل خسائر فصلية نتيجة انخفاض متوسط أسعار البيع"},
        "Q2_2020": {"Date": "2020-08-10", "Net": "-2.22 B", "YoY": "خسائر", "Notes": "قاع الأزمة: تأثر حاد بالإغلاقات العالمية للشحن وسلاسل الإمداد"},
        "Q3_2020": {"Date": "2020-11-08", "Net": "+1.09 B", "YoY": "+47%", "Notes": "عودة قوية للربحية بالتزامن مع تعافي الطلب الصناعي عالمياً"}
    },
    "2222.SR": {
        "Base_2019": {"Rev": "1,105 B", "Net": "330.7 B", "EPS": "1.65", "P/E": "21.3", "Notes": "نتائج قياسية لعام 2019 مع التزام بتوزيع 75 مليار دولار أرباحاً"},
        "Q1_2020": {"Date": "2020-05-12", "Net": "62.5 B", "YoY": "-25%", "Notes": "صمود قوي للتدفقات النقدية رغم التراجع الحاد في أسعار النفط"},
        "Q2_2020": {"Date": "2020-08-09", "Net": "24.6 B", "YoY": "-73%", "Notes": "تأثير قاع انهيار أسعار النفط واتفاق خفض الإنتاج غير المسبوق لأوبك+"},
        "Q3_2020": {"Date": "2020-11-03", "Net": "44.2 B", "YoY": "-44%", "Notes": "تحسن تدريجي مع صعود خام برنت وتماسك التوزيعات النقدية"}
    },
    "4013.SR": {
        "Base_2019": {"Rev": "5.03 B", "Net": "870 M", "EPS": "2.49", "P/E": "20.1", "Notes": "أرقام نشرة الإصدار: نمو سنوي قوي وهوامش ربحية متميزة قبل الطرح"},
        "Q1_2020": {"Date": "2020-05-14", "Net": "246 M", "YoY": "+8.9%", "Notes": "إقبال تشغيلي قوي ومرونة عالية خلال بدايات انتشار الجائحة"},
        "Q2_2020": {"Date": "2020-08-16", "Net": "271 M", "YoY": "+25.1%", "Notes": "استفادة استثنائية من خدمات الفحوصات والخدمات الطبية الرقمية"},
        "Q3_2020": {"Date": "2020-11-01", "Net": "298 M", "YoY": "+26.8%", "Notes": "مواصلة تسجيل أرقام قياسية ونمو متسارع في مراجعي العيادات"}
    },
    "4190.SR": {
        "Base_2019": {"Rev": "8.4 B", "Net": "984 M", "EPS": "8.20", "P/E": "19.5", "Notes": "أداء قياسي لعام 2019 مدعوماً بمبيعات الإلكترونيات والهواتف"},
        "Q1_2020": {"Date": "2020-04-22", "Net": "251 M", "YoY": "+7.3%", "Notes": "إقبال كبير على الحواسيب والأجهزة اللوحية استعداداً للدراسة عن بعد"},
        "Q2_2020": {"Date": "2020-07-28", "Net": "163 M", "YoY": "-3.6%", "Notes": "إغلاق المعارض جزئياً جراء الحظر وتعويض النقص عبر التجارة الإلكترونية"},
        "Q3_2020": {"Date": "2020-10-21", "Net": "255 M", "YoY": "-16.4%", "Notes": "تأخر موسم العودة للمدارس الفعلي وتطبيق نسبة ضريبة 15%"}
    }
}

# 4. جلب البيانات التاريخية لعام 2020 فقط (تنتهي بـ 2020-12-31)
@st.cache_data
def load_all_market_data():
    all_syms = list(TICKER_TO_NAME.keys()) + ["KSA", "BZ=F"]
    raw = yf.download(all_syms, start="2020-01-01", end="2020-12-31", progress=False)
    if isinstance(raw.columns, pd.MultiIndex):
        close_df = raw['Close'] if 'Close' in raw.columns.levels[0] else raw['Adj Close']
    else:
        close_df = raw['Close']
    close_df = close_df.ffill().bfill().dropna(how='all')
    return close_df

market_prices = load_all_market_data()
dates_list = market_prices.index.strftime('%Y-%m-%d').tolist()

# إدارة ملف لوحة الصدارة (Leaderboard)
LEADERBOARD_FILE = "leaderboard.csv"

def get_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        return pd.read_csv(LEADERBOARD_FILE)
    return pd.DataFrame(columns=["اللاعب", "القيمة النهائية (ر.س)", "عائد المحفظة (%)", "عائد السوق (%)", "الفارق (Alpha)"])

def save_score(player_name, final_val, pnl, tasi_pnl, alpha):
    df = get_leaderboard()
    new_entry = pd.DataFrame([{
        "اللاعب": player_name,
        "القيمة النهائية (ر.س)": f"{final_val:,.0f}",
        "عائد المحفظة (%)": f"{pnl:+.2f}%",
        "عائد السوق (%)": f"{tasi_pnl:+.2f}%",
        "الفارق (Alpha)": f"{alpha:+.2f}%"
    }])
    df = pd.concat([df, new_entry], ignore_index=True)
    # ترتيب حسب نسبة الربح
    df["sort_val"] = df["عائد المحفظة (%)"].str.replace("%", "").astype(float)
    df = df.sort_values(by="sort_val", ascending=False).drop(columns=["sort_val"])
    df.to_csv(LEADERBOARD_FILE, index=False)

# إدارة الذاكرة
if "player_name" not in st.session_state:
    st.session_state.player_name = ""
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "score_saved" not in st.session_state:
    st.session_state.score_saved = False
if "step" not in st.session_state:
    st.session_state.step = 0
    st.session_state.is_running = False
    st.session_state.cash = 100000.0
    st.session_state.portfolio = {sym: 0 for sym in TICKER_TO_NAME.keys()}
    st.session_state.trade_history = []
    st.session_state.equity_curve = [100000.0]

# ----------------- شاشة التسجيل والترحيب (Onboarding) -----------------
if not st.session_state.game_started:
    st.markdown("## 🏛️ محاكي تداول تاسي: أزمة 2020 | TASI Crisis Terminal")
    st.markdown("---")
    
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown("""
        ### مرحباً بك في قاعة التداول 📊
        تخوض في هذه التجربة محاكاة واقعية لإدارة محفظة استثمارية بقيمة **100,000 ريال** خلال أحداث عام **2020** الكاملة (من يناير حتى ديسمبر):
        * انهيار أسواق النفط والأسهم العالمية (مارس 2020).
        * فرض الإغلاقات وحظر التجول وتداعيات الجائحة.
        * موجة التعافي بعد إعلان اللقاحات وحزم الدعم الحكومية.
        
        **الهدف:** إدارة السيولة واقتناص الفرص وتحقيق أفضل عائد استثماري مقارنة بمؤشر السوق.
        """)
        
        name_input = st.text_input("أدخل اسمك أو لقب التداول للبدء:", placeholder="مثال: تركي - مدير الصندوق")
        if st.button("🚀 بدء جلسات التداول", use_container_width=True):
            if name_input.strip():
                st.session_state.player_name = name_input.strip()
                st.session_state.game_started = True
                st.rerun()
            else:
                st.warning("فضلاً أدخل اسمك للمتابعة.")
                
    with c2:
        st.markdown("### 🏆 لوحة المتصدرين (Top Traders)")
        lb = get_leaderboard()
        if not lb.empty:
            st.dataframe(lb.head(10), use_container_width=True, hide_index=True)
        else:
            st.caption("لا توجد نتائج مسجلة حتى الآن.. كن أول من يسجل اسمه!")
            
    st.stop()

# ----------------- متابعة محرك اللعبة -----------------
is_finished = st.session_state.step >= len(dates_list) - 1

if st.session_state.is_running and not is_finished:
    st_autorefresh(interval=1200, key="market_tick_2020")
    st.session_state.step += 1

current_date = dates_list[st.session_state.step]
current_slice = market_prices.iloc[st.session_state.step]
prev_slice = market_prices.iloc[max(0, st.session_state.step - 1)]

brent_price = current_slice.get("BZ=F", 65.0)
brent_prev = prev_slice.get("BZ=F", 65.0)
brent_chg = ((brent_price - brent_prev) / brent_prev) * 100 if brent_prev > 0 else 0.0

initial_index = market_prices["KSA"].iloc[0]
current_index = market_prices["KSA"].iloc[st.session_state.step]
index_return = ((current_index - initial_index) / initial_index) * 100

stocks_equity = 0.0
for sym in TICKER_TO_NAME.keys():
    if sym in LISTING_DATES and current_date < LISTING_DATES[sym]:
        continue
    stocks_equity += st.session_state.portfolio[sym] * current_slice.get(sym, 0.0)

total_equity = st.session_state.cash + stocks_equity
pnl_pct = ((total_equity - 100000.0) / 100000.0) * 100

if len(st.session_state.equity_curve) <= st.session_state.step:
    st.session_state.equity_curve.append(total_equity)

past_news = [f"**{d}**: {msg}" for d, msg in sorted(HISTORICAL_NEWS.items()) if d <= current_date]
latest_headline = past_news[-1] if past_news else "انتظام التداولات وتوازن تدفقات السيولة."

# ----------------- شاشة النهاية والنتائج والليدربورد -----------------
if is_finished:
    st.session_state.is_running = False
    st.markdown(f"## 🏁 انتهت تداولات عام 2020 | ملخص أداء: {st.session_state.player_name}")
    st.markdown("---")
    
    alpha = pnl_pct - index_return
    
    # حفظ النتيجة تلقائياً مرة واحدة
    if not st.session_state.score_saved:
        save_score(st.session_state.player_name, total_equity, pnl_pct, index_return, alpha)
        st.session_state.score_saved = True

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("إجمالي المحفظة النهائية", f"{total_equity:,.0f} ر.س")
    r2.metric("عائد محفظتك", f"{pnl_pct:+.2f}%")
    r3.metric("عائد مؤشر تاسي (2020)", f"{index_return:+.2f}%")
    r4.metric("الفارق عن المؤشر (Alpha)", f"{alpha:+.2f}%")

    if alpha > 0:
        st.success(f"أداء متميز: استطعت إنهاء عام 2020 بعائد يفوق أداء مؤشر تاسي العام بفارق {alpha:+.2f}%.")
    else:
        st.info("أغلقت تداولات العام بنجاح. أظهرت التجربة أهمية التوزيع القطاعي وإدارة السيولة وقت الصدمات.")

    c_chart, c_board = st.columns([1.5, 1])
    with c_chart:
        eq_series = pd.Series(st.session_state.equity_curve)
        norm_eq = (eq_series / 100000.0) * 100
        norm_idx = (market_prices["KSA"].iloc[:len(eq_series)] / initial_index) * 100
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(y=norm_eq, mode="lines", name="محفظتك", line=dict(color="#27ae60", width=3)))
        fig_comp.add_trace(go.Scatter(y=norm_idx, mode="lines", name="مؤشر تاسي (KSA)", line=dict(color="#7f8c8d", dash="dash")))
        fig_comp.update_layout(title="مقارنة أداء المحفظة بمؤشر السوق عبر عام 2020", yaxis_title="القيمة المعيارية (الأساس 100)", height=350)
        st.plotly_chart(fig_comp, use_container_width=True)

    with c_board:
        st.markdown("### 🏆 لوحة المتصدرين المحدثة")
        st.dataframe(get_leaderboard().head(10), use_container_width=True, hide_index=True)

    if st.button("🔄 بدء محاولة جديدة"):
        st.session_state.step = 0
        st.session_state.game_started = False
        st.session_state.score_saved = False
        st.session_state.cash = 100000.0
        st.session_state.portfolio = {sym: 0 for sym in TICKER_TO_NAME.keys()}
        st.session_state.trade_history = []
        st.session_state.equity_curve = [100000.0]
        st.rerun()
    st.stop()

# ----------------- الشاشة الرئيسية لصالة التداول -----------------
st.markdown(f"### 🏛️ صالة تداول تاسي (2020) | المتداول: `{st.session_state.player_name}`")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("📅 جلسة السوق", current_date)
oil_icon = "🟢" if brent_chg > 0 else "🔴"
m2.metric("🛢️ خام برنت (Brent)", f"{brent_price:.2f} $", f"{oil_icon} {brent_chg:+.2f}%")
m3.metric("📈 تاسي (KSA)", f"{current_index:.2f}", f"{index_return:+.2f}%")
m4.metric("💵 السيولة المتاحة (كاش)", f"{st.session_state.cash:,.0f} SAR")
m5.metric("💼 إجمالي المحفظة", f"{total_equity:,.0f} SAR", f"{pnl_pct:+.2f}%")

st.error(f"🚨 **آخر خبر ومستجد:** {latest_headline}")
with st.expander(f"📜 شريط الأحداث التاريخية المتراكمة ({len(past_news)} حدثاً)"):
    for item in reversed(past_news):
        st.write(item)

c_play, c_step, c_reset = st.columns([1.5, 1, 1])
with c_play:
    btn_text = "⏸️ إيقاف مؤقت (Pause)" if st.session_state.is_running else "▶️ تشغيل السوق (Play)"
    if st.button(btn_text, use_container_width=True):
        st.session_state.is_running = not st.session_state.is_running
        st.rerun()

with c_step:
    if st.button("⏩ جلسة تالية (+1D)", use_container_width=True):
        st.session_state.is_running = False
        if st.session_state.step < len(dates_list) - 1:
            st.session_state.step += 1
            st.rerun()

with c_reset:
    if st.button("🔄 تصفير المحفظة", use_container_width=True):
        st.session_state.step = 0
        st.session_state.is_running = False
        st.session_state.cash = 100000.0
        st.session_state.portfolio = {sym: 0 for sym in TICKER_TO_NAME.keys()}
        st.session_state.trade_history = []
        st.session_state.equity_curve = [100000.0]
        st.rerun()

st.divider()

col_board, col_desk = st.columns([1.8, 2.2])

with col_board:
    st.subheader("📋 أسعار السوق (Watchlist)")
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        selected_sector = st.selectbox("تصفية القطاع:", ["جميع القطاعات"] + list(MARKET_SECTORS.keys()))
    with f_c2:
        search_query = st.text_input("بحث بالسهم أو الرمز:")

    filtered_stocks = {}
    for name, sym in NAME_TO_TICKER.items():
        sec = SECTOR_MAP[name]
        if selected_sector != "جميع القطاعات" and sec != selected_sector:
            continue
        if search_query and (search_query.lower() not in name.lower() and search_query not in sym):
            continue
        filtered_stocks[name] = sym

    board_data = []
    for name, sym in filtered_stocks.items():
        is_unlisted = sym in LISTING_DATES and current_date < LISTING_DATES[sym]
        if is_unlisted:
            price_disp = "🔒 لم يُدرج بعد"
            chg_disp = "Pre-IPO"
        else:
            p_now = current_slice.get(sym, 0.0)
            p_old = prev_slice.get(sym, 0.0)
            chg = ((p_now - p_old) / p_old) * 100 if p_old > 0 else 0.0
            price_disp = f"{p_now:.2f}"
            icon = "🟢" if chg > 0 else ("🔴" if chg < 0 else "⚪")
            chg_disp = f"{icon} {chg:+.2f}%"

        board_data.append({
            "الرمز": sym.replace(".SR", ""),
            "الشركة": name,
            "السعر": price_disp,
            "التغير": chg_disp,
            "الكمية": st.session_state.portfolio[sym]
        })

    st.dataframe(pd.DataFrame(board_data), use_container_width=True, hide_index=True, height=320)

    st.markdown("#### 💼 المراكز المفتوحة")
    my_stocks = [
        {"الشركة": TICKER_TO_NAME[sym], "الكمية": qty, "القيمة": f"{qty * current_slice.get(sym, 0.0):,.1f} SAR"}
        for sym, qty in st.session_state.portfolio.items() if qty > 0
    ]
    if my_stocks:
        st.dataframe(pd.DataFrame(my_stocks), use_container_width=True, hide_index=True)
    else:
        st.caption("أنت في وضع الكاش بالكامل (100% Cash).")

with col_desk:
    st.subheader("⚡ التحليل وتنفيذ الأوامر")
    available_names = list(filtered_stocks.keys()) if filtered_stocks else list(NAME_TO_TICKER.keys())
    target_name = st.selectbox("اختر السهم:", available_names)
    target_sym = NAME_TO_TICKER[target_name]
    
    is_target_unlisted = target_sym in LISTING_DATES and current_date < LISTING_DATES[target_sym]

    tab_chart, tab_fin = st.tabs(["📈 حركة السعر والتداول", "📑 القوائم والإفصاحات"])

    with tab_chart:
        if is_target_unlisted:
            st.warning(f"⚠️ شركة {target_name} لم تُدرج بعد في السوق.\nتاريخ بدء التداول المقرر: {LISTING_DATES[target_sym]}")
        else:
            price_today = current_slice.get(target_sym, 0.0)
            shares_held = st.session_state.portfolio[target_sym]

            sub_hist = market_prices[target_sym].iloc[:st.session_state.step + 1]
            if target_sym in LISTING_DATES:
                sub_hist = sub_hist.loc[sub_hist.index >= LISTING_DATES[target_sym]]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sub_hist.index, y=sub_hist.values, mode="lines", name=target_name, line=dict(color="#2980b9", width=2.5)))
            fig.update_layout(title=f"{target_name} ({target_sym})", height=230, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig, use_container_width=True)

            ord_c1, ord_c2 = st.columns(2)
            with ord_c1:
                st.markdown(f"**سعر التنفيذ:** `{price_today:.2f}` SAR")
                max_buy = int(st.session_state.cash // price_today) if price_today > 0 else 0
                buy_qty = st.number_input(f"شراء (الأقصى {max_buy})", min_value=0, max_value=max_buy, step=100)
                if st.button(f"🟢 تنفيذ شراء ({target_sym.replace('.SR','')})", use_container_width=True):
                    st.session_state.is_running = False
                    cost = buy_qty * price_today
                    if cost <= st.session_state.cash and buy_qty > 0:
                        st.session_state.cash -= cost
                        st.session_state.portfolio[target_sym] += buy_qty
                        st.session_state.trade_history.append({"التاريخ": current_date, "النوع": "شراء", "السهم": target_name, "الكمية": buy_qty, "السعر": price_today})
                        st.success(f"تم شراء {buy_qty} سهم بنجاح")
                        st.rerun()

            with ord_c2:
                st.markdown(f"**الأسهم لديك:** `{shares_held}` سهم")
                sell_qty = st.number_input(f"بيع (الأقصى {shares_held})", min_value=0, max_value=shares_held, step=100)
                if st.button(f"🔴 تنفيذ بيع ({target_sym.replace('.SR','')})", use_container_width=True):
                    st.session_state.is_running = False
                    if sell_qty > 0:
                        rev = sell_qty * price_today
                        st.session_state.cash += rev
                        st.session_state.portfolio[target_sym] -= sell_qty
                        st.session_state.trade_history.append({"التاريخ": current_date, "النوع": "بيع", "السهم": target_name, "الكمية": sell_qty, "السعر": price_today})
                        st.warning(f"تم بيع {sell_qty} سهم بنجاح")
                        st.rerun()

    with tab_fin:
        st.markdown(f"#### 📑 القوائم والإفصاحات: {target_name}")
        if target_sym in FINANCIAL_DISCLOSURES:
            comp_data = FINANCIAL_DISCLOSURES[target_sym]
            b19 = comp_data.get("Base_2019", {})
            st.info(f"**📋 القوائم السنوية المدققة (FY 2019):**\n- الإيرادات: `{b19.get('Rev', 'N/A')}` | صافي الربح: `{b19.get('Net', 'N/A')}`\n- ربحية السهم (EPS): `{b19.get('EPS', 'N/A')} SAR` | مكرر الأرباح (P/E): `{b19.get('P/E', 'N/A')}`\n- *ملاحظة:* {b19.get('Notes', '')}")

            active_quarters = []
            for q_key in ["Q1_2020", "Q2_2020", "Q3_2020"]:
                if q_key in comp_data:
                    q_info = comp_data[q_key]
                    if current_date >= q_info["Date"]:
                        active_quarters.append({
                            "الفترة": q_key.replace("_", " "),
                            "تاريخ الإفصاح": q_info["Date"],
                            "صافي الربح": q_info["Net"],
                            "النمو السنوي": q_info["YoY"],
                            "الملاحظات": q_info["Notes"]
                        })
            if active_quarters:
                st.dataframe(pd.DataFrame(active_quarters), use_container_width=True, hide_index=True)
            else:
                st.caption(f"لم تُعلن أي نتائج فصلية لعام 2020 حتى تاريخ جلسة اليوم ({current_date}).")
        else:
            st.caption("البيانات المالية التاريخية قيد التحديث لهذا السهم.")

if st.session_state.trade_history:
    with st.expander("📜 سجل العمليات المنفذة (Trade Execution Log)"):
        st.dataframe(pd.DataFrame(st.session_state.trade_history).iloc[::-1], use_container_width=True)
