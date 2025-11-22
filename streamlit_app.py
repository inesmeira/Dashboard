import base64
import re
from pathlib import Path
import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go
from datetime import datetime
from zoneinfo import ZoneInfo

EXCEL_PATH = Path("statistics.xlsx")
ISMA_PATH = Path("ISMA.xlsx")
LOGO_PATH = Path("logoBA.png")

st.set_page_config(
    page_title="Dashboard Food",
    layout="wide",
    initial_sidebar_state="expanded",
)

# limpeza antiga — não faz mal existir, mas já não usamos "nave_page"/"nav_page"
if "nave_page" in st.session_state:
    del st.session_state["nave_page"]

SUBSEGMENTS = [
    "Preserves and Vegetables",
    "Sauces",
    "Sweet Spreades",
    "Olive Oil",
    "Mayonnaise",
    "Spices",
    "Yogurt and Desserts",
    "Milk and Smoothies",
    "Pate and Others",
]

THEMES = {
    "Olive Oil": {"b1": "#a7d97d", "b2": "#d9edb3", "b3": "#edf5dc"},
    "Preserves and Vegetables": {"b1": "#ff9800", "b2": "#ffe0b2", "b3": "#fff3e0"},
    "Sauces": {"b1": "#3f51b5", "b2": "#c5cae9", "b3": "#e8eaf6"},
    "Sweet Spreades": {"b1": "#e91e63", "b2": "#f8bbd0", "b3": "#fde6ef"},
    "Mayonnaise": {"b1": "#fdd835", "b2": "#fff59d", "b3": "#fffde7"},
    "Spices": {"b1": "#8d6e63", "b2": "#d7ccc8", "b3": "#efebe9"},
    "Yogurt and Desserts": {"b1": "#7e57c2", "b2": "#d1c4e9", "b3": "#f3e5f5"},
    "Milk and Smoothies": {"b1": "#26a69a", "b2": "#b2dfdb", "b3": "#e0f2f1"},
    "Pate and Others": {"b1": "#795548", "b2": "#d7ccc8", "b3": "#efebe9"},
    "default": {"b1": "#8ccf6e", "b2": "#dff0c8", "b3": "#f2f7ea"},
}


def _logo_data_uri(p: Path) -> str:
    try:
        data = p.read_bytes()
        return "data:image/png;base64," + base64.b64encode(data).decode("ascii")
    except Exception:
        return ""


def apply_theme(name: str):
    t = THEMES.get(name, THEMES["default"])
    st.markdown(
        f"""
        <style>
        :root {{
          --b1:{t["b1"]};
          --b2:{t["b2"]};
          --b3:{t["b3"]};
          --page-bg:#f6f7fb;
          --page-bg-2:#e4e7f0;
          --sidebar-bg:#ffffff;
          --sidebar-border:#d4e8cf;
          --card-border:#e0e4ec;
        }}

        .stApp {{
          background: linear-gradient(
            180deg,
            var(--page-bg) 0%,
            var(--page-bg-2) 45%,
            var(--page-bg) 100%
          ) !important;
          background-attachment: fixed;
        }}

        /* ⚠️ REMOVEMOS O BLOCO QUE ESCONDIA O HEADER E O TOOLBAR */

        .block-container {{
          padding-top: 1rem !important;
          padding-left: 2.5rem !important;
          padding-right: 2.5rem !important;
          max-width: 1500px; margin:auto;
        }}

        section[data-testid="stSidebar"] {{
          background: var(--sidebar-bg) !important;
          border-right: 1px solid var(--sidebar-border);
        }}

        .sb-brand {{ display:flex; align-items:center; gap:.6rem; padding:.9rem .8rem .3rem .8rem; }}
        .sb-title {{ font-weight:700; color:#244c1a; font-size:1.05rem; }}

        .card {{
          background:#ffffff;
          border:1px solid var(--card-border);
          border-radius:16px;
          padding:16px;
          margin-bottom:16px;
          box-shadow:0 6px 16px rgba(0,0,0,.04);
        }}

        .filters-card {{
          background:#ffffff;
          border:1px solid var(--card-border);
          border-radius:14px;
          padding:10px 14px;
          margin:10px 0 18px 0;
          box-shadow:0 4px 10px rgba(0,0,0,.03);
        }}

        .metric-card {{
          background: linear-gradient(135deg, var(--b1), var(--b2));
          padding:16px 20px;
          border-radius:16px;
          box-shadow:0 6px 16px rgba(0,0,0,.06);
        }}
        .metric-label {{ font-size:.9rem; opacity:.85; color:#223; margin-bottom:4px; }}
        .metric-value {{ font-size:1.7rem; font-weight:800; color:#223; }}
        .metric-delta {{ font-size:.85rem; margin-top:4px; font-weight:600; }}
        .metric-delta.positive {{ color:#2e7d32; }}
        .metric-delta.negative {{ color:#c62828; }}

        thead th {{ background: var(--b1) !important; color:#fff !important; }}

        .tiles .stButton > button {{
          width: 100%;
          background:#ffffff;
          border:1px solid var(--card-border);
          border-radius:22px;
          padding:26px 28px;
          height: 120px;
          box-shadow:0 8px 20px rgba(0,0,0,.06);
          cursor:pointer;
          transition: all .15s ease-in-out;
          font-weight:700;
          font-size:1.25rem;
          color:#223;
        }}
        .tiles .stButton > button:hover {{
          transform: translateY(-4px);
          box-shadow:0 12px 24px rgba(0,0,0,0.12);
          background: var(--b3);
        }}

        div[data-testid="stSelectbox"] > div:nth-child(2) {{
          border: 1px solid #c3cadb;
          border-radius: 10px;
          background: #ffffff;
          padding: 2px 6px;
          box-shadow: 0 2px 4px rgba(0,0,0,0.04);
        }}
        div[data-testid="stSelectbox"] > div:nth-child(2):hover {{
          box-shadow: 0 3px 8px rgba(0,0,0,0.06);
          border-color: #9aa6c4;
        }}

        div[data-testid="stSelectbox"] label {{
          font-weight: 600;
          font-size: 0.86rem;
          color: #24324a;
        }}

        button[kind="secondary"] {{
          padding: 0.15rem 0.4rem !important;
          font-size: 0.8rem !important;
        }}

        div[data-testid="column"] {{
          padding-left: 0.8rem !important;
          padding-right: 0.8rem !important;
        }}

        .footer-info {{
          position: fixed;
          bottom: 10px;
          left: 10px;
          background: rgba(255, 255, 255, 0.96);
          padding: 8px 14px;
          border-radius: 8px;
          font-size: 0.75rem;
          color: #666;
          box-shadow: 0 2px 8px rgba(0,0,0,0.08);
          z-index: 999;
          border: 1px solid var(--card-border);
        }}
        .footer-info div {{ margin: 2px 0; }}

        section[data-testid="stSidebar"] div[role="radiogroup"] label {{
          font-size: 1.10rem;
          padding: 10px 12px;
          border-radius: 10px;
          margin-bottom: 6px;
          display: flex;
          align-items: center;
          gap: 8px;
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label:hover {{
          background: rgba(0,0,0,.04);
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] input[type="radio"] {{
          transform: scale(1.2);
        }}
        section[data-testid="stSidebar"] div[role="radiogroup"] label:has(input:checked){{
          background: rgba(138, 180, 248, 0.18);
          font-weight: 700;
          border: 1px solid var(--card-border);
        }}

        .sb-lastupdate {{
          font-size: .85rem;
          color: #244c1a;
          background: #fff;
          border: 1px solid var(--card-border);
          padding: 8px 10px;
          border-radius: 8px;
          margin: 8px 10px 12px 8px;
          display: inline-block;
        }}      
        </style>
        """,
        unsafe_allow_html=True,
    )


def _norm_sheet(s: str) -> str:
    return re.sub(r"[\s_&+/.\-]+", "", str(s).strip().lower())


def pick_sheet(path: Path, aliases: list[str]) -> str:
    xf = pd.ExcelFile(path)
    norm_to_orig = {_norm_sheet(n): n for n in xf.sheet_names}
    for a in aliases:
        a = _norm_sheet(a)
        if a in norm_to_orig:
            return norm_to_orig[a]
    for a in aliases:
        a = _norm_sheet(a)
        for k, orig in norm_to_orig.items():
            if a in k or k in a:
                return orig
    raise ValueError(f"No sheet available. Sheets: {xf.sheet_names}")


def season_to_year(s):
    if not isinstance(s, str):
        return None
    s = s.strip()
    if "/" in s:
        try:
            return int(s.split("/")[0])
        except Exception:
            return None
    try:
        return int(s)
    except Exception:
        return None


def build_rename_map(columns: list[str]) -> dict[str, str]:
    def norm(x: str) -> str:
        if x is None:
            return ""
        t = str(x).strip().lower()
        t = t.translate(str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc"))
        return " ".join(t.split())

    TARGETS = {
        "harvest_period": [
            "harvest period",
            "harvestperiod",
            "haverst period",
            "periodo da colheita",
            "campanha",
            "safra",
            "epoca",
        ],
        "country": ["country", "member state", "memberstate", "pais", "estado membro"],
        "product_type": [
            "product type",
            "producttype",
            "product",
            "tipo produto",
            "tipo de produto",
        ],
        "indicator": ["indicator", "indicador"],
        "tonnes": [
            "tonnes",
            "tons",
            "tonnage",
            "tonnages",
            "toneladas",
            "ton",
            "tonnage (t)",
        ],
    }
    norm_cols = {c: norm(c) for c in columns}
    rename_map = {}
    for target, aliases in TARGETS.items():
        aliases_norm = [norm(a) for a in aliases]
        for orig, n in norm_cols.items():
            if n in aliases_norm:
                rename_map[orig] = target
                break
        else:
            for orig, n in norm_cols.items():
                if any(a in n for a in aliases_norm):
                    rename_map[orig] = target
                    break
    return rename_map


@st.cache_data(show_spinner=False)
def load_supply(path: Path) -> pd.DataFrame:
    sheet = pick_sheet(path, ["Export", "Exports", "db", "Price", "Prices"])
    raw = pd.read_excel(path, sheet_name=sheet, dtype=str)
    df = raw.rename(columns=build_rename_map(list(raw.columns))).copy()

    for col in ["harvest_period", "country", "product_type", "indicator", "tonnes"]:
        if col not in df.columns:
            df[col] = None

    for c in ["harvest_period", "country", "product_type", "indicator"]:
        df[c] = df[c].astype(str).str.strip()

    df["tonnes"] = (
        df["tonnes"]
        .astype(str)
        .str.replace("\u00a0", " ", regex=False)
        .str.replace(" ", "", regex=False)
        .str.replace(",", ".", regex=False)
    )
    df["tonnes"] = pd.to_numeric(df["tonnes"], errors="coerce")

    df["harvest_year"] = df["harvest_period"].apply(season_to_year)

    map_seg = {"OO": "Olive Oil", "TO": "Olive Oil"}
    df["subsegment"] = df["product_type"].map(map_seg).fillna(df["product_type"])
    return df


@st.cache_data(show_spinner=False)
def load_isma(path: Path) -> pd.DataFrame:
    sheet = pick_sheet(path, ["isma_final", "isma", "sheet1"])
    df = pd.read_excel(path, sheet_name=sheet)
    df.columns = df.columns.astype(str).str.strip()

    if "SalesBA" not in df.columns:
        for c in df.columns:
            if c.startswith("Unnamed") and df[c].notna().sum() > 0:
                df = df.rename(columns={c: "SalesBA"})
                break

    if "Country" in df.columns:
        df["Country"] = (
            df["Country"]
            .astype(str)
            .str.strip()
            .str.replace("\u00a0", " ", regex=False)
            .str.replace(r"\s+", " ", regex=True)
        )
        df["Country"] = df["Country"].replace({"nan": None, "None": None})
        df = df[df["Country"].notna()]

    if "Harvest Period" in df.columns:
        df["Harvest Period"] = df["Harvest Period"].astype(str).str.strip()

    num_cols = [
        "Offer_PCA",
        "Market_PCA",
        "Climate_PCA",
        "Economic_PCA",
        "ISMA_PCA",
        "ISMA_FINAL",
        "Explication",
        "SalesBA",
    ]

    for c in num_cols:
        if c in df.columns:
            if c == "SalesBA":
                df[c] = (
                    df[c]
                    .astype(str)
                    .str.replace("\u00a0", " ", regex=False)
                    .str.strip()
                    .str.replace(".", "", regex=False)
                    .str.replace(",", ".", regex=False)
                    .replace({"": None})
                )
                df[c] = pd.to_numeric(df[c], errors="coerce")
            else:
                df[c] = (
                    df[c]
                    .astype(str)
                    .str.replace(",", ".", regex=False)
                    .str.replace(" ", "", regex=False)
                    .replace({"": None})
                )
                df[c] = pd.to_numeric(df[c], errors="coerce")

    return df


def calculate_growth(flt: pd.DataFrame) -> tuple[float, str]:
    by_year = flt.groupby("harvest_year", dropna=True)["tonnes"].sum().sort_index()
    if len(by_year) < 2:
        return 0.0, "neutral"
    latest = by_year.iloc[-1]
    previous = by_year.iloc[-2]
    if previous == 0:
        return 0.0, "neutral"
    growth = ((latest - previous) / previous) * 100
    trend = "positive" if growth > 0 else "negative" if growth < 0 else "neutral"
    return growth, trend


def create_line_chart(
    data: pd.DataFrame, x: str, y: str, title: str, color: str = None
):
    if data.empty:
        return None
    fig = go.Figure()
    fig.add_trace(
        go.Scatter(
            x=data[x],
            y=data[y],
            mode="lines+markers",
            line=dict(color=color or "#8ccf6e", width=3),
            marker=dict(size=8),
            fill="tozeroy",
            fillcolor="rgba(140, 207, 110, 0.1)",
        )
    )
    fig.update_layout(
        title=title,
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
        hovermode="x unified",
        plot_bgcolor="white",
        height=400,
        margin=dict(l=0, r=0, t=40, b=0),
    )
    return fig


def create_area_chart(data: pd.DataFrame, x: str, y: str, color: str, title: str):
    if data.empty:
        return None
    fig = px.area(
        data,
        x=x,
        y=y,
        color=color,
        title=title,
        line_shape="spline",
    )
    fig.update_layout(
        height=400,
        plot_bgcolor="white",
        margin=dict(l=0, r=0, t=40, b=0),
        xaxis_title=x.replace("_", " ").title(),
        yaxis_title=y.replace("_", " ").title(),
    )
    return fig


def gauge_isma(value, country):
    fig = go.Figure(
        go.Indicator(
            mode="gauge+number",
            value=float(value) if value is not None else 0.0,
            title={"text": f"ISMA Final - {country}", "font": {"size": 18}},
            number={"valueformat": ".2f"},
            gauge={
                "axis": {"range": [0, 1], "tickwidth": 1},
                "bar": {"color": "darkblue"},
                "steps": [
                    {"range": [0.00, 0.20], "color": "#d73027"},
                    {"range": [0.20, 0.35], "color": "#fc8d59"},
                    {"range": [0.35, 0.50], "color": "#fee090"},
                    {"range": [0.50, 0.65], "color": "#e0f3f8"},
                    {"range": [0.65, 1.00], "color": "#91bfdb"},
                ],
                "threshold": {
                    "line": {"color": "black", "width": 4},
                    "value": float(value) if value is not None else 0.0,
                },
            },
        )
    )
    fig.update_layout(margin=dict(l=10, r=10, t=50, b=10), height=260)
    return fig


AGG_REGEX = re.compile(
    r"^(eu(\s*[-]?\s*\d+)?|europe|world|total|others?|rest.*|asia|africa|"
    r"americas?|north america|south america|middle\s*east|oecd|g20)$",
    re.I,
)


def drop_aggregate_countries(df: pd.DataFrame, col: str = "country") -> pd.DataFrame:
    s = df[col].astype(str).str.strip().str.lower()
    return df[~s.str.match(AGG_REGEX, na=False)]


def style_share_column(s: pd.Series):
    if s.empty:
        return []

    q1 = s.quantile(0.33)
    q2 = s.quantile(0.66)

    styles = []
    for v in s:
        if pd.isna(v):
            styles.append("")
        elif v >= q2:
            styles.append("background-color: #1b5e20; color: white;")
        elif v >= q1:
            styles.append("background-color: #66bb6a; color: white;")
        else:
            styles.append("background-color: #c8e6c9;")
    return styles


def get_last_update_dt(path: Path):
    try:
        ts = path.stat().st_mtime
        return datetime.fromtimestamp(ts, tz=ZoneInfo("Europe/Lisbon"))
    except Exception:
        return None


def render_status_card(data_str, isma_str):
    st.markdown(
        f"""
        <div style="
            margin-top: 40px;
            padding: 12px 16px;
            background: rgba(255,255,255,0.85);
            border: 1px solid #dfe3eb;
            border-radius: 10px;
            font-size: 0.85rem;
            color: #24324a;
        ">
            🟢 <strong>Status Active</strong><br>
            • Data file updated: {data_str}<br>
            • ISMA file updated: {isma_str}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ----------------- CARREGAR DADOS -----------------
if not EXCEL_PATH.exists():
    st.error(f"Ficheiro não encontrado: {EXCEL_PATH.resolve()}")
    st.stop()

with st.spinner("A carregar dados..."):
    df = load_supply(EXCEL_PATH)
    if not ISMA_PATH.exists():
        st.error(f"Ficheiro ISMA não encontrado: {ISMA_PATH.resolve()}")
        st.stop()
    isma = load_isma(ISMA_PATH)

_last_dt_main = get_last_update_dt(EXCEL_PATH)
_last_dt_isma = get_last_update_dt(ISMA_PATH) if ISMA_PATH.exists() else None

all_dts = [d for d in [_last_dt_main, _last_dt_isma] if d is not None]
if all_dts:
    last_update_global = max(all_dts)
    last_update_str = last_update_global.strftime("%d/%m/%Y %H:%M")
else:
    last_update_global = None
    last_update_str = "—"

last_update_main_str = (
    _last_dt_main.strftime("%d/%m/%Y %H:%M") if _last_dt_main else "—"
)
last_update_isma_str = (
    _last_dt_isma.strftime("%d/%m/%Y %H:%M") if _last_dt_isma else "—"
)


# ----------------- SIDEBAR (NAVEGAÇÃO) -----------------
PAGES = ["Home", "Overview", "Index Detail", "Table Content"]

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"


def _update_page_from_radio():
    st.session_state.current_page = st.session_state.nav_page_radio


with st.sidebar:
    logo_uri = _logo_data_uri(LOGO_PATH)
    st.markdown(
        f"""
        <div class="sb-brand">
          {'<img src="'+logo_uri+'" alt="logo" style="height:34px;border-radius:8px"/>' if logo_uri else ''}
          <div class="sb-title">Dashboard Food</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.write("")
    st.markdown("#### Navigation")

    st.radio(
        "Go to",
        PAGES,
        key="nav_page_radio",
        index=PAGES.index(st.session_state.current_page),
        label_visibility="collapsed",
        on_change=_update_page_from_radio,
    )

page = st.session_state.current_page


# ----------------- OPÇÕES DINÂMICAS -----------------
existing_subs = sorted(
    {str(x).strip() for x in df["subsegment"].dropna() if str(x).strip()}
)

all_subs = []
for s in SUBSEGMENTS:
    if s not in all_subs:
        all_subs.append(s)
for s in existing_subs:
    if s not in all_subs:
        all_subs.append(s)

opts_sub = ["(All)"] + all_subs
opts_pt = ["(All)"] + sorted(
    [x for x in df["product_type"].dropna().unique() if str(x).strip()]
)
opts_ctry = ["(All)"] + sorted(
    [x for x in df["country"].dropna().unique() if str(x).strip()]
)
opts_hp = ["(All)"] + sorted(
    [x for x in df["harvest_period"].dropna().unique() if str(x).strip()]
)
opts_ind = ["(All)"] + sorted(
    [x for x in df["indicator"].dropna().unique() if str(x).strip()]
)

default_sub = st.session_state.get(
    "selected_subsegment", "Olive Oil" if "Olive Oil" in opts_sub else "(All)"
)

product_type = "(All)"
country = "(All)"
harvest = "(All)"
indicator = "(All)"
default_ind = "C" if "C" in opts_ind else "(All)"


# ----------------- HOME -----------------
if page == "Home":
    apply_theme("default")

    st.write("")
    st.markdown("### Choose a subsegment")
    st.markdown('<div class="tiles">', unsafe_allow_html=True)

    subs_info = (
        df.groupby("subsegment", dropna=True)
        .agg(
            tonnes_total=("tonnes", "sum"),
            n_countries=("country", "nunique"),
        )
        .reset_index()
    )
    info_map = {row["subsegment"]: row for _, row in subs_info.iterrows()}

    rows = [SUBSEGMENTS[i: i + 3] for i in range(0, len(SUBSEGMENTS), 3)]
    for row in rows:
        cols = st.columns(3, gap="medium")
        for i, name in enumerate(row):
            with cols[i]:
                info = info_map.get(name)
                tonnes_txt = (
                    f"{info['tonnes_total']:,.0f} t"
                )
                countries_txt = (
                    f"{int(info['n_countries'])} países"
                )

                clicked = st.button(name, key=f"tile_{name}", use_container_width=True)

                st.markdown(
                    f"<div style='text-align:center;font-size:0.8rem;opacity:.8;'>"
                    f"{tonnes_txt} • {countries_txt}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if clicked:
                    st.session_state["selected_subsegment"] = name
                    st.session_state["flt_subsegment"] = name
                    st.session_state.current_page = "Overview"
                    try:
                        st.rerun()
                    except AttributeError:
                        st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()


# ----------------- FILTROS TOPO -----------------
st.markdown('<div class="filters-card">', unsafe_allow_html=True)
st.caption(
    "💡 In any filter, click on the box and start typing to search for values faster"
)

if page == "Index Detail":
    c1, _ = st.columns([1.4, 3])
    with c1:
        subsegment = st.selectbox(
            "Subsegment",
            opts_sub,
            index=opts_sub.index(default_sub) if default_sub in opts_sub else 0,
            key="flt_subsegment",
        )
else:
    c1, c2, c3, c4, c5, c6 = st.columns([1.4, 1.1, 1.1, 1.1, 1.0, 0.6])

    with c1:
        subsegment = st.selectbox(
            "Subsegment",
            opts_sub,
            index=opts_sub.index(default_sub) if default_sub in opts_sub else 0,
            key="flt_subsegment",
        )

    with c2:
        product_type = st.selectbox(
            "Product Type",
            opts_pt,
            key="flt_product_type",
        )

    with c3:
        country = st.selectbox(
            "Country",
            opts_ctry,
            key="flt_country",
        )

    with c4:
        harvest = st.selectbox(
            "Harvest Period",
            opts_hp,
            key="flt_harvest",
        )

    with c5:
        indicator = st.selectbox(
            "Indicator",
            opts_ind,
            index=opts_ind.index(default_ind) if default_ind in opts_ind else 0,
            key="flt_indicator",
        )

    with c6:
        if st.button("Reset", key="btn_reset_filters"):
            st.session_state["flt_product_type"] = "(All)"
            st.session_state["flt_country"] = "(All)"
            st.session_state["flt_harvest"] = "(All)"
            st.session_state["flt_indicator"] = default_ind
            try:
                st.rerun()
            except AttributeError:
                st.experimental_rerun()

st.markdown("</div>", unsafe_allow_html=True)

st.session_state["selected_subsegment"] = subsegment
apply_theme(subsegment if subsegment != "(All)" else "default")

# ----------------- APLICAR FILTROS -----------------
flt = df.copy()
if subsegment != "(All)":
    flt = flt[flt["subsegment"] == subsegment]
if product_type != "(All)":
    flt = flt[flt["product_type"] == product_type]
if country != "(All)":
    flt = flt[flt["country"] == country]
if harvest != "(All)":
    flt = flt[flt["harvest_period"] == harvest]
if indicator != "(All)":
    flt = flt[flt["indicator"] == indicator]


# ----------------- OVERVIEW -----------------
if page == "Overview":
    st.markdown("### Overview Dashboard")

    if flt.empty:
        st.info("No data available for the selected subsegment / filters.")
        st.stop()

    growth, trend = calculate_growth(flt)

    k1, k2, k3 = st.columns(3)
    with k1:
        total_tonnes = float(flt["tonnes"].sum())
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Total Tonnes</div>
                <div class="metric-value">{total_tonnes:,.0f} t</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with k2:
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">Records</div>
                <div class="metric-value">{len(flt):,}</div>
            </div>""",
            unsafe_allow_html=True,
        )

    with k3:
        delta_class = "positive" if growth > 0 else "negative" if growth < 0 else ""
        arrow = "↑" if growth > 0 else "↓" if growth < 0 else "→"
        st.markdown(
            f"""<div class="metric-card">
                <div class="metric-label">YoY Growth</div>
                <div class="metric-value">{growth:+.1f}%</div>
                <div class="metric-delta {delta_class}">{arrow} vs. previous year</div>
            </div>""",
            unsafe_allow_html=True,
        )

    st.write("")

    # -------- GRÁFICO ÚNICO: TONNES x HARVEST PERIOD x INDICATOR --------
    st.markdown('<div class="card">', unsafe_allow_html=True)

    flt_chart = df.copy()
    if subsegment != "(All)":
        flt_chart = flt_chart[flt_chart["subsegment"] == subsegment]
    if product_type != "(All)":
        flt_chart = flt_chart[flt_chart["product_type"] == product_type]
    if country != "(All)":
        flt_chart = flt_chart[flt_chart["country"] == country]
    if harvest != "(All)":
        flt_chart = flt_chart[flt_chart["harvest_period"] == harvest]

    flt_chart = drop_aggregate_countries(flt_chart, "country")

    by_hp = (
        flt_chart.groupby(["harvest_period", "indicator"], dropna=True)["tonnes"]
        .sum()
        .reset_index()
    )

    if not by_hp.empty:
        by_hp["sort_year"] = by_hp["harvest_period"].apply(season_to_year)
        by_hp = by_hp.sort_values(["sort_year", "harvest_period", "indicator"])
        ordered_periods = list(dict.fromkeys(by_hp["harvest_period"]))

        fig = px.area(
            by_hp,
            x="harvest_period",
            y="tonnes",
            color="indicator",
            line_group="indicator",
            markers=True,
            title="Tonnes por Harvest period e Indicator",
        )

        fig.update_traces(
            mode="lines+markers",
            texttemplate="%{y:.0f}",
            textposition="top center",
        )

        fig.update_layout(
            xaxis_title="Harvest period",
            yaxis_title="Tonnes",
            hovermode="x unified",
            plot_bgcolor="rgba(0,0,0,0)",
            paper_bgcolor="rgba(0,0,0,0)",
            height=430,
            legend_title_text="Indicator",
        )

        fig.update_xaxes(
            categoryorder="array",
            categoryarray=ordered_periods,
        )

        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Sem dados para os filtros atuais.")

    st.markdown("</div>", unsafe_allow_html=True)

    # -------- Top 15 + Distribuição --------
    flt_country = flt.copy()
    if indicator == "(All)" and "C" in df["indicator"].unique():
        flt_country = flt_country[flt_country["indicator"] == "C"]
    flt_country = drop_aggregate_countries(flt_country, "country")

    by_country = (
        flt_country.groupby("country")["tonnes"]
        .sum()
        .reset_index()
        .sort_values("tonnes", ascending=False)
    )

    colA, colB = st.columns(2)

    with colA:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Top 15 Countries by Tonnes")

        if not by_country.empty:
            top15 = by_country.head(15).copy()
            mean_val = top15["tonnes"].mean()

            fig_bar = px.bar(
                top15,
                x="country",
                y="tonnes",
                title="Top 15 Countries by Tonnes",
                color_discrete_sequence=["#2f5e1b"],
            )

            fig_bar.add_trace(
                go.Scatter(
                    x=top15["country"],
                    y=[mean_val] * len(top15),
                    mode="lines",
                    name="Average",
                    line=dict(
                        color="rgba(11,156,49,0.2)",
                        width=3,
                    ),
                    hovertemplate="Average: %{y:,.0f} t<extra></extra>",
                )
            )

            fig_bar.update_layout(
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                xaxis_title="Country",
                yaxis_title="Tonnes",
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.02,
                    xanchor="right",
                    x=1,
                ),
            )

            st.plotly_chart(fig_bar, use_container_width=True)

        else:
            st.info("Sem dados.")
        st.markdown("</div>", unsafe_allow_html=True)

    with colB:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.markdown("#### Distribution by Country (%)")

        if not by_country.empty:
            dist = by_country.copy()
            total_tonnes_dist = dist["tonnes"].sum()
            if total_tonnes_dist > 0:
                dist["Share %"] = dist["tonnes"] / total_tonnes_dist * 100
            else:
                dist["Share %"] = 0.0

            dist = dist.rename(columns={"country": "Country", "tonnes": "Tonnes"})
            dist = dist[["Country", "Tonnes", "Share %"]]
            dist = dist.sort_values("Share %", ascending=False)

            styler = (
                dist.style.apply(style_share_column, subset=["Share %"]).format(
                    {"Tonnes": "{:,.0f}", "Share %": "{:.1f}%"}
                )
            )

            st.dataframe(
                styler,
                use_container_width=True,
                height=400,
            )

        else:
            st.info("Sem dados.")
        st.markdown("</div>", unsafe_allow_html=True)

    # -------- Mapa --------
    st.markdown("### 🌍 Global Map by Tonnes")
    st.markdown('<div class="card">', unsafe_allow_html=True)

    flt_map = flt.copy()
    if indicator == "(All)" and "C" in flt_map["indicator"].unique():
        flt_map = flt_map[flt_map["indicator"] == "C"]
    flt_map = drop_aggregate_countries(flt_map, "country")
    flt_map = flt_map[flt_map["harvest_year"].notna()]

    if flt_map.empty:
        st.info("No data available for the map with the current filters.")
        st.markdown("</div>", unsafe_allow_html=True)
    else:
        col_mode, _ = st.columns([2, 1])
        with col_mode:
            map_mode = st.radio(
                "View mode",
                ["Latest year", "Select year"],
                horizontal=True,
                key="map_mode",
            )

        years_available = sorted(int(y) for y in flt_map["harvest_year"].unique())

        if map_mode == "Latest year":
            latest_year = years_available[-1]
            data_year = (
                flt_map[flt_map["harvest_year"] == latest_year]
                .groupby("country", as_index=False)["tonnes"]
                .sum()
            )
            title_suffix = f"(Year {latest_year})"
        else:
            sel_year = st.selectbox(
                "Select year", years_available, index=len(years_available) - 1
            )
            data_year = (
                flt_map[flt_map["harvest_year"] == sel_year]
                .groupby("country", as_index=False)["tonnes"]
                .sum()
            )
            title_suffix = f"(Year {sel_year})"

        fig_map = px.choropleth(
            data_year,
            locations="country",
            locationmode="country names",
            color="tonnes",
            hover_name="country",
            color_continuous_scale=["#e0f2d6", "#7faa5c", "#2f5e1b"],
        )

        fig_map.update_layout(
            height=430,
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            title_text=f"Global Tonnes Map {title_suffix}",
            title_x=0.02,
            coloraxis_colorbar=dict(
                title="Tonnes",
                ticksuffix=" t",
            ),
            geo=dict(
                showframe=False,
                showcoastlines=True,
                coastlinecolor="rgba(0,0,0,0.25)",
                projection_type="natural earth",
                showocean=True,
                oceancolor="rgb(185, 215, 250)",
                showland=True,
                landcolor="rgb(248, 248, 248)",
                bgcolor="rgba(0,0,0,0)",
            ),
        )

        st.plotly_chart(fig_map, use_container_width=True)
        st.markdown("</div>", unsafe_allow_html=True)

    # -------- resto do Overview (tabs + heatmap) --------
    st.markdown("## Advanced Analytics")

    tab1, tab2, tab3 = st.tabs(["📈 Trends", "🗺️ Geographic", "📊 Comparisons"])

    with tab1:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Year-over-Year Comparison")
        by_year = (
            flt.groupby("harvest_year", dropna=True)["tonnes"]
            .sum()
            .reset_index()
            .sort_values("harvest_year")
        )
        if len(by_year) >= 2:
            by_year["yoy_change"] = by_year["tonnes"].pct_change() * 100

            col1, col2 = st.columns(2)
            with col1:
                fig_yoy = go.Figure()
                fig_yoy.add_trace(
                    go.Bar(
                        x=by_year["harvest_year"],
                        y=by_year["yoy_change"],
                        marker_color=[
                            "red" if x < 0 else "green" for x in by_year["yoy_change"]
                        ],
                        name="YoY Change %",
                    )
                )
                fig_yoy.update_layout(
                    title="Year-over-Year Growth Rate (%)",
                    height=400,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_yoy, use_container_width=True)

            with col2:
                st.dataframe(
                    by_year[["harvest_year", "tonnes", "yoy_change"]].rename(
                        columns={
                            "harvest_year": "Year",
                            "tonnes": "Tonnes",
                            "yoy_change": "YoY Change %",
                        }
                    ),
                    use_container_width=True,
                    height=400,
                )
        else:
            st.info("Dados insuficientes para análise YoY (mínimo 2 anos).")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab2:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Top 10 Countries Ranking")
        flt_geo = (
            flt[flt["indicator"] == "C"]
            if "C" in flt["indicator"].unique()
            else flt
        )
        flt_geo = drop_aggregate_countries(flt_geo, "country")
        by_country_geo = (
            flt_geo.groupby("country", dropna=True)["tonnes"]
            .sum()
            .reset_index()
            .sort_values("tonnes", ascending=False)
            .head(10)
        )

        if not by_country_geo.empty:
            by_country_geo["rank"] = range(1, len(by_country_geo) + 1)
            fig_rank = px.bar(
                by_country_geo,
                y="country",
                x="tonnes",
                orientation="h",
                title="Top 10 Countries by Consumption",
                color="tonnes",
                color_continuous_scale="Greens",
            )
            fig_rank.update_layout(
                height=500,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                yaxis={"categoryorder": "total ascending"},
            )
            st.plotly_chart(fig_rank, use_container_width=True)
        else:
            st.info("Sem dados geográficos.")
        st.markdown("</div>", unsafe_allow_html=True)

    with tab3:
        st.markdown('<div class="card">', unsafe_allow_html=True)
        st.subheader("Compare Multiple Years")

        years_available = sorted(
            [int(y) for y in flt["harvest_year"].dropna().unique()]
        )
        if len(years_available) >= 2:
            selected_years = st.multiselect(
                "Select years to compare",
                years_available,
                default=years_available[-2:],
            )

            if len(selected_years) >= 2:
                comparison_data = flt[flt["harvest_year"].isin(selected_years)]
                by_year_country = (
                    comparison_data.groupby(
                        ["harvest_year", "country"], dropna=True
                    )["tonnes"]
                    .sum()
                    .reset_index()
                )

                top_countries = (
                    by_year_country.groupby("country")["tonnes"].sum().nlargest(5).index
                )
                plot_data = by_year_country[
                    by_year_country["country"].isin(top_countries)
                ]

                fig_comp = px.bar(
                    plot_data,
                    x="country",
                    y="tonnes",
                    color="harvest_year",
                    barmode="group",
                    title="Top 5 Countries - Year Comparison",
                )
                fig_comp.update_layout(
                    height=400,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                )
                st.plotly_chart(fig_comp, use_container_width=True)
            else:
                st.info("Select at least two years to compare.")
        else:
            st.info("Insufficient data for comparison (minimum 2 years).")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown('<div class="card">', unsafe_allow_html=True)
    st.subheader("Country vs Year Heatmap")

    with st.expander("Heatmap filters", True):
        c1_h, c2_h, c3_h, c4_h = st.columns([1.2, 1, 1, 1.4])

        years_series = pd.to_numeric(flt["harvest_year"], errors="coerce").dropna()

        if years_series.empty:
            st.info("Sem anos disponíveis para o heatmap.")
            heat_data = pd.DataFrame()
        else:
            yr_min = int(years_series.min())
            yr_max = int(years_series.max())
            year_range = c1_h.slider(
                "Year range",
                yr_min,
                yr_max,
                (max(yr_min, yr_max - 10), yr_max),
            )
            only_c = c2_h.checkbox(
                "Only indicator C (Consumption)",
                value=("C" in flt["indicator"].unique()),
            )
            exclude_aggr = c3_h.checkbox(
                "Exclude aggregates (EU, World…)", value=True
            )

            metric_mode = c4_h.radio(
                "Metric",
                ["Tonnes", "Share of year total (%)"],
                horizontal=True,
                index=0,
            )

            flt_heat = flt.copy()
            if only_c and "C" in flt_heat["indicator"].unique():
                flt_heat = flt_heat[flt_heat["indicator"] == "C"]

            flt_heat = flt_heat[
                pd.to_numeric(flt_heat["harvest_year"], errors="coerce").between(
                    year_range[0], year_range[1]
                )
            ]

            if exclude_aggr:
                flt_heat = drop_aggregate_countries(flt_heat, "country")

            by_ct = (
                flt_heat.groupby("country", dropna=True)["tonnes"]
                .sum()
                .sort_values(ascending=False)
            )
            default_countries = by_ct.head(15).index.tolist()
            all_countries = sorted(
                [c for c in flt_heat["country"].dropna().unique() if str(c).strip()]
            )

            selected_countries = st.multiselect(
                "Countries",
                all_countries,
                default=default_countries,
                placeholder="Choose countries to show…",
            )

            heat_data = flt_heat.copy()
            if selected_countries:
                heat_data = heat_data[heat_data["country"].isin(selected_countries)]

    if "heat_data" in locals() and heat_data.empty:
        st.info("Dados insuficientes para heatmap.")
    elif "heat_data" in locals():
        by_ct_year = (
            heat_data.groupby(["country", "harvest_year"], dropna=True)["tonnes"]
            .sum()
            .reset_index()
        )

        if metric_mode == "Share of year total (%)":
            total_by_year = by_ct_year.groupby("harvest_year")["tonnes"].transform(
                "sum"
            )
            by_ct_year["value"] = (by_ct_year["tonnes"] / total_by_year) * 100
            colorbar_title = "% of year total"
            value_fmt = lambda v: f"{v:.1f}%" if pd.notna(v) else ""
        else:
            by_ct_year["value"] = by_ct_year["tonnes"]
            colorbar_title = "Tonnes"
            value_fmt = lambda v: f"{v:,.0f}" if pd.notna(v) else ""

        pivot = by_ct_year.pivot_table(
            index="country",
            columns="harvest_year",
            values="value",
            aggfunc="mean",
        )

        pivot = pivot.sort_index(axis=1)

        text_matrix = pivot.applymap(value_fmt)

        fig_heat = go.Figure(
            data=go.Heatmap(
                z=pivot.values,
                x=pivot.columns,
                y=pivot.index,
                colorscale="Greens",
                text=text_matrix.values,
                texttemplate="%{text}",
                textfont={"size": 10},
                colorbar=dict(title=colorbar_title),
                hovertemplate=(
                    "Country=%{y}<br>"
                    "Year=%{x}<br>"
                    f"{colorbar_title}=%{{z:.2f}}<extra></extra>"
                ),
            )
        )

        fig_heat.update_layout(
            title="Production intensity by country and year",
            xaxis_title="Harvest Year",
            yaxis_title="Country",
            height=500,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=0, r=0, t=40, b=0),
        )

        st.plotly_chart(fig_heat, use_container_width=True)

        st.caption(
            "Each cell shows the selected metric (Tonnes or share of year total) "
            "for a country in a given harvest year. Darker green means higher value."
        )

    st.markdown("</div>", unsafe_allow_html=True)


# ----------------- INDEX DETAIL -----------------
elif page == "Index Detail":

    index_segment = subsegment if subsegment != "(All)" else "Olive Oil"
    st.session_state["index_segment"] = index_segment

    apply_theme(index_segment if index_segment in THEMES else "default")

    st.markdown(f"## 📊 {index_segment} – Composite Index")

    if index_segment != "Olive Oil":
        st.warning(
            "⚠️ No data available for this subsegment yet.\n\n"
            "Currently, only the **Olive Oil ISMA** composite index is available."
        )
        st.stop()

    if isma.empty:
        st.warning("⚠️ No ISMA data available.")
        st.stop()

    all_countries_raw = isma["Country"].dropna().astype(str).str.strip()

    def looks_like_country(x: str) -> bool:
        x_clean = x.replace(" ", "")
        if not x_clean:
            return False
        if any(ch.isdigit() for ch in x_clean):
            return False
        if "%" in x_clean:
            return False
        if len(x_clean) <= 1:
            return False
        return True

    valid_countries = sorted({c for c in all_countries_raw if looks_like_country(c)})

    priority = ["Greece", "Italy", "Portugal", "Spain"]
    countries_isma = [c for c in priority if c in valid_countries] + [
        c for c in valid_countries if c not in priority
    ]

    if not countries_isma:
        st.info("No valid ISMA countries found.")
        st.stop()

    isma_sorted = isma[isma["Country"].isin(countries_isma)].copy()
    isma_sorted = isma_sorted.sort_values(["Country", "Harvest Period"])

    latest_rows = isma_sorted.groupby("Country", as_index=False).tail(1)
    latest_rows = latest_rows.dropna(subset=["ISMA_FINAL"])

    top_isma = latest_rows.sort_values("ISMA_FINAL", ascending=False).head(10)

    if not top_isma.empty:
        fig_rank_isma = px.bar(
            top_isma,
            x="Country",
            y="ISMA_FINAL",
            color="ISMA_FINAL",
            color_continuous_scale="Greens",
            title="Top countries by ISMA Final (latest harvest)",
        )
        fig_rank_isma.update_layout(
            height=380,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            yaxis_title="ISMA Final",
        )
        st.plotly_chart(fig_rank_isma, use_container_width=True)
    else:
        st.info("No valid ISMA values to rank countries.")

    st.write("")

    st.markdown("### Detail by country & harvest period")

    col_sel1, col_sel2 = st.columns([2, 1.5])

    with col_sel1:
        sel_country = st.selectbox(
            "Country",
            countries_isma,
            key="isma_country_select",
        )

    df_country = (
        isma[isma["Country"] == sel_country].copy().sort_values("Harvest Period")
    )

    sales_col = None
    for c in df_country.columns:
        if c.lower().replace(" ", "").replace("_", "") == "salesba":
            sales_col = c
            break

    if df_country.empty:
        st.info("No ISMA records for the selected country.")
        st.stop()

    harvest_options = df_country["Harvest Period"].tolist()

    with col_sel2:
        sel_harvest = st.selectbox(
            "Harvest period",
            harvest_options,
            index=len(harvest_options) - 1,
            key="isma_harvest_select",
        )

    df_point = df_country[df_country["Harvest Period"] == sel_harvest]
    if df_point.empty:
        st.info("No ISMA data for this harvest period.")
        st.stop()

    row = df_point.iloc[0]

    offer_val = float(row["Offer_PCA"]) if pd.notna(row["Offer_PCA"]) else 0.0
    market_val = float(row["Market_PCA"]) if pd.notna(row["Market_PCA"]) else 0.0
    climate_val = float(row["Climate_PCA"]) if pd.notna(row["Climate_PCA"]) else 0.0
    eco_val = float(row["Economic_PCA"]) if pd.notna(row["Economic_PCA"]) else 0.0
    isma_val = float(row["ISMA_FINAL"]) if pd.notna(row["ISMA_FINAL"]) else 0.0

    c1, c2, c3, c4 = st.columns(4)

    with c1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">ISMA Final</div>
                <div class="metric-value">{isma_val:.2f}</div>
                <div class="metric-delta">Country: {sel_country}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Offer sub-index</div>
                <div class="metric-value">{offer_val:.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Market sub-index</div>
                <div class="metric-value">{market_val:.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with c4:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Climate sub-index</div>
                <div class="metric-value">{climate_val:.2f}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")

    st.markdown("### ISMA overview")

    col_g1, col_g2 = st.columns([1.2, 1])

    with col_g1:
        gauge_fig = go.Figure(
            go.Indicator(
                mode="gauge+number",
                value=isma_val,
                number={"valueformat": ".2f"},
                title={"text": f"{sel_country} – {sel_harvest}"},
                gauge={
                    "axis": {"range": [0, 1]},
                    "bar": {"color": "#244c1a"},
                    "steps": [
                        {"range": [0.0, 0.25], "color": "#f44336"},
                        {"range": [0.25, 0.5], "color": "#ffb74d"},
                        {"range": [0.5, 0.75], "color": "#90caf9"},
                        {"range": [0.75, 1.0], "color": "#81c784"},
                    ],
                },
            )
        )
        gauge_fig.update_layout(
            height=320,
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(
            gauge_fig,
            use_container_width=True,
            key="isma_gauge_final",
        )
    st.caption("Caption: < 0.35 = Low | 0.35-0.65 = Medium | > 0.65 = High")

    with col_g2:
        theta_labels = ["Offer", "Market", "Climate", "Economic"]
        r_values = [offer_val, market_val, climate_val, eco_val]

        fig_radar = go.Figure()

        fig_radar.add_trace(
            go.Scatterpolar(
                r=r_values + [r_values[0]],
                theta=theta_labels + [theta_labels[0]],
                fill="toself",
                name=f"{sel_country} – {sel_harvest}",
                line=dict(color="#6ca86a"),
            )
        )

        fig_radar.update_layout(
            polar=dict(
                radialaxis=dict(
                    visible=True,
                    range=[0, 1],
                ),
            ),
            showlegend=True,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="center",
                x=0.5,
            ),
            height=320,
            margin=dict(l=0, r=0, t=40, b=0),
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )

        st.plotly_chart(
            fig_radar,
            use_container_width=True,
            key="isma_radar_subindices",
        )

    st.markdown("### ISMA evolution vs BA Sales")

    fig_line_isma = go.Figure()

    fig_line_isma.add_trace(
        go.Scatter(
            x=df_country["Harvest Period"],
            y=df_country["ISMA_FINAL"],
            mode="lines+markers",
            name="ISMA Final",
            line=dict(color="#6ca86a", width=3),
            marker=dict(size=8),
            yaxis="y1",
        )
    )

    if sales_col is not None and df_country[sales_col].notna().any():
        fig_line_isma.add_trace(
            go.Scatter(
                x=df_country["Harvest Period"],
                y=df_country[sales_col],
                mode="lines+markers",
                name="BA Sales",
                line=dict(color="#1f77b4", width=3),
                marker=dict(size=7),
                yaxis="y2",
            )
        )

    fig_line_isma.update_layout(
        title=f"ISMA & BA Sales over time – {sel_country}",
        xaxis=dict(title="Harvest Period"),
        yaxis=dict(
            title="ISMA Final",
            side="left",
            range=[0, 1],
        ),
        yaxis2=dict(
            title="BA Sales",
            overlaying="y",
            side="right",
            showgrid=False,
        ),
        height=400,
        legend=dict(orientation="h", y=1.15, x=0.5, xanchor="center"),
        plot_bgcolor="white",
    )

    st.plotly_chart(fig_line_isma, use_container_width=True, key="isma_line_country")

    st.markdown("### Detailed ISMA table")
    st.dataframe(
        df_country[
            [
                "Harvest Period",
                "Offer_PCA",
                "Market_PCA",
                "Climate_PCA",
                "Economic_PCA",
                "ISMA_PCA",
                "ISMA_FINAL",
            ]
        ],
        use_container_width=True,
        height=350,
    )

    render_status_card(last_update_main_str, last_update_isma_str)


# ----------------- Table Content -----------------
elif page == "Table Content":
    st.markdown("## 📋 Data Table")

    if flt.empty:
        st.info("No data available for the selected subsegment / filters.")
        st.stop()

    display_df = flt.copy()
    display_df = display_df.sort_values(
        by=["harvest_year", "subsegment", "country"],
        ascending=[False, True, True],
    )

    st.dataframe(
        display_df,
        use_container_width=True,
        height=600,
    )

    render_status_card(last_update_main_str, last_update_isma_str)
