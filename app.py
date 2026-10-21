import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from streamlit_autorefresh import st_autorefresh
import os

# Page Configuration
st.set_page_config(page_title="TASI 2020 Crisis Simulator", layout="wide")

# ==============================================================================
# White-label Styling, Typography & RTL Setup
# ==============================================================================
custom_styling = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cairo:wght@400;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: 'Cairo', sans-serif !important;
    direction: rtl;
    text-align: right;
}

#MainMenu, footer, header {visibility: hidden !important;}
.viewerBadge_container__1QSob, [data-testid="stStatusWidget"], [data-testid="stToolbar"] {
    display: none !important;
}

/* Metric Card Layout */
div[data-testid="stMetric"] {
    background-color: #f8fafc;
    border: 1px solid #e2e8f0;
    padding: 12px;
    border-radius: 10px;
    box-shadow: 0 1px 3px rgba(0,0,0,0.05);
}

div[data-testid="stMetricLabel"] {
    font-size: 0.95rem !important;
    font-weight: 600 !important;
    color: #475569 !important;
}

/* Tabs Styling */
.stTabs [data-baseweb="tab-list"] {
    gap: 8px;
    direction: rtl;
}

.stTabs [data-baseweb="tab"] {
    font-size: 1.05rem;
    font-weight: 700;
    padding: 8px 16px;
    border-radius: 6px;
}
</style>
"""
st.markdown(custom_styling, unsafe_allow_html=True)

INITIAL_CAPITAL = 100000.0

# 1. Sector & Asset Mapping
MARKET_SECTORS = {
    "قطاع البنوك والمصارف": {
        "مصرف الراجحي": "1120.SR",
        "البنك الأهلي التجاري": "1180.SR",  # NCB in 2020 (became SNB after the 2021 Samba merger)
        "مصرف الإنماء": "1150.SR",
        "بنك البلاد": "1140.SR",
        "بنك الرياض": "1010.SR"
    },
    "قطاع الطاقة والمرافق": {
        "أرامكو السعودية": "2222.SR",
        "الشركة السعودية للكهرباء": "5110.SR",
        "البحري (النقل البحري)": "4030.SR"
    },
    "قطاع المواد الأساسية": {
        "سابك": "2010.SR",
        "معادن": "1211.SR",
        "ينساب": "2290.SR",
        "سابك للمغذيات الزراعية": "2020.SR"
    },
    "قطاع الاتصالات والتقنية": {
        "إس تي سي (stc)": "7010.SR",
        "موبايلي": "7020.SR",
        "زين السعودية": "7030.SR"
    },
    "قطاع الرعاية الصحية": {
        "مجموعة الدكتور سليمان الحبيب": "4013.SR",
        "المواساة": "4002.SR",
        "دله الصحية": "4004.SR"
    },
    "قطاع التجزئة والأغذية": {
        "المراعي": "2280.SR",
        "مجموعة صافولا": "2050.SR",
        "جرير للتسويق": "4190.SR",
        "أسواق عبدالله العثيم": "4001.SR"
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
    "4013.SR": "2020-03-17"  # Dr. Sulaiman Al Habib Listing Date
}

# Benchmark: the official TASI index if Yahoo serves it, otherwise the iShares MSCI Saudi ETF (KSA, USD) as a proxy
BENCHMARK_CANDIDATES = ["^TASI.SR", "KSA"]
BRENT_SYMBOL = "BZ=F"
# Optional offline snapshot of closing prices; avoids Yahoo rate limits on Streamlit Cloud when committed to the repo
SNAPSHOT_FILE = "market_data_2020.csv"

# 2. Historical Macro & Regulatory Timeline
HISTORICAL_NEWS = {
    "2020-01-05": "افتتاح تداولات عام 2020 بحالة من التفاؤل والزخم المستمر في السوق عقب طرح أرامكو التاريخي.",
    "2020-01-20": "تأكيد انتقال فيروس كورونا المستجد بين البشر رسمياً، وبداية اضطراب الأسواق الآسيوية وحركة الشحن.",
    "2020-02-03": "تصاعد المخاوف العالمية إزاء تباطؤ سلاسل الإمداد وانخفاض الطلب الصيني على واردات الطاقة.",
    "2020-02-27": "تعليق الدخول إلى المملكة لأغراض العمرة وزيارة المسجد النبوي الشريف مؤقتاً كإجراء وقائي احترازي.",
    "2020-03-02": "وزارة الصحة تعلن رصد أول حالة إصابة مؤكدة بفيروس كورونا قادمة من خارج المملكة.",
    "2020-03-08": "تعليق الحضور لمقرات التعليم المدرسي والجامعي، وفرض قيود على السفر مع تسع دول.",
    "2020-03-09": "فشل محادثات منظمة أوبك بلس واندلاع حرب حصص سوقية، مما أدى لهبوط حاد في أسعار النفط وضغط عنيف على تاسي.",
    "2020-03-11": "منظمة الصحة العالمية تعلن تصنيف انتشار فيروس كورونا كجائحة عالمية رسمية.",
    "2020-03-14": "تعليق الرحلات الجوية الدولية للمسافرين بالكامل لمدة أسبوعين لحماية الصحة العامة.",
    "2020-03-17": "إدراج وبدء تداول أسهم مجموعة الدكتور سليمان الحبيب بالرمز 4013 بسعر طرح بلغ 50 ريالاً وسط طلبات قياسية.",
    "2020-03-20": "مؤسسة النقد العربي السعودي (ساما) تعتمد برنامج دعم تمويلي تاريخي بقيمة 50 مليار ريال للقطاع الخاص.",
    "2020-03-23": "بدء سريان حظر التجول المسائي الجزئي من الساعة السابعة مساءً حتى السادسة صباحاً في كافة المناطق.",
    "2020-04-06": "تشديد التدابير وفرض حظر تجول شامل على مدار 24 ساعة في عدد من المدن الرئيسية بالمملكة.",
    "2020-04-12": "اتفاق استثنائي وتاريخي لدول أوبك بلس بإقرار أضخم خفض إنتاجي بواقع 9.7 مليون برميل يومياً لدعم استقرار الخام.",
    "2020-04-20": "واقعة غير مسبوقة في تاريخ الطاقة: العقود الآجلة للنفط الأمريكي تهبط إلى النطاق السالب مسجلة سالب 37 دولاراً.",
    "2020-05-03": "بدء إفصاح الشركات عن نتائج الربع الأول لعام 2020، وانعكاس هبوط أسعار المنتجات على قطاع البتروكيماويات.",
    "2020-05-11": "إقرار حزمة إجراءات مالية حكومية شملت زيادة نسبة ضريبة القيمة المضافة إلى 15% بهدف تحصين المالية العامة.",
    "2020-05-28": "إطلاق مرحلة العودة بحذر وتقليص فترات الحظر جزئياً مع الالتزام بالإجراءات الوقائية.",
    "2020-06-21": "رفع حظر التجول بشكل كامل في كافة مدن المملكة وعودة حركة الأنشطة التجارية والاقتصادية للعمل.",
    "2020-08-05": "إفصاحات الربع الثاني تعكس عمق أثر الإغلاقات على الصناعة مقابل أداء مالي دفاعي قوي لقطاعي التجزئة والرعاية.",
    "2020-10-15": "ارتفاع ملموس في عمليات نقاط البيع والاستهلاك المحلي تزامناً مع استعادة الدورة الاقتصادية عافيتها.",
    "2020-11-09": "إعلان شركتي فايزر وبيونتيك عن فعالية اللقاح بنسبة تتجاوز 90%، وصعود جماعي حاد في أسواق المال العالمية.",
    "2020-12-17": "انطلاق حملة التطعيم الوطنية الكبرى في المملكة بالمجان، وتأكيد مسار التعافي الاقتصادي المستدام.",
    "2020-12-31": "إغلاق التداولات السنوية لعام 2020 على مكاسب سنوية لتاسي متجاوزاً أثر الهبوط الكبير الذي شهده في الربع الأول."
}

# 3. Fundamental Disclosures & Accounting Metrics
FINANCIAL_STATEMENTS = {
    "1120.SR": {  # Al Rajhi Bank
        "FY_2019": {
            "إجمالي الدخل التشغيلي": "19.48 مليار ريال",
            "صافي الربح السنوي": "10.16 مليار ريال",
            "ربحية السهم (EPS)": "4.06 ريال",
            "مكرر الأرباح (P/E)": "16.2 مرة",
            "العائد على حقوق المساهمين": "20.1%",
            "نبذة القوائم": "أداء قياسي لعام 2019 بنمو سنوي بلغ 13% بدعم من قروض الأفراد والرهن العقاري."
        },
        "Quarters_2020": [
            {
                "الفترة": "الربع الأول 2020",
                "تاريخ النشر": "2020-05-04",
                "الدخل التشغيلي": "4.92 مليار ريال",
                "صافي الربح": "2.38 مليار ريال",
                "التغير السنوي": "-7.3%",
                "التعليق المالي": "انخفاض طفيف نتيجة رفع البنك للمخصصات الائتمانية تحوطاً من تداعيات تفشي الجائحة."
            },
            {
                "الفترة": "الربع الثاني 2020",
                "تاريخ النشر": "2020-08-04",
                "الدخل التشغيلي": "5.11 مليار ريال",
                "صافي الربح": "2.44 مليار ريال",
                "التغير السنوي": "-5.4%",
                "التعليق المالي": "صمود الدخل التشغيلي ونمو متماسك للودائع ومحفظة التمويل على الرغم من انخفاض أسعار الفائدة."
            },
            {
                "الفترة": "الربع الثالث 2020",
                "تاريخ النشر": "2020-11-02",
                "الدخل التشغيلي": "5.35 مليار ريال",
                "صافي الربح": "2.66 مليار ريال",
                "التغير السنوي": "+3.1%",
                "التعليق المالي": "العودة لتسجيل نمو سنوي إيجابي بدعم من نشاط قطاع التمويل السكني وتراجع تكاليف التمويل."
            }
        ]
    },
    "2010.SR": {  # SABIC
        "FY_2019": {
            "إجمالي الدخل التشغيلي": "139.7 مليار ريال",
            "صافي الربح السنوي": "5.63 مليار ريال",
            "ربحية السهم (EPS)": "1.88 ريال",
            "مكرر الأرباح (P/E)": "49.5 مرة",
            "العائد على حقوق المساهمين": "3.4%",
            "نبذة القوائم": "تأثرت نتائج 2019 بانخفاض حاد في أسعار البتروكيماويات عالمياً وتباطؤ النمو الصناعي الدولي."
        },
        "Quarters_2020": [
            {
                "الفترة": "الربع الأول 2020",
                "تاريخ النشر": "2020-05-10",
                "الدخل التشغيلي": "30.5 مليار ريال",
                "صافي الربح": "صافي خسارة (950 مليون ريال)",
                "التغير السنوي": "تحول للخسائر",
                "التعليق المالي": "تسجيل خسائر فصلية نتيجة انخفاض متوسط أسعار البيع وتسجيل مخصصات انخفاض في قيمة الأصول."
            },
            {
                "الفترة": "الربع الثاني 2020",
                "تاريخ النشر": "2020-08-10",
                "الدخل التشغيلي": "24.6 مليار ريال",
                "صافي الربح": "صافي خسارة (2.22 مليار ريال)",
                "التغير السنوي": "تعمق الخسائر",
                "التعليق المالي": "بلوغ قاع الأزمة جراء الإغلاقات العالمية الشاملة وتراجع هوامش الربحية التشغيلية لمنتجات اللقيم."
            },
            {
                "الفترة": "الربع الثالث 2020",
                "تاريخ النشر": "2020-11-08",
                "الدخل التشغيلي": "29.3 مليار ريال",
                "صافي الربح": "1.09 مليار ريال",
                "التغير السنوي": "+47.3%",
                "التعليق المالي": "تحول قوي ومفاجئ نحو الربحية تزامناً مع تحسن الطلب التصنيعي العالمي وصعود أسعار البيع."
            }
        ]
    },
    "2222.SR": {  # Saudi Aramco
        "FY_2019": {
            "إجمالي الدخل التشغيلي": "1,105 مليار ريال",
            "صافي الربح السنوي": "330.7 مليار ريال",
            "ربحية السهم (EPS)": "1.65 ريال",
            "مكرر الأرباح (P/E)": "21.3 مرة",
            "توزيعات الأرباح": "73.2 مليار دولار سنوياً",
            "نبذة القوائم": "أكبر شركة ربحية في العالم لعام 2019 والتزام ببرنامج توزيعات نقدية مستدامة للمساهمين."
        },
        "Quarters_2020": [
            {
                "الفترة": "الربع الأول 2020",
                "تاريخ النشر": "2020-05-12",
                "الدخل التشغيلي": "224.5 مليار ريال",
                "صافي الربح": "62.5 مليار ريال",
                "التغير السنوي": "-25.0%",
                "التعليق المالي": "مرونة تشغيلية نقدية بالغة القوة رغم بداية انحدار أسعار النفط الخام في الأسواق الدولية."
            },
            {
                "الفترة": "الربع الثاني 2020",
                "تاريخ النشر": "2020-08-09",
                "الدخل التشغيلي": "123.8 مليار ريال",
                "صافي الربح": "24.6 مليار ريال",
                "التغير السنوي": "-73.4%",
                "التعليق المالي": "أشد الفصول تأثراً بسبب انهيار أسعار برنت وتطبيق خفض الإنتاج غير المسبوق المتفق عليه في أوبك بلس."
            },
            {
                "الفترة": "الربع الثالث 2020",
                "تاريخ النشر": "2020-11-03",
                "الدخل التشغيلي": "158.4 مليار ريال",
                "صافي الربح": "44.2 مليار ريال",
                "التغير السنوي": "-44.6%",
                "التعليق المالي": "تحسن تدريجي متسارع في التدفقات النقدية التشغيلية وتأكيد سداد كامل التوزيعات النقدية المقررة."
            }
        ]
    },
    "4013.SR": {  # Dr. Sulaiman Al Habib
        "FY_2019": {
            "إجمالي الدخل التشغيلي": "5.03 مليار ريال",
            "صافي الربح السنوي": "870.2 مليون ريال",
            "ربحية السهم (EPS)": "2.49 ريال",
            "مكرر الأرباح (P/E)": "20.1 مرة",
            "العائد على حقوق المساهمين": "18.4%",
            "نبذة القوائم": "بيانات نشرة الإصدار: تحقيق نمو سنوي قوي بنسبة 8.7% وهوامش ربحية تشغيلية متفوقة قبل الطرح."
        },
        "Quarters_2020": [
            {
                "الفترة": "الربع الأول 2020",
                "تاريخ النشر": "2020-05-14",
                "الدخل التشغيلي": "1.34 مليار ريال",
                "صافي الربح": "246.6 مليون ريال",
                "التغير السنوي": "+8.9%",
                "التعليق المالي": "إقبال مرتفع على المراكز الطبية ومرونة العمليات مع بدء تفشي الأزمة الصحية."
            },
            {
                "الفترة": "الربع الثاني 2020",
                "تاريخ النشر": "2020-08-16",
                "الدخل التشغيلي": "1.41 مليار ريال",
                "صافي الربح": "271.4 مليون ريال",
                "التغير السنوي": "+25.1%",
                "التعليق المالي": "استفادة استثنائية من تقديم خدمات الفحوصات المخبرية وتطوير منظومة الرعاية الطبية الرقمية."
            },
            {
                "الفترة": "الربع الثالث 2020",
                "تاريخ النشر": "2020-11-01",
                "الدخل التشغيلي": "1.52 مليار ريال",
                "صافي الربح": "298.8 مليون ريال",
                "التغير السنوي": "+26.8%",
                "التعليق المالي": "مواصلة تحقيق أرقام ربحية تاريخية بدعم من زيادة أعداد المراجعين ونمو إيرادات قطاع الصيدليات."
            }
        ]
    },
    "4190.SR": {  # Jarir Marketing
        "FY_2019": {
            "إجمالي الدخل التشغيلي": "8.42 مليار ريال",
            "صافي الربح السنوي": "984.7 مليون ريال",
            "ربحية السهم (EPS)": "8.21 ريال",
            "مكرر الأرباح (P/E)": "19.5 مرة",
            "العائد على حقوق المساهمين": "58.2%",
            "نبذة القوائم": "أداء قياسي تاريخي لعام 2019 مدعوماً بمبيعات الإلكترونيات والهواتف الذكية وتوسع المعارض."
        },
        "Quarters_2020": [
            {
                "الفترة": "الربع الأول 2020",
                "تاريخ النشر": "2020-04-22",
                "الدخل التشغيلي": "2.21 مليار ريال",
                "صافي الربح": "251.7 مليون ريال",
                "التغير السنوي": "+7.3%",
                "التعليق المالي": "طلب واسع وكثيف على أجهزة الحاسب الآلي والأجهزة اللوحية استعداداً لتعليمات الدراسة والعمل عن بُعد."
            },
            {
                "الفترة": "الربع الثاني 2020",
                "تاريخ النشر": "2020-07-28",
                "الدخل التشغيلي": "2.05 مليار ريال",
                "صافي الربح": "163.5 مليون ريال",
                "التغير السنوي": "-3.6%",
                "التعليق المالي": "إغلاق المعارض جزئياً تماشياً مع الحظر وتعويض معظم المبيعات بنمو غير مسبوق لمتجرها الإلكتروني."
            },
            {
                "الفترة": "الربع الثالث 2020",
                "تاريخ النشر": "2020-10-21",
                "الدخل التشغيلي": "2.18 مليار ريال",
                "صافي الربح": "255.2 مليون ريال",
                "التغير السنوي": "-16.4%",
                "التعليق المالي": "تأثر نسبي بعد بدء تطبيق رفع ضريبة القيمة المضافة لـ 15% وتأجيل موسم العودة الحضورية للمدارس."
            }
        ]
    }
}

# 4. Market Data Engine
@st.cache_data(show_spinner="جاري تحميل بيانات السوق لعام 2020...")
def load_all_market_data():
    if os.path.exists(SNAPSHOT_FILE):
        close_df = pd.read_csv(SNAPSHOT_FILE, index_col=0, parse_dates=True)
    else:
        all_syms = list(TICKER_TO_NAME.keys()) + BENCHMARK_CANDIDATES + [BRENT_SYMBOL]
        # yfinance's end date is exclusive, so 2021-01-01 is needed to include the 2020-12-31 session
        raw = yf.download(all_syms, start="2020-01-01", end="2021-01-01", progress=False, auto_adjust=False)
        if raw.empty:
            return pd.DataFrame(), None
        price_field = "Close" if "Close" in raw.columns.get_level_values(0) else "Adj Close"
        close_df = raw[price_field]
        try:
            close_df.to_csv(SNAPSHOT_FILE)
        except OSError:
            pass

    # Keep only Tadawul sessions (Sun-Thu in 2020); Brent and the benchmark are carried forward onto them
    saudi_cols = [c for c in close_df.columns if c in TICKER_TO_NAME]
    saudi_sessions = close_df[saudi_cols].notna().any(axis=1)
    close_df = close_df.ffill().bfill().loc[saudi_sessions]

    benchmark = next((c for c in BENCHMARK_CANDIDATES if c in close_df.columns and close_df[c].notna().any()), None)
    if benchmark is None:
        return pd.DataFrame(), None
    close_df["TASI"] = close_df[benchmark]
    return close_df, benchmark

market_prices, benchmark_symbol = load_all_market_data()
if market_prices.empty:
    st.error("تعذر تحميل بيانات السوق من Yahoo Finance حالياً. يرجى إعادة المحاولة بعد قليل.")
    st.stop()
dates_list = market_prices.index.strftime('%Y-%m-%d').tolist()
benchmark_label = "مؤشر تاسي (TASI)" if benchmark_symbol == "^TASI.SR" else "مؤشر تاسي (KSA)"

def price_of(row, sym):
    val = row.get(sym, np.nan)
    return float(val) if pd.notna(val) and val > 0 else None

def is_unlisted(sym, date):
    return sym in LISTING_DATES and date < LISTING_DATES[sym]

# 5. Leaderboard Engine
LEADERBOARD_FILE = "leaderboard.csv"

def get_leaderboard():
    if os.path.exists(LEADERBOARD_FILE):
        return pd.read_csv(LEADERBOARD_FILE)
    return pd.DataFrame(columns=["اسم المتداول", "القيمة النهائية (ريال)", "عائد المحفظة (%)", "عائد تاسي (%)", "الفارق (ألفا)"])

def save_score(player_name, final_val, pnl, tasi_pnl, alpha):
    df = get_leaderboard()
    new_entry = pd.DataFrame([{
        "اسم المتداول": player_name,
        "القيمة النهائية (ريال)": f"{final_val:,.0f}",
        "عائد المحفظة (%)": f"{pnl:+.2f}%",
        "عائد تاسي (%)": f"{tasi_pnl:+.2f}%",
        "الفارق (ألفا)": f"{alpha:+.2f}%"
    }])
    df = pd.concat([df, new_entry], ignore_index=True)
    df["sort_val"] = df["عائد المحفظة (%)"].astype(str).str.replace("%", "").astype(float)
    df = df.sort_values(by="sort_val", ascending=False).drop(columns=["sort_val"])
    df.to_csv(LEADERBOARD_FILE, index=False)

# 6. Session State Management
def reset_portfolio():
    st.session_state.step = 0
    st.session_state.is_running = False
    st.session_state.last_tick = None
    st.session_state.cash = INITIAL_CAPITAL
    st.session_state.portfolio = {sym: 0 for sym in TICKER_TO_NAME.keys()}
    st.session_state.trade_history = []
    st.session_state.equity_curve = [INITIAL_CAPITAL]

if "player_name" not in st.session_state:
    st.session_state.player_name = ""
if "game_started" not in st.session_state:
    st.session_state.game_started = False
if "score_saved" not in st.session_state:
    st.session_state.score_saved = False
if "flash" not in st.session_state:
    st.session_state.flash = None
if "step" not in st.session_state:
    reset_portfolio()

# ----------------- Onboarding Screen -----------------
if not st.session_state.game_started:
    st.markdown("## 🏛️ منصة محاكاة تداول تاسي: تجربة أزمة عام 2020")
    st.markdown("---")
    c1, c2 = st.columns([1.5, 1])
    with c1:
        st.markdown("""
        ### أهلاً بك في قاعة التداول 📊
        تخوض في هذه التجربة محاكاة واقعية لإدارة محفظة استثمارية برأس مال قدره **100,000 ريال سعودي** خلال كافة جلسات عام **2020**:
        * **الصدمة:** انهيار أسعار النفط العالمية وقاع الأسواق في مارس.
        * **الإغلاق:** فترات الحظر وتأثر القطاعات الاقتصادية.
        * **الانفراجة:** إعلانات اللقاحات وتدفق برامج الدعم وعودة مسار التعافي.

        الهدف هو بناء محفظة متوازنة، الاستفادة من الإفصاحات المالية لكل شركة، وتحقيق أعلى عائد ممكن مقارنة بمؤشر السوق.
        """)
        name_input = st.text_input("أدخل اسمك أو لقب التداول للبدء:", placeholder="مثال: تركي - مدير الصندوق")
        if st.button("🚀 بدء جلسات التداول", width="stretch"):
            if name_input.strip():
                st.session_state.player_name = name_input.strip()
                st.session_state.game_started = True
                st.rerun()
            else:
                st.warning("يرجى إدخال الاسم قبل المتابعة.")
    with c2:
        st.markdown("### 🏆 لوحة المتصدرين الحالية")
        lb = get_leaderboard()
        if not lb.empty:
            st.dataframe(lb.head(10), width="stretch", hide_index=True)
        else:
            st.caption("لا توجد نتائج مسجلة حتى الآن.. كن أول من يحقق عائداً ويسجل اسمه!")
    st.stop()

# ----------------- Time-Step Engine -----------------
if st.session_state.is_running and st.session_state.step < len(dates_list) - 1:
    # Advance only on a genuine timer tick, not on reruns caused by widget interaction
    tick = st_autorefresh(interval=1200, key="market_tick_final")
    if tick != st.session_state.last_tick:
        st.session_state.last_tick = tick
        st.session_state.step += 1

is_finished = st.session_state.step >= len(dates_list) - 1

current_date = dates_list[st.session_state.step]
current_slice = market_prices.iloc[st.session_state.step]
prev_slice = market_prices.iloc[max(0, st.session_state.step - 1)]

brent_price = price_of(current_slice, BRENT_SYMBOL)
brent_prev = price_of(prev_slice, BRENT_SYMBOL)
brent_chg = ((brent_price - brent_prev) / brent_prev) * 100 if brent_price and brent_prev else 0.0

initial_index = market_prices["TASI"].iloc[0]
current_index = market_prices["TASI"].iloc[st.session_state.step]
index_return = ((current_index - initial_index) / initial_index) * 100

stocks_equity = 0.0
for sym, qty in st.session_state.portfolio.items():
    px = price_of(current_slice, sym)
    if qty and px and not is_unlisted(sym, current_date):
        stocks_equity += qty * px

total_equity = st.session_state.cash + stocks_equity
pnl_pct = ((total_equity - INITIAL_CAPITAL) / INITIAL_CAPITAL) * 100

# One equity point per session; overwritten so same-day trades are reflected
curve = st.session_state.equity_curve
while len(curve) <= st.session_state.step:
    curve.append(curve[-1])
curve[st.session_state.step] = total_equity

past_news = [f"**{d}**: {msg}" for d, msg in sorted(HISTORICAL_NEWS.items()) if d <= current_date]
latest_headline = past_news[-1] if past_news else "جلسة تداول منتظمة؛ وترقب لحركة السيولة والنتائج المالية."

# ----------------- End of Simulation Analytics -----------------
if is_finished:
    st.session_state.is_running = False
    st.markdown(f"## 🏁 انتهت تداولات عام 2020 | تقرير الأداء المالي للمتداول: {st.session_state.player_name}")
    st.markdown("---")

    alpha = pnl_pct - index_return
    if not st.session_state.score_saved:
        save_score(st.session_state.player_name, total_equity, pnl_pct, index_return, alpha)
        st.session_state.score_saved = True

    r1, r2, r3, r4 = st.columns(4)
    r1.metric("إجمالي القيمة النهائية", f"{total_equity:,.0f} ريال")
    r2.metric("عائد محفظتك النهائي", f"{pnl_pct:+.2f}%")
    r3.metric(f"عائد {benchmark_label} 2020", f"{index_return:+.2f}%")
    r4.metric("الفارق المحقق (ألفا)", f"{alpha:+.2f}%")

    if alpha > 0:
        st.success(f"أداء مالي استثنائي: أغلقت العام بعائد يتفوق على أداء مؤشر تاسي العام بفارق إيجابي قدره {alpha:+.2f}%.")
    else:
        st.info("أغلقت تداولات العام بنجاح؛ وقد أبرزت التجربة أهمية قراءة القوائم المالية وإدارة السيولة وقت الصدمات.")

    c_chart, c_board = st.columns([1.5, 1])
    with c_chart:
        eq_series = pd.Series(curve, index=market_prices.index[:len(curve)])
        norm_eq = (eq_series / INITIAL_CAPITAL) * 100
        norm_idx = (market_prices["TASI"].iloc[:len(curve)] / initial_index) * 100
        fig_comp = go.Figure()
        fig_comp.add_trace(go.Scatter(x=norm_eq.index, y=norm_eq.values, mode="lines", name="محفظتك الاستثمارية", line=dict(color="#10b981", width=3)))
        fig_comp.add_trace(go.Scatter(x=norm_idx.index, y=norm_idx.values, mode="lines", name=benchmark_label, line=dict(color="#64748b", dash="dash")))
        fig_comp.update_layout(title="منحنى نمو الثروة مقابل مؤشر السوق خلال عام 2020", yaxis_title="القيمة المعيارية (الأساس 100)", height=350)
        st.plotly_chart(fig_comp, width="stretch")

    with c_board:
        st.markdown("### 🏆 لوحة المتصدرين النهائية")
        st.dataframe(get_leaderboard().head(10), width="stretch", hide_index=True)

    if st.button("🔄 بدء محاولة جديدة"):
        reset_portfolio()
        st.session_state.game_started = False
        st.session_state.score_saved = False
        st.rerun()
    st.stop()

# ----------------- Main Trading Terminal -----------------
st.markdown(f"### 🏛️ صالة تداول السوق المالي (2020) | مدير المحفظة: `{st.session_state.player_name}`")

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("📅 تاريخ الجلسة", current_date)
oil_icon = "🟢" if brent_chg > 0 else "🔴"
m2.metric("🛢️ خام برنت العالمي", f"{brent_price:.2f} $" if brent_price else "—", f"{oil_icon} {brent_chg:+.2f}%")
m3.metric(f"📈 {benchmark_label}", f"{current_index:.2f}", f"{index_return:+.2f}%")
m4.metric("💵 السيولة النقدية (كاش)", f"{st.session_state.cash:,.0f} ريال")
m5.metric("💼 إجمالي قيمة المحفظة", f"{total_equity:,.0f} ريال", f"{pnl_pct:+.2f}%")

if st.session_state.flash:
    kind, msg = st.session_state.flash
    (st.success if kind == "success" else st.warning)(msg)
    st.session_state.flash = None

st.info(f"📢 **آخر تطور إخباري مؤثر:** {latest_headline}")
with st.expander(f"📜 شريط الأحداث التاريخية المتراكمة ({len(past_news)} حدثاً مسجلاً)"):
    for item in reversed(past_news):
        st.write(item)

c_play, c_step, c_reset = st.columns([1.5, 1, 1])
with c_play:
    btn_text = "⏸️ إيقاف التداول مؤقتاً" if st.session_state.is_running else "▶️ بدء تشغيل الجلسات"
    if st.button(btn_text, width="stretch"):
        st.session_state.is_running = not st.session_state.is_running
        st.rerun()

with c_step:
    if st.button("⏩ الجلسة التالية (+1D)", width="stretch"):
        st.session_state.is_running = False
        if st.session_state.step < len(dates_list) - 1:
            st.session_state.step += 1
            st.rerun()

with c_reset:
    if st.button("🔄 تصفير وإعادة الضبط", width="stretch"):
        reset_portfolio()
        st.rerun()

st.divider()

col_board, col_desk = st.columns([1.7, 2.3])

with col_board:
    st.subheader("📋 قائمة أسعار ومراقبة الأسهم")
    f_c1, f_c2 = st.columns(2)
    with f_c1:
        selected_sector = st.selectbox("تصفية بحسب القطاع:", ["كافة القطاعات"] + list(MARKET_SECTORS.keys()))
    with f_c2:
        search_query = st.text_input("بحث باسم السهم أو رمزه:")

    filtered_stocks = {}
    for name, sym in NAME_TO_TICKER.items():
        sec = SECTOR_MAP[name]
        if selected_sector != "كافة القطاعات" and sec != selected_sector:
            continue
        if search_query and (search_query.lower() not in name.lower() and search_query not in sym):
            continue
        filtered_stocks[name] = sym

    board_data = []
    for name, sym in filtered_stocks.items():
        # Check for recent quarterly announcement (within last 10 days)
        has_new_disclosure = False
        if sym in FINANCIAL_STATEMENTS:
            for q in FINANCIAL_STATEMENTS[sym]["Quarters_2020"]:
                if q["تاريخ النشر"] <= current_date:
                    days_diff = (pd.to_datetime(current_date) - pd.to_datetime(q["تاريخ النشر"])).days
                    if days_diff <= 10:
                        has_new_disclosure = True
                        break

        p_now = price_of(current_slice, sym)
        if is_unlisted(sym, current_date):
            price_disp = "🔒 لم يُدرج بعد"
            chg_disp = "ما قبل الطرح"
        elif p_now is None:
            price_disp = "—"
            chg_disp = "لا تتوفر بيانات"
        else:
            p_old = price_of(prev_slice, sym)
            chg = ((p_now - p_old) / p_old) * 100 if p_old else 0.0
            price_disp = f"{p_now:.2f} ريال"
            icon = "🟢" if chg > 0 else ("🔴" if chg < 0 else "⚪")
            chg_disp = f"{icon} {chg:+.2f}%"

        display_name = f"🔔 {name}" if has_new_disclosure else name

        board_data.append({
            "الرمز": sym.replace(".SR", ""),
            "الشركة المدرجة": display_name,
            "سعر الإغلاق": price_disp,
            "التغير اليومي": chg_disp,
            "الأسهم المملوكة": st.session_state.portfolio[sym]
        })

    st.dataframe(pd.DataFrame(board_data), width="stretch", hide_index=True, height=330)

    st.markdown("#### 💼 المراكز الاستثمارية المفتوحة")
    my_stocks = [
        {"الشركة": TICKER_TO_NAME[sym], "الكمية": qty, "القيمة السوقية": f"{qty * (price_of(current_slice, sym) or 0.0):,.1f} ريال"}
        for sym, qty in st.session_state.portfolio.items() if qty > 0
    ]
    if my_stocks:
        st.dataframe(pd.DataFrame(my_stocks), width="stretch", hide_index=True)
    else:
        st.caption("المحفظة خالية من الأسهم حالياً (مركز كاش بالكامل بنسبة 100%).")

with col_desk:
    st.subheader("⚡ مركز الأوامر والتحليل والقوائم المالية")
    available_names = list(filtered_stocks.keys()) if filtered_stocks else list(NAME_TO_TICKER.keys())
    target_name = st.selectbox("اختر السهم للفحص والتداول:", available_names)
    target_sym = NAME_TO_TICKER[target_name]

    price_today = price_of(current_slice, target_sym)

    tab_order, tab_fin = st.tabs(["📈 التحليل الفني وتنفيذ الصفقات", "📑 القوائم المالية وإفصاحات الأرباح"])

    with tab_order:
        if is_unlisted(target_sym, current_date):
            st.warning(f"⚠️ شركة {target_name} غير متاحة للتداول حالياً.\nموعد بدء التداول الرسمي في تاسي: {LISTING_DATES[target_sym]}")
        elif price_today is None:
            st.warning(f"⚠️ لا تتوفر بيانات سعرية لسهم {target_name} في هذه الجلسة.")
        else:
            shares_held = st.session_state.portfolio[target_sym]

            sub_hist = market_prices[target_sym].iloc[:st.session_state.step + 1]
            if target_sym in LISTING_DATES:
                sub_hist = sub_hist.loc[sub_hist.index >= LISTING_DATES[target_sym]]

            fig = go.Figure()
            fig.add_trace(go.Scatter(x=sub_hist.index, y=sub_hist.values, mode="lines", name=target_name, line=dict(color="#0284c7", width=2.5)))
            fig.update_layout(title=f"المسار التاريخي للسعر: {target_name} ({target_sym.replace('.SR','')})", height=230, margin=dict(l=10, r=10, t=35, b=10))
            st.plotly_chart(fig, width="stretch")

            ord_c1, ord_c2 = st.columns(2)
            with ord_c1:
                st.markdown(f"**سعر التنفيذ الفوري:** `{price_today:.2f} ريال`")
                max_buy = int(st.session_state.cash // price_today)
                buy_qty = st.number_input(f"كمية الشراء (الحد الأقصى {max_buy})", min_value=0, max_value=max_buy, step=50)
                if st.button(f"🟢 تأكيد شراء ({target_name})", width="stretch"):
                    st.session_state.is_running = False
                    cost = buy_qty * price_today
                    if cost <= st.session_state.cash and buy_qty > 0:
                        st.session_state.cash -= cost
                        st.session_state.portfolio[target_sym] += buy_qty
                        st.session_state.trade_history.append({"التاريخ": current_date, "النوع": "شراء", "الشركة": target_name, "الكمية": buy_qty, "السعر": price_today})
                        st.session_state.flash = ("success", f"تم تنفيذ أمر شراء {buy_qty} سهم من {target_name} بنجاح.")
                        st.rerun()

            with ord_c2:
                st.markdown(f"**الكمية المتاحة لديك:** `{shares_held} سهم`")
                sell_qty = st.number_input(f"كمية البيع (الحد الأقصى {shares_held})", min_value=0, max_value=shares_held, step=50)
                if st.button(f"🔴 تأكيد بيع ({target_name})", width="stretch"):
                    st.session_state.is_running = False
                    if 0 < sell_qty <= st.session_state.portfolio[target_sym]:
                        rev = sell_qty * price_today
                        st.session_state.cash += rev
                        st.session_state.portfolio[target_sym] -= sell_qty
                        st.session_state.trade_history.append({"التاريخ": current_date, "النوع": "بيع", "الشركة": target_name, "الكمية": sell_qty, "السعر": price_today})
                        st.session_state.flash = ("warning", f"تم تنفيذ أمر بيع {sell_qty} سهم من {target_name} بنجاح.")
                        st.rerun()

    with tab_fin:
        st.markdown(f"### 📑 الملف المالي والإفصاحات: {target_name}")

        if target_sym in FINANCIAL_STATEMENTS:
            comp_fin = FINANCIAL_STATEMENTS[target_sym]
            b19 = comp_fin["FY_2019"]

            st.markdown("#### 📋 القوائم السنوية المدققة لعام 2019 (الأساس قبل الأزمة)")
            f1, f2, f3 = st.columns(3)
            f1.metric("إجمالي الإيرادات / الدخل", b19.get("إجمالي الدخل التشغيلي", "غير متوفر"))
            f2.metric("صافي الدخل السنوي", b19.get("صافي الربح السنوي", "غير متوفر"))
            f3.metric("ربحية السهم (EPS)", b19.get("ربحية السهم (EPS)", "غير متوفر"))

            f4, f5 = st.columns(2)
            f4.metric("مكرر الأرباح (P/E)", b19.get("مكرر الأرباح (P/E)", "غير متوفر"))
            f5.write(f"📌 **الملاحظة المحاسبية:** {b19.get('نبذة القوائم', '')}")

            st.markdown("---")
            st.markdown("#### 📢 إفصاحات الأرباح الربعية المعلنة لعام 2020:")

            active_q = []
            for q in comp_fin["Quarters_2020"]:
                if current_date >= q["تاريخ النشر"]:
                    active_q.append({
                        "الفترة المالية": q["الفترة"],
                        "تاريخ النشر في تداول": q["تاريخ النشر"],
                        "الدخل التشغيلي": q["الدخل التشغيلي"],
                        "صافي الربح": q["صافي الربح"],
                        "النمو السنوي (YoY)": q["التغير السنوي"],
                        "الأثر المالي المفصح عنه": q["التعليق المالي"]
                    })

            if active_q:
                st.dataframe(pd.DataFrame(active_q), width="stretch", hide_index=True)
            else:
                st.warning(f"لم تعلن الشركة عن أي نتائج مالية لعام 2020 حتى تاريخ جلسة اليوم ({current_date}). سيبدأ موسم إفصاحات الربع الأول تدريجياً في مايو 2020.")
        else:
            st.info("البيانات والقوائم المالية المفصلة لهذا السهم قيد المراجعة والتدقيق.")

if st.session_state.trade_history:
    with st.expander("📜 سجل الصفقات التاريخية المنفذة"):
        st.dataframe(pd.DataFrame(st.session_state.trade_history).iloc[::-1], width="stretch")
