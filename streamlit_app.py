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

# --------- LIMPAR QUALQUER COISA ANTIGA DE NAVEGAÇÃO ---------
for k in ("nav_page", "nave_page"):
    if k in st.session_state:
        del st.session_state[k]

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

        [data-testid="stToolbar"],
        header[data-testid="stHeader"],
        section.main > div:first-child {{
          display:none !important; height:0 !important; visibility:hidden !important;
        }}

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


# ----------------- CARREGAR DADOS -----------------
if not EXCEL_PATH.exists():
    st.error(f"Ficheiro não encontrado: {EXCEL_PATH.resolve()}")
    st.stop()

with st.spinner("A carregar dados..."):
    df = load_supply(EXCEL_PATH)

# ----------------- NAVEGAÇÃO SIMPLES -----------------
PAGES = ["Home", "Overview"]  # (se quiseres depois voltamos a pôr Index Detail, Table, etc.)

if "current_page" not in st.session_state:
    st.session_state.current_page = "Home"


def _on_page_change():
    st.session_state.current_page = st.session_state.page_radio


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
        key="page_radio",
        index=PAGES.index(st.session_state.current_page),
        label_visibility="collapsed",
        on_change=_on_page_change,
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

default_sub = st.session_state.get(
    "selected_subsegment", "Olive Oil" if "Olive Oil" in opts_sub else "(All)"
)

# ----------------- HOME NOVA -----------------
if page == "Home":
    apply_theme("default")

    st.markdown("## 🍽️ Food Dashboard")
    st.markdown(
        "Selecione um **subsegmento** para explorar volumes, países e tendências "
        "na página de **Overview**."
    )
    st.write("")

    total_tonnes_all = float(df["tonnes"].sum(skipna=True))
    n_countries_all = df["country"].nunique()
    n_years_all = df["harvest_year"].nunique()

    k1, k2, k3 = st.columns(3)
    with k1:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Total Tonnes (todas as categorias)</div>
                <div class="metric-value">{total_tonnes_all:,.0f} t</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k2:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Países com dados</div>
                <div class="metric-value">{n_countries_all}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with k3:
        st.markdown(
            f"""
            <div class="metric-card">
                <div class="metric-label">Campanhas de colheita</div>
                <div class="metric-value">{n_years_all}</div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.write("")
    st.markdown("### Escolha um subsegmento")
    st.caption("Ao clicar, vamos para **Overview** com esse subsegmento aplicado.")
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
                    if info is not None and pd.notna(info["tonnes_total"])
                    else "Sem dados"
                )
                countries_txt = (
                    f"{int(info['n_countries'])} países"
                    if info is not None and pd.notna(info["n_countries"])
                    else "—"
                )

                clicked = st.button(name, key=f"tile_{name}", use_container_width=True)

                st.markdown(
                    f"<div style='text-align:center;font-size:0.8rem;opacity:.8;'>"
                    f"{tonnes_txt} • {countries_txt}"
                    f"</div>",
                    unsafe_allow_html=True,
                )

                if clicked:
                    # guarda o subsegmento escolhido
                    st.session_state["selected_subsegment"] = name
                    st.session_state["flt_subsegment"] = name  # para o filtro em Overview
                    # muda página lógica
                    st.session_state.current_page = "Overview"
                    st.session_state.page_radio = "Overview"
                    st.experimental_rerun()

    st.markdown("</div>", unsafe_allow_html=True)
    st.stop()

# ----------------- FILTROS TOPO (para Overview) -----------------
st.markdown('<div class="filters-card">', unsafe_allow_html=True)
st.caption("💡 In any filter, click on the box and start typing to search for values faster")

c1, = st.columns(1)
with c1:
    subsegment = st.selectbox(
        "Subsegment",
        opts_sub,
        index=opts_sub.index(default_sub) if default_sub in opts_sub else 0,
        key="flt_subsegment",
    )

st.markdown("</div>", unsafe_allow_html=True)

st.session_state["selected_subsegment"] = subsegment
apply_theme(subsegment if subsegment != "(All)" else "default")

flt = df.copy()
if subsegment != "(All)":
    flt = flt[flt["subsegment"] == subsegment]

# ----------------- OVERVIEW MUITO SIMPLES (apenas para testar navegação) -----------------
if page == "Overview":
    st.markdown("## Overview (teste)")
    st.write(f"Subsegmento atual: **{subsegment}**")
    st.dataframe(flt.head(50), use_container_width=True)
