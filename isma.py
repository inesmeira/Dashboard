from pathlib import Path
import os

import numpy as np
import pandas as pd
from sklearn.decomposition import PCA

# ============================
# PATHS (ajustados à tua pasta)
# ============================

SCRIPT_DIR = Path(__file__).resolve().parent
CLIMATE_DIR = SCRIPT_DIR / "excel_paises_htx"   # pasta com Espanha_hu_tn_tx_...
ISMA_PATH   = SCRIPT_DIR / "ISMA.xlsx"          # ficheiro com a tabela que mostraste

print("SCRIPT_DIR  =", SCRIPT_DIR)
print("CLIMATE_DIR =", CLIMATE_DIR)
print("ISMA_PATH   =", ISMA_PATH)


# ============================
# HELPERS
# ============================

def season_to_year(s: str) -> int | None:
    """Converte '2018/2019' -> 2018, '2020-21' -> 2020, etc."""
    if not isinstance(s, str):
        return None
    s = s.strip()
    for sep in ["/", "-"]:
        if sep in s:
            try:
                return int(s.split(sep)[0])
            except Exception:
                return None
    try:
        return int(s)
    except Exception:
        return None


def infer_country_from_filename(path: Path) -> str:
    name = path.stem
    for sep in ["_", "-", " "]:
        parts = name.split(sep)
        if len(parts) > 1:
            return parts[0].capitalize()
    return name.capitalize()


def clean_numeric(series: pd.Series) -> pd.Series:
    """Converte strings tipo '245,30' para float 245.30."""
    s = (
        series.astype(str)
        .str.replace("\u00a0", "", regex=False)  # espaço especial
        .str.replace(" ", "", regex=False)
        .str.replace(".", "", regex=False)       # remove milhares
        .str.replace(",", ".", regex=False)      # vírgula -> ponto
    )
    return pd.to_numeric(s, errors="coerce")


def minmax_norm(col: pd.Series) -> pd.Series:
    v = col.astype(float)
    vmin = v.min(skipna=True)
    vmax = v.max(skipna=True)
    if pd.isna(vmin) or pd.isna(vmax) or vmax == vmin:
        return pd.Series(0.0, index=col.index)
    return (v - vmin) / (vmax - vmin)


def pca_subindex(df: pd.DataFrame, cols: list[str], new_col: str):
    """
    Faz PCA 1D em cols normalizadas, devolve sub-índice em [0,1]
    e pesos (loadings absolutos normalizados).
    """
    X = df[cols].to_numpy(dtype=float)
    # substituir NaN pela média da coluna
    col_means = np.nanmean(X, axis=0)
    inds = np.where(np.isnan(X))
    X[inds] = np.take(col_means, inds[1])

    pca = PCA(n_components=1)
    pc1 = pca.fit_transform(X).ravel()

    pc_min = pc1.min()
    pc_max = pc1.max()
    if pc_max == pc_min:
        sub = np.zeros_like(pc1)
    else:
        sub = (pc1 - pc_min) / (pc_max - pc_min)

    df[new_col] = sub

    loadings = np.abs(pca.components_[0])
    weights = loadings / loadings.sum()
    weight_dict = {col: float(w) for col, w in zip(cols, weights)}
    return df, weight_dict


# ============================
# 1) CLIMA: ler ficheiros hu/tn/tx e agregar por ano
# ============================

def build_climate_stats() -> pd.DataFrame:
    if not CLIMATE_DIR.exists():
        raise FileNotFoundError(f"Pasta de clima não encontrada: {CLIMATE_DIR}")

    all_rows = []

    for f in CLIMATE_DIR.glob("*.xlsx"):
        print(f"📄 A ler clima de {f.name}")
        df = pd.read_excel(f)
        df.columns = df.columns.astype(str).str.strip().str.lower()

        # detectar coluna de tempo
        time_candidates = [c for c in df.columns if c in ("time", "date", "data")]
        if not time_candidates:
            raise ValueError(f"Não encontrei coluna de tempo em {f}")
        time_col = time_candidates[0]

        for col in ("hu", "tn", "tx"):
            if col not in df.columns:
                raise ValueError(f"Ficheiro {f.name} não tem coluna '{col}'")

        df["time"] = pd.to_datetime(df[time_col], errors="coerce")
        df["Year"] = df["time"].dt.year

        agg = (
            df.groupby("Year")
            .agg(
                hu_mean=("hu", "mean"),
                tn_mean=("tn", "mean"),
                tx_mean=("tx", "mean"),
            )
            .reset_index()
        )

        country = infer_country_from_filename(f)
        agg["Country"] = country
        all_rows.append(agg)

    climate = pd.concat(all_rows, ignore_index=True)
    climate = climate[["Country", "Year", "hu_mean", "tn_mean", "tx_mean"]]
    climate["Year"] = pd.to_numeric(climate["Year"], errors="coerce").astype("Int64")
    climate = climate.sort_values(["Country", "Year"])

    print("✅ Clima agregado por Country+Year")
    return climate


# ============================
# 2) Ler dados brutos do ISMA.xlsx (tabela que enviaste)
# ============================

def load_raw_isma() -> pd.DataFrame:
    if not ISMA_PATH.exists():
        raise FileNotFoundError(f"ISMA.xlsx não encontrado: {ISMA_PATH}")

    # detectar sheet que contém Harvest Period
    xls = pd.ExcelFile(ISMA_PATH)
    chosen_sheet = None
    for sheet in xls.sheet_names:
        df = pd.read_excel(ISMA_PATH, sheet_name=sheet)
        cols = set(df.columns.astype(str))
        if {"Harvest Period", "Country", "Production", "Consumption"}.issubset(cols):
            chosen_sheet = sheet
            break

    if chosen_sheet is None:
        raise ValueError("Não encontrei nenhuma sheet com Harvest Period + Country + Production + Consumption.")

    print(f"📊 A usar sheet '{chosen_sheet}' como dados brutos.")
    df = pd.read_excel(ISMA_PATH, sheet_name=chosen_sheet)
    df.columns = df.columns.astype(str).str.strip()

    # garantir Year
    df["Year"] = df["Harvest Period"].apply(season_to_year)

    # limpar colunas numéricas
    num_cols = [
        "Consumption",
        "Production",
        "Exportation",
        "Importation",
        "Production_Olives",
        "PIB",
        "Inflation",
        "PriceAVG",
        "Precipitation (mm)",
    ]
    for c in num_cols:
        if c in df.columns:
            df[c] = clean_numeric(df[c])

    return df


# ============================
# 3) Construir ISMA_v2 com PCA (incluindo clima)
# ============================

def build_isma_v2():
    # clima
    climate = build_climate_stats()

    # dados brutos
    base = load_raw_isma()

    # juntar clima por Country+Year
    df = base.merge(
        climate,
        how="left",
        on=["Country", "Year"],
    )

    # ========= NORMALIZAÇÕES =========

    # POSITIVAS
    for col in [
        "Production",
        "Exportation",
        "Production_Olives",
        "Consumption",
        "Precipitation (mm)",
        "PIB",
        "hu_mean",
        "tn_mean",
        "tx_mean",
    ]:
        if col in df.columns:
            df[col + "_N"] = minmax_norm(df[col])

    # NEGATIVAS (invertidas)
    if "Importation" in df.columns:
        df["Importation_N"] = minmax_norm(df["Importation"])
        df["Importation_N_Inversion"] = 1 - df["Importation_N"]

    if "Inflation" in df.columns:
        df["Inflation_N"] = minmax_norm(df["Inflation"])
        df["Inflation_N_Inversion"] = 1 - df["Inflation_N"]

    # ========= SUB-ÍNDICES COM PCA =========

    weights = {}

    # Oferta: Production, Exportation, Production_Olives
    offer_cols = ["Production_N", "Exportation_N", "Production_Olives_N"]
    df, w_offer = pca_subindex(df, offer_cols, "Offer_PCA_v2")
    weights["Offer_PCA_v2"] = w_offer

    # Mercado: Consumption + Importation invertida
    market_cols = ["Consumption_N", "Importation_N_Inversion"]
    df, w_market = pca_subindex(df, market_cols, "Market_PCA_v2")
    weights["Market_PCA_v2"] = w_market

    # Económico: PIB + Inflation invertida
    econ_cols = ["PIB_N", "Inflation_N_Inversion"]
    df, w_econ = pca_subindex(df, econ_cols, "Economic_PCA_v2")
    weights["Economic_PCA_v2"] = w_econ

    # Clima (versão B): PCA(Precipitation_N, hu_N, tn_N, tx_N)
    climate_cols = [
        "Precipitation (mm)_N",
        "hu_mean_N",
        "tn_mean_N",
        "tx_mean_N",
    ]
    df, w_climate = pca_subindex(df, climate_cols, "Climate_PCA_v2")
    weights["Climate_PCA_v2"] = w_climate

    # ========= PCA GLOBAL: ISMA_v2 =========
    sub_cols = [
        "Offer_PCA_v2",
        "Market_PCA_v2",
        "Climate_PCA_v2",
        "Economic_PCA_v2",
    ]
    df, w_global = pca_subindex(df, sub_cols, "ISMA_v2")
    weights["ISMA_v2"] = w_global

    print("\nPesos dos sub-índices no ISMA_v2 (PCA global):")
    for k, v in w_global.items():
        print(f"  {k}: {v:.3f}")

    # ========= PREPARAR SHEET ISMA_v2 =========

    cols_base = [
        "Harvest Period",
        "Year",
        "Country",
        "Consumption",
        "Production",
        "Exportation",
        "Importation",
        "Production_Olives",
        "PIB",
        "Inflation",
        "PriceAVG",
        "Precipitation (mm)",
        "hu_mean",
        "tn_mean",
        "tx_mean",
    ]

    cols_sub = [
        "Offer_PCA_v2",
        "Market_PCA_v2",
        "Climate_PCA_v2",
        "Economic_PCA_v2",
        "ISMA_v2",
    ]

    df_out = df[cols_base + cols_sub].copy()

    # escrever nova sheet no ISMA.xlsx
    with pd.ExcelWriter(
        ISMA_PATH,
        engine="openpyxl",
        mode="a",
        if_sheet_exists="replace",
    ) as writer:
        df_out.to_excel(writer, sheet_name="ISMA_v2", index=False)

    print(f"\n✅ Sheet 'ISMA_v2' criada/atualizada dentro de {ISMA_PATH}")


# ============================
# MAIN
# ============================

def main():
    print("=== A construir ISMA_v2 com PCA climático (Precip + hu + tn + tx) ===")
    build_isma_v2()
    print("\n✔ Processo concluído.")


if __name__ == "__main__":
    main()
