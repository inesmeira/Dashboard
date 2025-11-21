import os
import re
import time
import json
from pathlib import Path
from typing import Optional, Dict, Any, List

import pandas as pd
from pandas import ExcelFile
from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

# ------------------ Config ------------------
BASE_DIR = Path(__file__).resolve().parent
EXCEL_PATH = os.getenv("EXCEL_PATH", str(BASE_DIR / "statistics.xlsx"))
CACHE_TTL_SECONDS = int(os.getenv("CACHE_TTL_SECONDS", "10"))

app = FastAPI(title="Food Backend (Sheets: Data/TO+OO, Prices)", version="0.1.3")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# estáticos em /static e index.html na raiz
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.get("/", include_in_schema=False)
def root():
    return FileResponse(BASE_DIR / "static" / "index.html")

# ------------------ Cache ------------------
_cache: Dict[str, Dict[str, Any]] = {
    "supply": {"df": None, "mtime": None, "last": 0.0, "rename_map": {}, "sheet": None},
    "prices": {"df": None, "mtime": None, "last": 0.0, "sheet": None},
}

def _file_mtime(path: str) -> float:
    p = Path(path)
    return p.stat().st_mtime if p.exists() else 0.0

def _season_to_year(s: str) -> Optional[int]:
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

# ------------------ Sheet helpers ------------------
def _norm_sheet(s: str) -> str:
    # lowercase, remove espaços e símbolos comuns
    return re.sub(r"[\s_&+/.\-]+", "", str(s).strip().lower())

def _pick_sheet(path: str, aliases: List[str]) -> str:
    """Escolhe o nome da sheet real com base numa lista de aliases."""
    xf = ExcelFile(path)
    norm_to_orig = {_norm_sheet(n): n for n in xf.sheet_names}
    # match exato por normalização
    for alias in aliases:
        a = _norm_sheet(alias)
        if a in norm_to_orig:
            return norm_to_orig[a]
    # fallback: substring
    for alias in aliases:
        a = _norm_sheet(alias)
        for k, orig in norm_to_orig.items():
            if a in k or k in a:
                return orig
    raise ValueError(f"Nenhuma sheet compatível encontrada. Sheets: {xf.sheet_names}")

# ------------------ Header mapping helpers ------------------
def _norm(s: str) -> str:
    """normalize: lower, strip, remove acentos simples, colapsar espaços"""
    if s is None:
        return ""
    t = str(s).strip().lower()
    rep = str.maketrans("áàâãéêíóôõúç", "aaaaeeiooouc")
    t = t.translate(rep)
    t = " ".join(t.split())
    return t

TARGETS = {
    "harvest_period": [
        "harvest period","harvestperiod","haverst period","periodo da colheita",
        "periodo colheita","colheita","campanha","safra","epoca"
    ],
    "country": ["country","member state","memberstate","pais","estado membro"],
    "product_type": ["product type","producttype","product","tipo produto","tipo de produto"],
    "indicator": ["indicator","indicador"],
    "tonnes": ["tonnes","tons","tonnage","tonnages","toneladas","ton","tonnage (t)"],
}

def build_rename_map(columns: List[str]) -> Dict[str, str]:
    rename_map: Dict[str, str] = {}
    norm_cols = {c: _norm(c) for c in columns}
    for target, aliases in TARGETS.items():
        aliases_norm = [_norm(a) for a in aliases]
        # match exato
        for orig, n in norm_cols.items():
            if n in aliases_norm:
                rename_map[orig] = target
                break
        else:
            # substring
            for orig, n in norm_cols.items():
                if any(a in n for a in aliases_norm):
                    rename_map[orig] = target
                    break
    return rename_map

# ------------------ Loaders ------------------
def load_supply(force: bool = False) -> pd.DataFrame:
    slot = _cache["supply"]
    if not Path(EXCEL_PATH).exists():
        raise FileNotFoundError(f"Excel not found at '{EXCEL_PATH}'")
    mtime = _file_mtime(EXCEL_PATH)
    now = time.time()
    if slot["df"] is None or slot["mtime"] != mtime or force or (now - slot["last"]) > CACHE_TTL_SECONDS:
        # <<< aceita Data, TO+OO e também Sheet1 / Export >>>
        sheet_supply = _pick_sheet(EXCEL_PATH, ["Export", "Data", "TO+OO", "TO & OO", "Supply", "Sheet1"])
        raw = pd.read_excel(EXCEL_PATH, sheet_name=sheet_supply, dtype=str)

        # renomear colunas inteligentemente
        rename_map = build_rename_map(list(raw.columns))
        df = raw.rename(columns=rename_map).copy()

        # garantir colunas chave
        for col in ["harvest_period", "country", "product_type", "indicator", "tonnes"]:
            if col not in df.columns:
                df[col] = None

        # limpeza de valores
        df["harvest_period"] = df["harvest_period"].astype(str).str.strip()
        df["country"] = df["country"].astype(str).str.strip()
        df["product_type"] = df["product_type"].astype(str).str.strip()
        df["indicator"] = df["indicator"].astype(str).str.strip()

        # vírgula decimal em toneladas
        if df["tonnes"].dtype == object:
            df["tonnes"] = (
                df["tonnes"]
                .astype(str)
                .str.replace("\u00a0", " ")         # NBSP
                .str.replace(".", "", regex=False)  # separador milhar
                .str.replace(",", ".", regex=False) # decimal
            )
        df["tonnes"] = pd.to_numeric(df["tonnes"], errors="coerce")

        # ano derivado
        df["harvest_year"] = df["harvest_period"].apply(_season_to_year)

        slot["df"] = df
        slot["mtime"] = mtime
        slot["last"] = now
        slot["rename_map"] = rename_map
        slot["sheet"] = sheet_supply
    return slot["df"]

def load_prices(force: bool = False) -> pd.DataFrame:
    slot = _cache["prices"]
    if not Path(EXCEL_PATH).exists():
        raise FileNotFoundError(f"Excel not found at '{EXCEL_PATH}'")
    mtime = _file_mtime(EXCEL_PATH)
    now = time.time()
    if slot["df"] is None or slot["mtime"] != mtime or force or (now - slot["last"]) > CACHE_TTL_SECONDS:
        # <<< também aceita Export, caso a pivot venha assim >>>
        sheet_prices = _pick_sheet(EXCEL_PATH, ["Export", "Prices", "Price", "PRICES", "Preços", "Precos", "Sheet1"])
        raw = pd.read_excel(EXCEL_PATH, sheet_name=sheet_prices, header=None)

        # localizar header "Row Labels"
        idx = None
        for i in range(min(len(raw), 200)):
            val = str(raw.iloc[i, 0]).strip().lower()
            if val == "row labels":
                idx = i
                break
        if idx is None:
            idx = 0

        header_row = raw.iloc[idx].fillna("")
        df = raw.iloc[idx + 1:].copy()
        df.columns = header_row
        if "Row Labels" not in df.columns:
            for c in df.columns:
                if str(c).strip().lower() == "row labels":
                    df = df.rename(columns={c: "Row Labels"})
                    break
        if "Row Labels" not in df.columns:
            df.insert(0, "Row Labels", None)

        year_cols = [c for c in df.columns if isinstance(c, str) and ("/" in c or str(c).strip().isdigit())]
        keep = ["Row Labels"] + year_cols
        df = df[keep]
        df = df[df["Row Labels"].notna()]

        tidy = df.melt(id_vars=["Row Labels"], var_name="year_season", value_name="price")
        tidy["row_label"] = tidy["Row Labels"].astype(str).str.strip()
        tidy.drop(columns=["Row Labels"], inplace=True)

        tidy["price"] = pd.to_numeric(tidy["price"], errors="coerce")
        tidy["year_start"] = tidy["year_season"].astype(str).apply(_season_to_year)

        slot["df"] = tidy.reset_index(drop=True)
        slot["mtime"] = mtime
        slot["last"] = now
        slot["sheet"] = sheet_prices
    return slot["df"]

# ------------------ Endpoints ------------------
@app.get("/health")
def health():
    # tenta inferir as sheets selecionadas (não falha se der erro)
    chosen = {}
    try:
        chosen["supply_sheet"] = _pick_sheet(EXCEL_PATH, ["Data", "TO+OO", "TO & OO", "Supply", "Sheet1", "Export"])
    except Exception as e:
        chosen["supply_sheet_error"] = str(e)
    try:
        chosen["prices_sheet"] = _pick_sheet(EXCEL_PATH, ["Prices", "Price", "PRICES", "Preços", "Precos", "Export", "Sheet1"])
    except Exception as e:
        chosen["prices_sheet_error"] = str(e)
    return {"status": "ok", "excel_path": EXCEL_PATH, **chosen}

@app.get("/debug/sheets")
def debug_sheets():
    if not Path(EXCEL_PATH).exists():
        raise HTTPException(404, f"Excel not found at '{EXCEL_PATH}'")
    xf = ExcelFile(EXCEL_PATH)
    return {"excel": EXCEL_PATH, "sheets": xf.sheet_names}

@app.get("/debug/columns")
def debug_columns():
    """Cabeçalhos originais e mapeamento para a sheet de Supply."""
    if not Path(EXCEL_PATH).exists():
        raise HTTPException(404, f"Excel not found at '{EXCEL_PATH}'")
    sheet_supply = _pick_sheet(EXCEL_PATH, ["Data", "TO+OO", "TO & OO", "Supply", "Sheet1", "Export"])
    raw = pd.read_excel(EXCEL_PATH, sheet_name=sheet_supply, dtype=str, nrows=1)
    rename_map = build_rename_map(list(raw.columns))
    return {
        "sheet_supply": sheet_supply,
        "original_columns": list(map(str, raw.columns)),
        "computed_rename_map": rename_map,
        "expected_targets": list(TARGETS.keys()),
    }

# -------- SUPPLY --------
@app.get("/supply/filters")
def supply_filters():
    df = load_supply()
    return {
        "harvest_periods": sorted([x for x in df["harvest_period"].dropna().unique().tolist() if str(x).strip()]),
        "countries": sorted([x for x in df["country"].dropna().unique().tolist() if str(x).strip()]),
        "product_types": sorted([x for x in df["product_type"].dropna().unique().tolist() if str(x).strip()]),
        "indicators": sorted([x for x in df["indicator"].dropna().unique().tolist() if str(x).strip()]),
        "years": sorted([int(x) for x in df["harvest_year"].dropna().unique().tolist()]),
    }

@app.get("/supply/data")
def supply_data(
    harvest_period: Optional[str] = Query(None),
    country: Optional[str] = Query(None),
    product_type: Optional[str] = Query(None),
    indicator: Optional[str] = Query(None),
    year: Optional[int] = Query(None),
    group: Optional[str] = Query("year", description="none|harvest_period|country|product_type|indicator|year"),
):
    df = load_supply().copy()
    if harvest_period:
        df = df[df["harvest_period"].str.lower() == str(harvest_period).lower()]
    if country:
        df = df[df["country"].str.lower() == str(country).lower()]
    if product_type:
        df = df[df["product_type"].str.lower() == str(product_type).lower()]
    if indicator:
        df = df[df["indicator"].str.lower() == str(indicator).lower()]
    if year is not None:
        df = df[df["harvest_year"] == int(year)]

    if df.empty:
        return {"group": group, "rows": []}

    agg = {"tonnes": "sum"}

    def pack(dfx: pd.DataFrame):
        cols = [c for c in ["harvest_period","country","product_type","indicator","harvest_year","tonnes"] if c in dfx.columns]
        return json.loads(dfx[cols].to_json(orient="records"))

    if group in (None, "", "none"):
        return {"group": "none", "rows": pack(df)}

    if group in ("harvest_period", "country", "product_type", "indicator", "year"):
        key = "harvest_year" if group == "year" else group
        g = df.groupby(key, dropna=True).agg(agg).reset_index()
        if key == "harvest_year":
            g = g.rename(columns={"harvest_year": "year"})
        return {"group": group, "rows": json.loads(g.to_json(orient="records"))}

    return {"group": group, "rows": pack(df)}

# -------- PRICES --------
@app.get("/prices/filters")
def prices_filters():
    tidy = load_prices()
    return {
        "row_labels": sorted([x for x in tidy["row_label"].dropna().unique().tolist() if str(x).strip()]),
        "year_seasons": sorted([x for x in tidy["year_season"].dropna().unique().tolist() if str(x).strip()]),
        "years_start": sorted([int(x) for x in tidy["year_start"].dropna().unique().tolist()]),
    }

@app.get("/prices/data")
def prices_data(
    row_label: Optional[str] = Query(None),
    year_season: Optional[str] = Query(None),
    year_start: Optional[int] = Query(None),
    group: Optional[str] = Query("year", description="none|year|row_label"),
):
    tidy = load_prices().copy()
    if row_label:
        tidy = tidy[tidy["row_label"].str.lower() == row_label.lower()]
    if year_season:
        tidy = tidy[tidy["year_season"].astype(str) == str(year_season)]
    if year_start is not None:
        tidy = tidy[tidy["year_start"] == int(year_start)]

    if tidy.empty:
        return {"group": group, "rows": []}

    if group in (None, "", "none"):
        return {"group": "none", "rows": json.loads(tidy.to_json(orient="records"))}

    if group == "year":
        g = tidy.groupby("year_season", dropna=True)["price"].mean().reset_index()
        g = g.rename(columns={"year_season": "year", "price": "avg_price"})
        return {"group": "year", "rows": json.loads(g.to_json(orient="records"))}

    if group == "row_label":
        g = tidy.groupby("row_label", dropna=True)["price"].mean().reset_index()
        g = g.rename(columns={"price": "avg_price"})
        return {"group": "row_label", "rows": json.loads(g.to_json(orient="records"))}

    return {"group": group, "rows": json.loads(tidy.to_json(orient="records"))}
