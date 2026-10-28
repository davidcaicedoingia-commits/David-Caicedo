from __future__ import annotations

import json
import logging
import os
from functools import lru_cache
from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from dash import Dash, Input, Output, dcc, html, dash_table
from flask import jsonify

BASE_DIR = Path(__file__).resolve().parent
SUMMARY_DIR = BASE_DIR / "data" / "summary"
YEAR = 2019
MONTHS = {
    1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
    7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre",
}
AGE_GROUPS = [
    ("Neonatal según guía (0–4)", range(0, 5)), ("Infantil según guía (5–6)", range(5, 7)),
    ("Primera infancia (7–8)", range(7, 9)), ("Niñez (9–10)", range(9, 11)),
    ("Adolescencia (11)", range(11, 12)), ("Juventud (12–13)", range(12, 14)),
    ("Adultez temprana (14–16)", range(14, 17)), ("Adultez intermedia (17–19)", range(17, 20)),
    ("Vejez (20–24)", range(20, 25)), ("Longevidad (25–28)", range(25, 29)),
    ("Edad desconocida (29)", range(29, 30)),
]
logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"), format="%(asctime)s %(levelname)s %(name)s: %(message)s")
log = logging.getLogger("mortalidad_dashboard")


def read_summary(name: str) -> pd.DataFrame:
    path = SUMMARY_DIR / f"{name}.csv.gz"
    if not path.is_file():
        raise FileNotFoundError(
            f"Falta {path.relative_to(BASE_DIR)}. Descomprime el proyecto completo y verifica que incluya data/summary/."
        )
    # Los CSV comprimidos son pequeños y no requieren Excel/openpyxl durante el arranque en Render.
    return pd.read_csv(path, compression="gzip", low_memory=False)


@lru_cache(maxsize=1)
def load_data():
    required = ["overview", "municipios", "homicidios", "causas", "edades", "coordenadas"]
    tables = {name: read_summary(name) for name in required}
    quality_path = SUMMARY_DIR / "quality.json"
    if not quality_path.is_file():
        raise FileNotFoundError(f"Falta {quality_path.relative_to(BASE_DIR)}")
    with quality_path.open("r", encoding="utf-8") as f:
        quality = json.load(f)

    # Tipos pequeños para las dimensiones numéricas de las tablas resumidas.
    for name in ["overview", "municipios", "homicidios", "causas", "edades"]:
        table = tables[name]
        if "MES" in table:
            table["MES"] = pd.to_numeric(table["MES"], errors="coerce").astype("Int8")
        if "CASOS" in table:
            table["CASOS"] = pd.to_numeric(table["CASOS"], errors="coerce", downcast="integer").fillna(0).astype("int32")
        # Categorías reutilizan el mismo texto y reducen mucho la RAM, en especial en CIE-10.
        for column in table.select_dtypes(include=["object", "string"]).columns:
            table[column] = table[column].astype("category")
    if "GRUPO_EDAD1" in tables["edades"]:
        tables["edades"]["GRUPO_EDAD1"] = pd.to_numeric(tables["edades"]["GRUPO_EDAD1"], errors="coerce").astype("Int8")
    for c in ["LONGITUD", "LATITUD"]:
        tables["coordenadas"][c] = pd.to_numeric(tables["coordenadas"][c], errors="coerce")
    log.info(
        "Tablas resumidas cargadas; %s registros de origen; RAM de tablas pandas aprox. %.2f MB",
        quality["registros"], sum(t.memory_usage(deep=True).sum() for t in tables.values()) / (1024 ** 2),
    )
    return tables, quality


def card(label, value, detail):
    return html.Div([html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"), html.Div(detail, className="kpi-note")], className="kpi-card")


def empty_fig(msg, height=340):
    fig = go.Figure()
    fig.add_annotation(text=msg, x=.5, y=.5, xref="paper", yref="paper", showarrow=False, font={"size": 14, "color": "#66758a"})
    fig.update_layout(template="plotly_white", height=height, margin={"l": 10, "r": 10, "t": 35, "b": 10})
    return fig


def style(fig, height=340):
    fig.update_layout(template="plotly_white", height=height, font={"family": "Arial, sans-serif", "color": "#24364b"}, paper_bgcolor="white", plot_bgcolor="white", margin={"l": 10, "r": 10, "t": 48, "b": 25})
    return fig


def filtered(table: pd.DataFrame, department, sex, month):
    """Filtra tablas ya agregadas; no procesa las 244 mil filas originales en cada interacción."""
    mask = None
    if department and "DEPARTAMENTO" in table.columns:
        mask = table["DEPARTAMENTO"].eq(department)
    if sex and "SEXO_NOMBRE" in table.columns:
        part = table["SEXO_NOMBRE"].eq(sex)
        mask = part if mask is None else mask & part
    if month is not None and "MES" in table.columns:
        part = table["MES"].eq(int(month))
        mask = part if mask is None else mask & part
    return table if mask is None else table.loc[mask]


try:
    TABLES, QUALITY = load_data()
    overview = TABLES["overview"]
    department_options = sorted(overview["DEPARTAMENTO"].dropna().astype(str).unique())
except Exception as exc:
    log.exception("Error inicializando dashboard")
    raise RuntimeError(f"No fue posible iniciar el dashboard: {exc}") from exc

app = Dash(__name__, title="Mortalidad en Colombia 2019", update_title="Actualizando análisis…")
server = app.server


@server.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "year": YEAR, "records_loaded": QUALITY["registros"], "mode": "aggregated_summaries"}), 200


@server.get("/api/summary")
def summary():
    return jsonify({"year": YEAR, **QUALITY, "tables": {k: len(v) for k, v in TABLES.items()}}), 200


app.layout = html.Div([
    html.Header([
        html.Div([html.Div("CENTRO DE ANALÍTICA · ESTADÍSTICAS VITALES", className="eyebrow"), html.H1("Mortalidad en Colombia"), html.P("Dashboard interactivo de defunciones no fetales · 2019", className="subtitle")], className="hero-copy"),
        html.Div([html.Span("DANE", className="source-pill"), html.Span("Python · Dash · Plotly", className="tech-pill")], className="hero-tags"),
    ], className="hero"),
    html.Div([
        html.Div([html.Label("Departamento"), dcc.Dropdown(id="department-filter", options=[{"label": x.title(), "value": x} for x in department_options], placeholder="Todos los departamentos", clearable=True)], className="filter"),
        html.Div([html.Label("Sexo"), dcc.Dropdown(id="sex-filter", options=[{"label": x, "value": x} for x in ["Hombres", "Mujeres", "Indeterminado", "Sin dato"]], placeholder="Todos los sexos", clearable=True)], className="filter"),
        html.Div([html.Label("Mes"), dcc.Dropdown(id="month-filter", options=[{"label": v, "value": k} for k, v in MONTHS.items()], placeholder="Todo el año", clearable=True)], className="filter"),
        html.Button("↺ Limpiar filtros", id="clear-filters", n_clicks=0, className="clear-button"),
    ], className="filters"),
    html.Div(id="kpis", className="kpi-grid"), html.Div(id="quality-note", className="quality-note"),
    html.Div([
        html.Section([html.Div([html.H2("Distribución geográfica"), html.Span("01", className="section-number")], className="section-head"), html.P("Conteo por departamento. Las burbujas usan centroides aproximados de municipios DIVIPOLA; no representan límites departamentales oficiales."), dcc.Graph(id="map-chart", config={"displayModeBar": False}, responsive=True)], className="panel"),
        html.Section([html.Div([html.H2("Evolución mensual"), html.Span("02", className="section-number")], className="section-head"), dcc.Graph(id="monthly-chart", config={"displayModeBar": False}, responsive=True)], className="panel"),
    ], className="chart-grid"),
    html.Div([
        html.Section([html.Div([html.H2("Homicidios y agresiones con arma de fuego · X95"), html.Span("03", className="section-number")], className="section-head"), html.P("Top cinco municipios por registros clasificados como homicidio o código CIE-10 X95."), dcc.Graph(id="homicide-chart", config={"displayModeBar": False}, responsive=True)], className="panel"),
        html.Section([html.Div([html.H2("Diez municipios con menor conteo"), html.Span("04", className="section-number")], className="section-head"), html.P("Conteo absoluto entre municipios con registros; no es una tasa poblacional."), dcc.Graph(id="lowest-chart", config={"displayModeBar": False}, responsive=True)], className="panel"),
    ], className="chart-grid"),
    html.Div([
        html.Section([html.Div([html.H2("Principales causas de muerte"), html.Span("05", className="section-number")], className="section-head"), dash_table.DataTable(id="causes-table", columns=[{"name": "Código CIE-10", "id": "COD_MUERTE"}, {"name": "Descripción de la causa", "id": "NOMBRE_CAUSA"}, {"name": "Casos", "id": "CASOS", "type": "numeric", "format": {"specifier": ","}}], data=[], page_size=10, sort_action="native", export_format="csv", style_table={"overflowX": "auto"}, style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "11px", "whiteSpace": "normal", "textAlign": "left"}, style_header={"backgroundColor": "#eef3f8", "fontWeight": "bold"})], className="panel"),
        html.Section([html.Div([html.H2("Defunciones por sexo y departamento"), html.Span("06", className="section-number")], className="section-head"), dcc.Graph(id="sex-chart", config={"displayModeBar": False}, responsive=True)], className="panel"),
        html.Section([html.Div([html.H2("Mortalidad por etapa del ciclo de vida"), html.Span("07", className="section-number")], className="section-head"), html.P("Agrupación operativa de GRUPO_EDAD1; verifica el diccionario DANE antes de interpretar las categorías como edades cronológicas."), dcc.Graph(id="age-chart", config={"displayModeBar": False}, responsive=True)], className="panel"),
    ], className="chart-grid single-column"),
    html.Footer([html.Div("Fuente: DANE · Estadísticas Vitales · Defunciones no fetales 2019 y DIVIPOLA."), html.Div("Herramienta académica de análisis exploratorio. Los conteos no son tasas ni estimaciones de riesgo poblacional."), html.Div([html.A("Estado del servicio", href="/healthz", target="_blank"), " · ", html.A("Resumen técnico", href="/api/summary", target="_blank")])], className="footer"),
], className="page")


@app.callback(Output("department-filter", "value"), Output("sex-filter", "value"), Output("month-filter", "value"), Input("clear-filters", "n_clicks"), prevent_initial_call=True)
def clear_filters(_):
    return None, None, None


@app.callback(
    Output("kpis", "children"), Output("quality-note", "children"), Output("map-chart", "figure"),
    Output("monthly-chart", "figure"), Output("homicide-chart", "figure"), Output("lowest-chart", "figure"),
    Output("causes-table", "data"), Output("sex-chart", "figure"), Output("age-chart", "figure"),
    Input("department-filter", "value"), Input("sex-filter", "value"), Input("month-filter", "value"),
)
def update_dashboard(department, sex, month):
    ov = filtered(TABLES["overview"], department, sex, month)
    d = ov.groupby("DEPARTAMENTO", observed=True)["CASOS"].sum().sort_values(ascending=False)
    m = ov.groupby("MES", observed=True)["CASOS"].sum().sort_values(ascending=False)
    cause_filtered = filtered(TABLES["causas"], department, sex, month)
    c = cause_filtered.groupby("NOMBRE_CAUSA", observed=True)["CASOS"].sum().sort_values(ascending=False)
    total = int(ov["CASOS"].sum())
    kpis = [
        card("Total de defunciones", f"{total:,}", "Registros de la selección"),
        card("Departamento con más casos", str(d.index[0]).title() if len(d) else "Sin datos", "Filtros activos"),
        card("Mes con más defunciones", MONTHS.get(int(m.index[0]), "Sin datos") if len(m) else "Sin datos", "Filtros activos"),
        card("Causa más frecuente", str(c.index[0]) if len(c) else "Sin datos", "Catálogo CIE-10"),
    ]
    q = (f"Control de calidad · {QUALITY['registros']:,} registros de 2019 · {QUALITY['municipios_sin_match']:,} sin correspondencia DIVIPOLA · "
         f"{QUALITY['causas_sin_descripcion']:,} sin descripción CIE-10 · {QUALITY['meses_invalidos']:,} con mes inválido · "
         f"{QUALITY['grupos_edad_sin_clasificar']:,} con grupo de edad fuera de 0–29 · {QUALITY['departamentos_con_coordenadas']} departamentos con coordenadas.")

    # Mapa: solo se procesan unas decenas de filas agregadas.
    dc = ov.groupby(["COD_DEPARTAMENTO", "DEPARTAMENTO"], observed=True, as_index=False)["CASOS"].sum()
    mp = dc.merge(TABLES["coordenadas"], on="COD_DEPARTAMENTO", how="left").dropna(subset=["LATITUD", "LONGITUD"])
    if len(mp):
        mf = px.scatter_geo(mp, lat="LATITUD", lon="LONGITUD", size="CASOS", color="CASOS", hover_name="DEPARTAMENTO", hover_data={"CASOS": ":,", "LATITUD": False, "LONGITUD": False, "COD_DEPARTAMENTO": False}, scope="south america", projection="natural earth", size_max=42, color_continuous_scale="Tealgrn", title="Defunciones registradas por departamento")
        mf.update_geos(lataxis_range=[-5, 14], lonaxis_range=[-82, -66], showcountries=True, showland=True, landcolor="#f1f5f9", showocean=True, oceancolor="#eaf3fb", showcoastlines=True, countrycolor="#9caaba", showframe=False)
        style(mf, 400)
    else:
        mf = empty_fig("No hay coordenadas geográficas disponibles para los filtros activos", 400)

    mc = ov.groupby("MES", observed=True)["CASOS"].sum()
    monthly = mc.reindex(range(1, 13), fill_value=0).rename("CASOS").reset_index() if month is None else mc.rename("CASOS").reset_index()
    monthly["MES_NOMBRE"] = monthly["MES"].astype(int).map(MONTHS)
    mfig = px.line(monthly, x="MES_NOMBRE", y="CASOS", markers=True, title="Defunciones por mes")
    mfig.update_traces(line={"width": 3, "color": "#168c87"}, marker={"size": 7})
    style(mfig)

    h = filtered(TABLES["homicidios"], department, sex, month)
    hc = h.groupby(["MUNICIPIO", "DEPARTAMENTO"], observed=True, as_index=False)["CASOS"].sum()
    hc["CIUDAD"] = hc["MUNICIPIO"].astype(str).str.title() + " · " + hc["DEPARTAMENTO"].astype(str).str.title()
    hc = hc.nlargest(5, "CASOS").sort_values("CASOS")
    if len(hc):
        hfig = px.bar(hc, x="CASOS", y="CIUDAD", orientation="h", text="CASOS", title="Top 5 municipios · homicidio o código X95", color="CASOS", color_continuous_scale="Reds")
        hfig.update_traces(textposition="outside", cliponaxis=False)
        hfig.update_layout(coloraxis_showscale=False)
        style(hfig)
    else:
        hfig = empty_fig("No hay registros con los filtros activos")

    municipalities = filtered(TABLES["municipios"], department, sex, month)
    cc = municipalities.loc[municipalities["MUNICIPIO"].ne("SIN IDENTIFICAR")].groupby(["MUNICIPIO", "DEPARTAMENTO"], observed=True, as_index=False)["CASOS"].sum()
    cc["CIUDAD"] = cc["MUNICIPIO"].astype(str).str.title() + " · " + cc["DEPARTAMENTO"].astype(str).str.title()
    low = cc.nsmallest(10, "CASOS")
    if len(low):
        lfig = px.bar(low.sort_values("CASOS"), x="CASOS", y="CIUDAD", orientation="h", text="CASOS", title="10 municipios con menor conteo", color="CASOS", color_continuous_scale="Tealgrn")
        lfig.update_traces(textposition="outside", cliponaxis=False)
        lfig.update_layout(coloraxis_showscale=False)
        style(lfig, 380)
    else:
        lfig = empty_fig("No hay municipios para comparar")

    ct = cause_filtered.groupby(["COD_MUERTE", "NOMBRE_CAUSA"], observed=True, as_index=False)["CASOS"].sum().sort_values("CASOS", ascending=False).head(10)
    ct["CASOS"] = ct["CASOS"].astype(int)

    ds = ov.groupby(["DEPARTAMENTO", "SEXO_NOMBRE"], observed=True, as_index=False)["CASOS"].sum()
    top = ds.groupby("DEPARTAMENTO", observed=True)["CASOS"].sum().nlargest(15).index.tolist()
    ds = ds.loc[ds.DEPARTAMENTO.isin(top)]
    if len(ds):
        sfig = px.bar(ds, x="DEPARTAMENTO", y="CASOS", color="SEXO_NOMBRE", barmode="stack", category_orders={"DEPARTAMENTO": top}, color_discrete_map={"Hombres": "#2878b5", "Mujeres": "#e58a72", "Indeterminado": "#8a8f98", "Sin dato": "#b9c4d0"}, title="Departamentos con más registros por sexo")
        sfig.update_layout(xaxis_tickangle=-40, margin={"l": 10, "r": 10, "t": 48, "b": 100})
        style(sfig, 430)
    else:
        sfig = empty_fig("No hay datos por sexo y departamento", 430)

    age_table = filtered(TABLES["edades"], department, sex, month)
    age_counts = age_table.groupby("GRUPO_EDAD1", observed=True)["CASOS"].sum()
    ad = pd.DataFrame([{"ETAPA": label, "CASOS": int(age_counts.reindex(list(rng), fill_value=0).sum())} for label, rng in AGE_GROUPS])
    af = px.bar(ad, x="ETAPA", y="CASOS", text="CASOS", title="Defunciones por grupo de edad")
    af.update_traces(marker_color="#168c87", texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
    af.update_layout(xaxis_tickangle=-35, margin={"l": 10, "r": 10, "t": 48, "b": 115})
    style(af, 400)
    return kpis, q, mf, mfig, hfig, lfig, ct.to_dict("records"), sfig, af


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", "8050")), debug=os.getenv("DASH_DEBUG", "false").lower() == "true")
