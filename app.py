from __future__ import annotations
import logging, os, zipfile
from functools import lru_cache
from pathlib import Path
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html, dash_table
from flask import jsonify

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
YEAR = 2019
MONTHS = {1:"Enero",2:"Febrero",3:"Marzo",4:"Abril",5:"Mayo",6:"Junio",7:"Julio",8:"Agosto",9:"Septiembre",10:"Octubre",11:"Noviembre",12:"Diciembre"}
AGE_GROUPS = [("Neonatal según guía (0–4)",range(0,5)),("Infantil según guía (5–6)",range(5,7)),("Primera infancia (7–8)",range(7,9)),("Niñez (9–10)",range(9,11)),("Adolescencia (11)",range(11,12)),("Juventud (12–13)",range(12,14)),("Adultez temprana (14–16)",range(14,17)),("Adultez intermedia (17–19)",range(17,20)),("Vejez (20–24)",range(20,25)),("Longevidad (25–28)",range(25,29)),("Edad desconocida (29)",range(29,30))]
logging.basicConfig(level=os.getenv("LOG_LEVEL","INFO"),format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log=logging.getLogger("mortalidad_dashboard")

def norm(s,width=None):
    s=s.astype("string").str.strip().str.replace(r"\.0$","",regex=True)
    return s.str.zfill(width) if width else s

def need(df, cols, label):
    missing=[c for c in cols if c not in df.columns]
    if missing: raise ValueError(f"{label}: faltan columnas {missing}. Encontradas: {list(df.columns)}")

def excel(path, **kwargs):
    if not path.is_file(): raise FileNotFoundError(f"No existe el archivo: {path}")
    if path.stat().st_size==0: raise ValueError(f"El archivo está vacío: {path}")
    if not zipfile.is_zipfile(path):
        with path.open('rb') as f: head=f.read(100).lstrip()
        what="parece HTML, no Excel" if head.startswith((b'<html',b'<!DOCTYPE')) else "no es un XLSX válido"
        raise ValueError(f"ARCHIVO DANE INVÁLIDO: {path} ({what}; {path.stat().st_size:,} bytes)")
    try: return pd.read_excel(path,engine="openpyxl",**kwargs)
    except Exception as e: raise RuntimeError(f"Error leyendo {path.name}, hoja {kwargs.get('sheet_name')!r}: {type(e).__name__}: {e}") from e

def first(*names):
    for name in names:
        p=DATA_DIR/name
        if p.is_file(): return p
    raise FileNotFoundError(f"Falta archivo en data/: {' o '.join(names)}")

def colmatch(df, target):
    key=lambda x: ''.join(c.lower() for c in str(x) if c.isalnum())
    lookup={key(c):c for c in df.columns}
    return next((lookup[key(t)] for t in target if key(t) in lookup),None)

@lru_cache(maxsize=1)
def load_data():
    deaths_path=first("NoFetal2019.xlsx","Anexo1.NoFetal2019_CE_15-03-23.xlsx")
    causes_path=first("CodigosDeMuerte.xlsx","Anexo2.CodigosDeMuerte_CE_15-03-23.xlsx")
    div_path=first("Divipola.xlsx","Divipola_CE_.xlsx")
    deaths=excel(deaths_path,sheet_name="No_Fetales_2019")
    need(deaths,["COD_DANE","COD_DEPARTAMENTO","AÑO","MES","SEXO","GRUPO_EDAD1","MANERA_MUERTE","COD_MUERTE"],deaths_path.name)
    deaths["COD_DANE"]=norm(deaths["COD_DANE"],5); deaths["COD_DEPARTAMENTO"]=norm(deaths["COD_DEPARTAMENTO"],2)
    deaths["COD_MUERTE"]=norm(deaths["COD_MUERTE"]).str.upper(); deaths["MANERA_MUERTE"]=deaths["MANERA_MUERTE"].astype("string").str.strip()
    for c in ["AÑO","MES","SEXO","GRUPO_EDAD1"]: deaths[c]=pd.to_numeric(deaths[c],errors="coerce")
    deaths=deaths.loc[deaths["AÑO"].eq(YEAR)].copy()
    if deaths.empty: raise ValueError(f"No hay registros de {YEAR} en {deaths_path.name}")
    div=excel(div_path,sheet_name="Hoja1")
    need(div,["COD_DANE","COD_DEPARTAMENTO","DEPARTAMENTO","MUNICIPIO"],div_path.name)
    div["COD_DANE"]=norm(div["COD_DANE"],5); div["COD_DEPARTAMENTO"]=norm(div["COD_DEPARTAMENTO"],2)
    div["DEPARTAMENTO"]=div["DEPARTAMENTO"].astype("string").str.strip().str.upper(); div["MUNICIPIO"]=div["MUNICIPIO"].astype("string").str.strip().str.upper()
    div=div.drop_duplicates("COD_DANE")
    deaths=deaths.merge(div[["COD_DANE","DEPARTAMENTO","MUNICIPIO"]],on="COD_DANE",how="left",validate="many_to_one")
    deaths["DEPARTAMENTO"]=deaths["DEPARTAMENTO"].fillna("SIN IDENTIFICAR"); deaths["MUNICIPIO"]=deaths["MUNICIPIO"].fillna("SIN IDENTIFICAR")
    raw=excel(causes_path,sheet_name="Final",header=8)
    c4=colmatch(raw,["Código de la CIE-10 cuatro caracteres"]); n4=colmatch(raw,["Descripcion de códigos mortalidad a cuatro caracteres"])
    c3=colmatch(raw,["Código de la CIE-10 tres caracteres"]); n3=colmatch(raw,["Descripción de códigos mortalidad a tres caracteres"])
    if not all([c4,n4,c3,n3]): raise ValueError(f"No se identificaron columnas CIE-10 en {causes_path.name}. Columnas: {list(raw.columns)}")
    a=raw[[c4,n4]].copy(); a.columns=["COD_MUERTE","NOMBRE_CAUSA"]
    b=raw[[c3,n3]].copy(); b.columns=["COD_MUERTE","NOMBRE_CAUSA"]
    causes=pd.concat([a,b],ignore_index=True); causes["COD_MUERTE"]=norm(causes["COD_MUERTE"]).str.upper(); causes["NOMBRE_CAUSA"]=causes["NOMBRE_CAUSA"].astype("string").str.strip()
    causes=causes.dropna(subset=["COD_MUERTE","NOMBRE_CAUSA"]); causes=causes[causes["COD_MUERTE"].str.fullmatch(r"[A-Z][0-9]{2}(?:[A-Z0-9])?",na=False)].drop_duplicates("COD_MUERTE")
    deaths=deaths.merge(causes,on="COD_MUERTE",how="left",validate="many_to_one"); deaths["NOMBRE_CAUSA"]=deaths["NOMBRE_CAUSA"].fillna("Descripción no disponible en catálogo")
    deaths["SEXO_NOMBRE"]=deaths["SEXO"].map({1:"Hombres",2:"Mujeres",3:"Indeterminado"}).fillna("Sin dato")
    coords=pd.DataFrame(columns=["COD_DEPARTAMENTO","LONGITUD","LATITUD"])
    # Coordinates are optional; their absence should not take down all other views.
    try:
        geo=excel(div_path,sheet_name="Hoja3",header=1); geo.columns=[str(c).strip() for c in geo.columns]
        gc=next((c for c in geo.columns if "codigo" in c.casefold().replace("ó","o") and ".1" in c),None)
        lon=next((c for c in geo.columns if "longitud" in c.casefold()),None); lat=next((c for c in geo.columns if "latitud" in c.casefold()),None)
        dc=next((c for c in geo.columns if c.casefold().replace("ó","o").strip()=="codigo"),None)
        if all([gc,lon,lat,dc]):
            geo["COD_DEPARTAMENTO"]=norm(geo[dc],2)
            for c in [lon,lat]: geo[c]=pd.to_numeric(geo[c].astype("string").str.replace(",",".",regex=False),errors="coerce")
            coords=geo.dropna(subset=[lon,lat]).groupby("COD_DEPARTAMENTO",as_index=False).agg(LONGITUD=(lon,"mean"),LATITUD=(lat,"mean"))
        else: log.warning("No se detectaron columnas geográficas en Hoja3; mapa mostrará aviso.")
    except Exception: log.exception("No se pudo leer Hoja3; continúo sin mapa geográfico.")
    quality={"registros":len(deaths),"municipios_sin_match":int(deaths.MUNICIPIO.eq("SIN IDENTIFICAR").sum()),"causas_sin_descripcion":int(deaths.NOMBRE_CAUSA.eq("Descripción no disponible en catálogo").sum()),"meses_invalidos":int((~deaths.MES.between(1,12)).sum()),"grupos_edad_sin_clasificar":int((~deaths.GRUPO_EDAD1.isin(range(30))).sum()),"departamentos_con_coordenadas":int(coords.COD_DEPARTAMENTO.nunique())}
    log.info("Datos cargados: %s registros; archivos %s / %s / %s",quality['registros'],deaths_path.name,causes_path.name,div_path.name)
    return deaths,causes,coords,quality

def card(label,value,detail): return html.Div([html.Div(label,className="kpi-label"),html.Div(value,className="kpi-value"),html.Div(detail,className="kpi-note")],className="kpi-card")
def empty_fig(msg,height=340):
    f=go.Figure(); f.add_annotation(text=msg,x=.5,y=.5,xref="paper",yref="paper",showarrow=False,font={"size":14,"color":"#66758a"}); f.update_layout(template="plotly_white",height=height,margin={"l":10,"r":10,"t":35,"b":10}); return f
def style(f,height=340): f.update_layout(template="plotly_white",height=height,font={"family":"Arial, sans-serif","color":"#24364b"},paper_bgcolor="white",plot_bgcolor="white",margin={"l":10,"r":10,"t":48,"b":25}); return f

try: df,causes_catalogue,department_coords,QUALITY=load_data()
except Exception as e:
    log.exception("Error inicializando dashboard")
    raise RuntimeError(f"No fue posible iniciar el dashboard: {e}") from e
app=Dash(__name__,title="Mortalidad en Colombia 2019",update_title="Actualizando análisis…"); server=app.server
@server.get("/healthz")
def healthz(): return jsonify({"status":"ok","year":YEAR,"records_loaded":QUALITY["registros"]}),200
@server.get("/api/summary")
def summary(): return jsonify({"year":YEAR,**QUALITY}),200

app.layout=html.Div([
 html.Header([html.Div([html.Div("CENTRO DE ANALÍTICA · ESTADÍSTICAS VITALES",className="eyebrow"),html.H1("Mortalidad en Colombia"),html.P("Dashboard interactivo de defunciones no fetales · 2019",className="subtitle")],className="hero-copy"),html.Div([html.Span("DANE",className="source-pill"),html.Span("Python · Dash · Plotly",className="tech-pill")],className="hero-tags")],className="hero"),
 html.Div([html.Div([html.Label("Departamento"),dcc.Dropdown(id="department-filter",options=[{"label":str(x).title(),"value":x} for x in sorted(df.DEPARTAMENTO.dropna().unique())],placeholder="Todos los departamentos",clearable=True)],className="filter"),html.Div([html.Label("Sexo"),dcc.Dropdown(id="sex-filter",options=[{"label":x,"value":x} for x in ["Hombres","Mujeres","Indeterminado","Sin dato"]],placeholder="Todos los sexos",clearable=True)],className="filter"),html.Div([html.Label("Mes"),dcc.Dropdown(id="month-filter",options=[{"label":v,"value":k} for k,v in MONTHS.items()],placeholder="Todo el año",clearable=True)],className="filter"),html.Button("↺ Limpiar filtros",id="clear-filters",n_clicks=0,className="clear-button")],className="filters"),
 html.Div(id="kpis",className="kpi-grid"),html.Div(id="quality-note",className="quality-note"),
 html.Div([html.Section([html.Div([html.H2("Distribución geográfica"),html.Span("01",className="section-number")],className="section-head"),html.P("Conteo por departamento. Las burbujas usan centroides aproximados de municipios DIVIPOLA; no son límites departamentales oficiales."),dcc.Graph(id="map-chart")],className="panel"),html.Section([html.Div([html.H2("Evolución mensual"),html.Span("02",className="section-number")],className="section-head"),dcc.Graph(id="monthly-chart")],className="panel")],className="chart-grid"),
 html.Div([html.Section([html.Div([html.H2("Homicidios y agresiones con arma de fuego · X95"),html.Span("03",className="section-number")],className="section-head"),html.P("Top cinco municipios por registros clasificados como homicidio o código CIE-10 X95."),dcc.Graph(id="homicide-chart")],className="panel"),html.Section([html.Div([html.H2("Diez municipios con menor conteo"),html.Span("04",className="section-number")],className="section-head"),html.P("Conteo absoluto entre municipios con registros; no es una tasa poblacional."),dcc.Graph(id="lowest-chart")],className="panel")],className="chart-grid"),
 html.Div([html.Section([html.Div([html.H2("Principales causas de muerte"),html.Span("05",className="section-number")],className="section-head"),dash_table.DataTable(id="causes-table",columns=[{"name":"Código CIE-10","id":"COD_MUERTE"},{"name":"Descripción de la causa","id":"NOMBRE_CAUSA"},{"name":"Casos","id":"CASOS","type":"numeric","format":{"specifier":","}}],data=[],page_size=10,sort_action="native",export_format="csv",style_table={"overflowX":"auto"},style_cell={"fontFamily":"Arial","fontSize":"13px","padding":"11px","whiteSpace":"normal","textAlign":"left"},style_header={"backgroundColor":"#eef3f8","fontWeight":"bold"})],className="panel"),html.Section([html.Div([html.H2("Defunciones por sexo y departamento"),html.Span("06",className="section-number")],className="section-head"),dcc.Graph(id="sex-chart")],className="panel"),html.Section([html.Div([html.H2("Mortalidad por etapa del ciclo de vida"),html.Span("07",className="section-number")],className="section-head"),html.P("Agrupación operativa de GRUPO_EDAD1; verifica el diccionario DANE antes de interpretar las categorías como edades cronológicas."),dcc.Graph(id="age-chart")],className="panel")],className="chart-grid single-column"),
 html.Footer([html.Div("Fuente: DANE · Estadísticas Vitales · Defunciones no fetales 2019 y DIVIPOLA."),html.Div("Herramienta académica de análisis exploratorio. Los conteos no son tasas ni estimaciones de riesgo poblacional."),html.Div([html.A("Estado del servicio",href="/healthz",target="_blank")," · ",html.A("Resumen técnico",href="/api/summary",target="_blank")])],className="footer")],className="page")

@app.callback(Output("department-filter","value"),Output("sex-filter","value"),Output("month-filter","value"),Input("clear-filters","n_clicks"),prevent_initial_call=True)
def clear_filters(_): return None,None,None
@app.callback(Output("kpis","children"),Output("quality-note","children"),Output("map-chart","figure"),Output("monthly-chart","figure"),Output("homicide-chart","figure"),Output("lowest-chart","figure"),Output("causes-table","data"),Output("sex-chart","figure"),Output("age-chart","figure"),Input("department-filter","value"),Input("sex-filter","value"),Input("month-filter","value"))
def update_dashboard(department,sex,month):
 f=df
 if department: f=f.loc[f.DEPARTAMENTO.eq(department)]
 if sex: f=f.loc[f.SEXO_NOMBRE.eq(sex)]
 if month: f=f.loc[f.MES.eq(int(month))]
 d=f.DEPARTAMENTO.value_counts(); m=f.MES.value_counts(); c=f.NOMBRE_CAUSA.value_counts()
 kpis=[card("Total de defunciones",f"{len(f):,}","Registros de la selección"),card("Departamento con más casos",str(d.index[0]).title() if len(d) else "Sin datos","Filtros activos"),card("Mes con más defunciones",MONTHS.get(int(m.index[0]),"Sin datos") if len(m) else "Sin datos","Filtros activos"),card("Causa más frecuente",str(c.index[0]) if len(c) else "Sin datos","Catálogo CIE-10")]
 q=(f"Control de calidad · {QUALITY['registros']:,} registros de 2019 · {QUALITY['municipios_sin_match']:,} sin correspondencia DIVIPOLA · {QUALITY['causas_sin_descripcion']:,} sin descripción CIE-10 · {QUALITY['meses_invalidos']:,} con mes inválido · {QUALITY['grupos_edad_sin_clasificar']:,} con grupo de edad fuera de 0–29 · {QUALITY['departamentos_con_coordenadas']} departamentos con coordenadas.")
 dc=f.groupby(["COD_DEPARTAMENTO","DEPARTAMENTO"],dropna=False).size().rename("CASOS").reset_index(); mp=dc.merge(department_coords,on="COD_DEPARTAMENTO",how="left").dropna(subset=["LATITUD","LONGITUD"])
 if len(mp):
  mf=px.scatter_geo(mp,lat="LATITUD",lon="LONGITUD",size="CASOS",color="CASOS",hover_name="DEPARTAMENTO",hover_data={"CASOS":":,","LATITUD":False,"LONGITUD":False,"COD_DEPARTAMENTO":False},scope="south america",projection="natural earth",size_max=42,color_continuous_scale="Tealgrn",title="Defunciones registradas por departamento"); mf.update_geos(lataxis_range=[-5,14],lonaxis_range=[-82,-66],showcountries=True,showland=True,landcolor="#f1f5f9",showocean=True,oceancolor="#eaf3fb",showcoastlines=True,countrycolor="#9caaba",showframe=False); style(mf,400)
 else: mf=empty_fig("No hay coordenadas geográficas disponibles para los filtros activos",400)
 mc=f.groupby("MES").size(); monthly=mc.rename("CASOS").reset_index() if month else mc.reindex(range(1,13),fill_value=0).rename("CASOS").reset_index(); monthly["MES_NOMBRE"]=monthly.MES.map(MONTHS); mfig=px.line(monthly,x="MES_NOMBRE",y="CASOS",markers=True,title="Defunciones por mes"); mfig.update_traces(line={"width":3,"color":"#168c87"},marker={"size":7}); style(mfig)
 hm=f.MANERA_MUERTE.str.casefold().eq("homicidio")|f.COD_MUERTE.str.startswith("X95",na=False); hc=f.loc[hm].groupby(["MUNICIPIO","DEPARTAMENTO"]).size().rename("CASOS").reset_index(); hc["CIUDAD"]=hc.MUNICIPIO.str.title()+" · "+hc.DEPARTAMENTO.str.title(); hc=hc.nlargest(5,"CASOS").sort_values("CASOS")
 if len(hc): hfig=px.bar(hc,x="CASOS",y="CIUDAD",orientation="h",text="CASOS",title="Top 5 municipios · homicidio o código X95",color="CASOS",color_continuous_scale="Reds"); hfig.update_traces(textposition="outside",cliponaxis=False); hfig.update_layout(coloraxis_showscale=False); style(hfig)
 else: hfig=empty_fig("No hay registros con los filtros activos")
 cc=f.loc[f.MUNICIPIO.ne("SIN IDENTIFICAR")].groupby(["MUNICIPIO","DEPARTAMENTO"]).size().rename("CASOS").reset_index(); cc["CIUDAD"]=cc.MUNICIPIO.str.title()+" · "+cc.DEPARTAMENTO.str.title(); low=cc.nsmallest(10,"CASOS")
 if len(low): lfig=px.pie(low,names="CIUDAD",values="CASOS",hole=.42,title="Menor conteo absoluto entre municipios con registros"); lfig.update_traces(textposition="inside",textinfo="percent",hovertemplate="%{label}<br>Casos: %{value:,}<br>Participación: %{percent}<extra></extra>"); style(lfig)
 else: lfig=empty_fig("No hay municipios para comparar")
 ct=f.groupby(["COD_MUERTE","NOMBRE_CAUSA"]).size().rename("CASOS").reset_index().sort_values("CASOS",ascending=False).head(10); ct["CASOS"]=ct.CASOS.astype(int)
 ds=f.groupby(["DEPARTAMENTO","SEXO_NOMBRE"]).size().rename("CASOS").reset_index(); top=f.DEPARTAMENTO.value_counts().head(15).index.tolist(); ds=ds.loc[ds.DEPARTAMENTO.isin(top)]
 if len(ds): sfig=px.bar(ds,x="DEPARTAMENTO",y="CASOS",color="SEXO_NOMBRE",barmode="stack",category_orders={"DEPARTAMENTO":top},color_discrete_map={"Hombres":"#2878b5","Mujeres":"#e58a72","Indeterminado":"#8a8f98","Sin dato":"#b9c4d0"},title="Departamentos con más registros por sexo"); sfig.update_layout(xaxis_tickangle=-40,margin={"l":10,"r":10,"t":48,"b":100}); style(sfig,430)
 else: sfig=empty_fig("No hay datos por sexo y departamento",430)
 ad=pd.DataFrame([{"ETAPA":label,"CASOS":int(f.GRUPO_EDAD1.isin(list(rng)).sum())} for label,rng in AGE_GROUPS]); af=px.bar(ad,x="ETAPA",y="CASOS",text="CASOS",title="Defunciones por grupo de edad"); af.update_traces(marker_color="#168c87",texttemplate="%{text:,}",textposition="outside",cliponaxis=False); af.update_layout(xaxis_tickangle=-35,margin={"l":10,"r":10,"t":48,"b":115}); style(af,400)
 return kpis,q,mf,mfig,hfig,lfig,ct.to_dict("records"),sfig,af

if __name__=="__main__": app.run(host="0.0.0.0",port=int(os.getenv("PORT","8050")),debug=os.getenv("DASH_DEBUG","false").lower()=="true")
