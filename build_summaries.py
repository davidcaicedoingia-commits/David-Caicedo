"""Genera tablas agregadas compactas para el dashboard de mortalidad 2019.
Ejecutar una sola vez localmente: python build_summaries.py
No se ejecuta en Render; Render solo carga los CSV comprimidos resultantes.
"""
from __future__ import annotations
import logging, re, zipfile
from pathlib import Path
import pandas as pd

BASE = Path(__file__).resolve().parent
DATA = BASE / "data"
OUT = DATA / "summary"
YEAR = 2019
logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger("build_summaries")

def first(*names):
    for name in names:
        p = DATA / name
        if p.is_file(): return p
    raise FileNotFoundError(f"Falta archivo: {' o '.join(names)}")

def excel(path, **kwargs):
    if not zipfile.is_zipfile(path): raise ValueError(f"Archivo XLSX inválido: {path}")
    return pd.read_excel(path, engine="openpyxl", **kwargs)

def norm(s, width=None):
    s=s.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    return s.str.zfill(width) if width else s

def colmatch(df, targets):
    key=lambda x: ''.join(c.lower() for c in str(x) if c.isalnum())
    lookup={key(c):c for c in df.columns}
    return next((lookup[key(t)] for t in targets if key(t) in lookup), None)

def save(df, name):
    path=OUT / f"{name}.csv.gz"
    df.to_csv(path, index=False, compression={"method":"gzip", "compresslevel":6})
    log.info("%s: %s filas, %.1f KB", path.name, len(df), path.stat().st_size/1024)

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    dp=first("NoFetal2019.xlsx", "Anexo1.NoFetal2019_CE_15-03-23.xlsx")
    cp=first("CodigosDeMuerte.xlsx", "Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
    vp=first("Divipola.xlsx", "Divipola_CE_.xlsx")
    deaths=excel(dp, sheet_name="No_Fetales_2019", usecols=["COD_DANE","COD_DEPARTAMENTO","AÑO","MES","SEXO","GRUPO_EDAD1","MANERA_MUERTE","COD_MUERTE"])
    deaths["COD_DANE"]=norm(deaths["COD_DANE"],5)
    deaths["COD_DEPARTAMENTO"]=norm(deaths["COD_DEPARTAMENTO"],2)
    deaths["COD_MUERTE"]=norm(deaths["COD_MUERTE"]).str.upper()
    deaths["MANERA_MUERTE"]=deaths["MANERA_MUERTE"].astype("string").str.strip()
    for c in ["AÑO","MES","SEXO","GRUPO_EDAD1"]: deaths[c]=pd.to_numeric(deaths[c], errors="coerce", downcast="integer")
    deaths=deaths.loc[deaths.AÑO.eq(YEAR)].copy()
    if deaths.empty: raise ValueError(f"No hay registros de {YEAR}")
    div=excel(vp,sheet_name="Hoja1",usecols=["COD_DANE","COD_DEPARTAMENTO","DEPARTAMENTO","MUNICIPIO"])
    div["COD_DANE"]=norm(div["COD_DANE"],5)
    div["COD_DEPARTAMENTO"]=norm(div["COD_DEPARTAMENTO"],2)
    for c in ["DEPARTAMENTO","MUNICIPIO"]: div[c]=div[c].astype("string").str.strip().str.upper()
    div=div.drop_duplicates("COD_DANE")
    deaths=deaths.merge(div[["COD_DANE","COD_DEPARTAMENTO","DEPARTAMENTO","MUNICIPIO"]],on="COD_DANE",how="left",validate="many_to_one",suffixes=("_DANE","_DIV"))
    # Prefer department code from DIVIPOLA where present, then original code.
    if "COD_DEPARTAMENTO_DIV" in deaths:
        deaths["COD_DEPARTAMENTO"]=deaths["COD_DEPARTAMENTO_DIV"].fillna(deaths["COD_DEPARTAMENTO_DANE"])
        deaths.drop(columns=["COD_DEPARTAMENTO_DIV","COD_DEPARTAMENTO_DANE"],inplace=True)
    deaths["DEPARTAMENTO"]=deaths["DEPARTAMENTO"].fillna("SIN IDENTIFICAR")
    deaths["MUNICIPIO"]=deaths["MUNICIPIO"].fillna("SIN IDENTIFICAR")
    raw=excel(cp,sheet_name="Final",header=8)
    c4=colmatch(raw,["Código de la CIE-10 cuatro caracteres"]); n4=colmatch(raw,["Descripcion de códigos mortalidad a cuatro caracteres"])
    c3=colmatch(raw,["Código de la CIE-10 tres caracteres"]); n3=colmatch(raw,["Descripción de códigos mortalidad a tres caracteres"])
    if not all([c4,n4,c3,n3]): raise ValueError(f"No se detectaron columnas CIE-10: {list(raw.columns)}")
    a=raw[[c4,n4]].copy(); a.columns=["COD_MUERTE","NOMBRE_CAUSA"]
    b=raw[[c3,n3]].copy(); b.columns=["COD_MUERTE","NOMBRE_CAUSA"]
    causes=pd.concat([a,b],ignore_index=True)
    causes["COD_MUERTE"]=norm(causes["COD_MUERTE"]).str.upper()
    causes["NOMBRE_CAUSA"]=causes["NOMBRE_CAUSA"].astype("string").str.strip()
    causes=causes.dropna(subset=["COD_MUERTE","NOMBRE_CAUSA"])
    causes=causes.loc[causes.COD_MUERTE.str.fullmatch(r"[A-Z][0-9]{2}(?:[A-Z0-9])?",na=False)].drop_duplicates("COD_MUERTE")
    deaths=deaths.merge(causes,on="COD_MUERTE",how="left",validate="many_to_one")
    deaths["NOMBRE_CAUSA"]=deaths["NOMBRE_CAUSA"].fillna("Descripción no disponible en catálogo")
    deaths["SEXO_NOMBRE"]=deaths["SEXO"].map({1:"Hombres",2:"Mujeres",3:"Indeterminado"}).fillna("Sin dato")
    # Compact dimensions and counts. Each table preserves the three interactive filters.
    fkeys=["DEPARTAMENTO","MES","SEXO_NOMBRE"]
    overview=deaths.groupby(["COD_DEPARTAMENTO","DEPARTAMENTO","MES","SEXO_NOMBRE"],dropna=False,observed=True).size().rename("CASOS").reset_index()
    save(overview,"overview")
    municipal=deaths.groupby(["DEPARTAMENTO","MUNICIPIO","MES","SEXO_NOMBRE"],dropna=False,observed=True).size().rename("CASOS").reset_index()
    save(municipal,"municipios")
    homicide_mask=deaths.MANERA_MUERTE.astype("string").str.casefold().eq("homicidio") | deaths.COD_MUERTE.astype("string").str.startswith("X95",na=False)
    homicide=deaths.loc[homicide_mask].groupby(["DEPARTAMENTO","MUNICIPIO","MES","SEXO_NOMBRE"],dropna=False,observed=True).size().rename("CASOS").reset_index()
    save(homicide,"homicidios")
    causes_sum=deaths.groupby(["DEPARTAMENTO","MES","SEXO_NOMBRE","COD_MUERTE","NOMBRE_CAUSA"],dropna=False,observed=True).size().rename("CASOS").reset_index()
    save(causes_sum,"causas")
    ages=deaths.groupby(["DEPARTAMENTO","MES","SEXO_NOMBRE","GRUPO_EDAD1"],dropna=False,observed=True).size().rename("CASOS").reset_index()
    save(ages,"edades")
    # Coordinates are optional; use the same DIVIPOLA Hoja3 source, aggregated to department centroids.
    coords=pd.DataFrame(columns=["COD_DEPARTAMENTO","LONGITUD","LATITUD"])
    try:
        geo=excel(vp,sheet_name="Hoja3",header=1); geo.columns=[str(c).strip() for c in geo.columns]
        lon=next((c for c in geo.columns if "longitud" in c.casefold()),None)
        lat=next((c for c in geo.columns if "latitud" in c.casefold()),None)
        dc=next((c for c in geo.columns if c.casefold().replace("ó","o").strip()=="codigo"),None)
        if all([lon,lat,dc]):
            geo["COD_DEPARTAMENTO"]=norm(geo[dc],2)
            for c in [lon,lat]: geo[c]=pd.to_numeric(geo[c].astype("string").str.replace(",",".",regex=False),errors="coerce")
            coords=geo.dropna(subset=[lon,lat]).groupby("COD_DEPARTAMENTO",as_index=False).agg(LONGITUD=(lon,"mean"),LATITUD=(lat,"mean"))
    except Exception as e: log.warning("Coordenadas no disponibles: %s",e)
    save(coords,"coordenadas")
    quality={
      "registros":int(len(deaths)),
      "municipios_sin_match":int(deaths.MUNICIPIO.eq("SIN IDENTIFICAR").sum()),
      "causas_sin_descripcion":int(deaths.NOMBRE_CAUSA.eq("Descripción no disponible en catálogo").sum()),
      "meses_invalidos":int((~deaths.MES.between(1,12)).sum()),
      "grupos_edad_sin_clasificar":int((~deaths.GRUPO_EDAD1.isin(range(30))).sum()),
      "departamentos_con_coordenadas":int(coords.COD_DEPARTAMENTO.nunique()),
    }
    pd.Series(quality).to_json(OUT/"quality.json",force_ascii=False,indent=2)
    log.info("Calidad: %s",quality)
    log.info("Generación terminada: Render cargará solo tablas agregadas comprimidas.")
if __name__=="__main__": main()
