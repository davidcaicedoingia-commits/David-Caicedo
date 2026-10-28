"""Validación previa de los tres Excel DANE del proyecto. Ejecutar: python validar_datos.py"""
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data"


def normalize(series, width=None):
    values = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return values.str.zfill(width) if width else values


def main():
    expected = ["NoFetal2019.xlsx", "CodigosDeMuerte.xlsx", "Divipola.xlsx"]
    missing_files = [name for name in expected if not (DATA / name).exists()]
    if missing_files:
        print("ERROR: faltan archivos:", ", ".join(missing_files))
        return 2

    deaths = pd.read_excel(DATA / expected[0], sheet_name="No_Fetales_2019", engine="openpyxl")
    divipola = pd.read_excel(DATA / expected[2], sheet_name="Hoja1", engine="openpyxl")
    codebook = pd.read_excel(DATA / expected[1], sheet_name="Final", header=8, engine="openpyxl")

    required_deaths = {"COD_DANE", "AÑO", "MES", "SEXO", "GRUPO_EDAD1", "MANERA_MUERTE", "COD_MUERTE"}
    required_divipola = {"COD_DANE", "DEPARTAMENTO", "MUNICIPIO"}
    required_codebook = {"Código de la CIE-10 cuatro caracteres", "Descripcion  de códigos mortalidad a cuatro caracteres",
                         "Código de la CIE-10 tres caracteres", "Descripción  de códigos mortalidad a tres caracteres"}
    errors = []
    if not required_deaths.issubset(deaths.columns): errors.append(f"Columnas faltantes en microdatos: {sorted(required_deaths - set(deaths.columns))}")
    if not required_divipola.issubset(divipola.columns): errors.append(f"Columnas faltantes en DIVIPOLA: {sorted(required_divipola - set(divipola.columns))}")
    if not required_codebook.issubset(codebook.columns): errors.append(f"Columnas faltantes en catálogo CIE-10: {sorted(required_codebook - set(codebook.columns))}")
    if errors:
        print("VALIDACIÓN FALLIDA")
        print("\n".join(errors))
        return 2

    deaths["COD_DANE"] = normalize(deaths["COD_DANE"], 5)
    deaths["COD_MUERTE"] = normalize(deaths["COD_MUERTE"]).str.upper()
    deaths["AÑO"] = pd.to_numeric(deaths["AÑO"], errors="coerce")
    deaths["MES"] = pd.to_numeric(deaths["MES"], errors="coerce")
    deaths = deaths.loc[deaths["AÑO"].eq(2019)].copy()
    divipola["COD_DANE"] = normalize(divipola["COD_DANE"], 5)
    geo_codes = set(divipola["COD_DANE"].dropna())
    missing_geo = int((~deaths["COD_DANE"].isin(geo_codes)).sum())

    c4 = codebook[["Código de la CIE-10 cuatro caracteres", "Descripcion  de códigos mortalidad a cuatro caracteres"]].copy()
    c4.columns = ["COD_MUERTE", "DESCRIPCION"]
    c3 = codebook[["Código de la CIE-10 tres caracteres", "Descripción  de códigos mortalidad a tres caracteres"]].copy()
    c3.columns = ["COD_MUERTE", "DESCRIPCION"]
    codes = pd.concat([c4, c3], ignore_index=True)
    codes["COD_MUERTE"] = normalize(codes["COD_MUERTE"]).str.upper()
    code_set = set(codes["COD_MUERTE"].dropna())
    missing_causes = int((~deaths["COD_MUERTE"].isin(code_set)).sum())
    invalid_months = int((~deaths["MES"].between(1, 12)).sum())
    deaths["GRUPO_EDAD1"] = pd.to_numeric(deaths["GRUPO_EDAD1"], errors="coerce")
    invalid_age_groups = int((~deaths["GRUPO_EDAD1"].isin(range(30))).sum())
    unexpected_sex_codes = sorted(set(pd.to_numeric(deaths["SEXO"], errors="coerce").dropna().astype(int).unique()) - {1, 2, 3})

    print("VALIDACIÓN DE DATOS DANE · DEFUNCIONES NO FETALES 2019")
    print("=" * 58)
    print(f"Registros de 2019: {len(deaths):,}")
    print(f"Códigos departamentales representados: {deaths['COD_DANE'].str[:2].nunique():,}")
    print(f"Códigos municipales sin correspondencia DIVIPOLA: {missing_geo:,}")
    print(f"Códigos CIE-10 sin descripción en catálogo (niveles 3 y 4 caracteres): {missing_causes:,}")
    print(f"Registros con mes fuera de 1–12: {invalid_months:,}")
    print(f"Registros con GRUPO_EDAD1 fuera de 0–29 o vacío: {invalid_age_groups:,}")
    print(f"Códigos de sexo distintos de 1, 2 o 3: {unexpected_sex_codes}")
    print("Meses observados:", ", ".join(map(str, sorted(deaths["MES"].dropna().unique().astype(int)))) )
    print("\nLa validación terminó. Los conteos anteriores describen la calidad de los archivos; no sustituyen la revisión de los gráficos.")
    if missing_geo or missing_causes or invalid_months or invalid_age_groups or unexpected_sex_codes:
        print("ADVERTENCIA: revise las incidencias antes de la entrega.")
        return 1
    print("RESULTADO: validación estructural aprobada.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
