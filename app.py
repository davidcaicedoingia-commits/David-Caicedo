from __future__ import annotations

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
DATA_DIR = BASE_DIR / "data"
YEAR = 2019
MONTHS = {1: "Enero", 2: "Febrero", 3: "Marzo", 4: "Abril", 5: "Mayo", 6: "Junio",
          7: "Julio", 8: "Agosto", 9: "Septiembre", 10: "Octubre", 11: "Noviembre", 12: "Diciembre"}
# These labels/ranges follow the assignment's mapping for GRUPO_EDAD1.
# They are operational categories from the guide and should not be treated as
# literal ages without checking the DANE codebook.
AGE_GROUPS = [
    ("Neonatal según guía (0–4)", range(0, 5)), ("Infantil según guía (5–6)", range(5, 7)),
    ("Primera infancia (7–8)", range(7, 9)), ("Niñez (9–10)", range(9, 11)),
    ("Adolescencia (11)", range(11, 12)), ("Juventud (12–13)", range(12, 14)),
    ("Adultez temprana (14–16)", range(14, 17)), ("Adultez intermedia (17–19)", range(17, 20)),
    ("Vejez (20–24)", range(20, 25)), ("Longevidad (25–28)", range(25, 29)),
    ("Edad desconocida (29)", range(29, 30)),
]

logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"),
                    format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logger = logging.getLogger("mortalidad_dashboard")


def normalize_code(series: pd.Series, width: int | None = None) -> pd.Series:
    """Normalize DANE/CIE codes without converting them to scientific notation."""
    values = series.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)
    if width:
        values = values.str.zfill(width)
    return values


def require_columns(frame: pd.DataFrame, columns: list[str], file_label: str) -> None:
    missing = [c for c in columns if c not in frame.columns]
    if missing:
        raise ValueError(f"El archivo {file_label} no contiene las columnas requeridas: {', '.join(missing)}")


@lru_cache(maxsize=1)
def load_data():
    """Load and validate local DANE source files once per worker process."""
    deaths_path = DATA_DIR / "NoFetal2019.xlsx"
    causes_path = DATA_DIR / "CodigosDeMuerte.xlsx"
    divipola_path = DATA_DIR / "Divipola.xlsx"
    for path in (deaths_path, causes_path, divipola_path):
        if not path.exists():
            raise FileNotFoundError(f"No se encontró el archivo requerido: {path.name} en {DATA_DIR}")

    deaths = pd.read_excel(deaths_path, sheet_name="No_Fetales_2019", engine="openpyxl")
    require_columns(deaths, ["COD_DANE", "AÑO", "MES", "SEXO", "GRUPO_EDAD1", "MANERA_MUERTE", "COD_MUERTE"], deaths_path.name)
    deaths["COD_DANE"] = normalize_code(deaths["COD_DANE"], 5)
    for col in ["AÑO", "MES", "SEXO", "GRUPO_EDAD1"]:
        deaths[col] = pd.to_numeric(deaths[col], errors="coerce")
    deaths["COD_DEPARTAMENTO"] = normalize_code(deaths["COD_DEPARTAMENTO"], 2)
    deaths["COD_MUERTE"] = normalize_code(deaths["COD_MUERTE"]).str.upper()
    deaths["MANERA_MUERTE"] = deaths["MANERA_MUERTE"].astype("string").str.strip()
    deaths = deaths.loc[deaths["AÑO"].eq(YEAR)].copy()
    if deaths.empty:
        raise ValueError(f"No hay registros del año {YEAR} en el archivo de mortalidad.")

    divipola = pd.read_excel(divipola_path, sheet_name="Hoja1", engine="openpyxl")
    require_columns(divipola, ["COD_DANE", "COD_DEPARTAMENTO", "DEPARTAMENTO", "MUNICIPIO"], divipola_path.name)
    divipola["COD_DANE"] = normalize_code(divipola["COD_DANE"], 5)
    divipola["COD_DEPARTAMENTO"] = normalize_code(divipola["COD_DEPARTAMENTO"], 2)
    divipola["DEPARTAMENTO"] = divipola["DEPARTAMENTO"].astype("string").str.strip().str.upper()
    divipola["MUNICIPIO"] = divipola["MUNICIPIO"].astype("string").str.strip().str.upper()
    divipola = divipola.drop_duplicates("COD_DANE")
    deaths = deaths.merge(divipola[["COD_DANE", "DEPARTAMENTO", "MUNICIPIO"]],
                          on="COD_DANE", how="left", validate="many_to_one")
    deaths["DEPARTAMENTO"] = deaths["DEPARTAMENTO"].fillna("SIN IDENTIFICAR")
    deaths["MUNICIPIO"] = deaths["MUNICIPIO"].fillna("SIN IDENTIFICAR")

    # Catalogue has introductory rows; its real column header is row 9 (Excel row 9 / pandas header=8).
    causes_raw = pd.read_excel(causes_path, sheet_name="Final", header=8, engine="openpyxl")
    code4_col = "Código de la CIE-10 cuatro caracteres"
    name4_col = "Descripcion  de códigos mortalidad a cuatro caracteres"
    code3_col = "Código de la CIE-10 tres caracteres"
    name3_col = "Descripción  de códigos mortalidad a tres caracteres"
    require_columns(causes_raw, [code4_col, name4_col, code3_col, name3_col], causes_path.name)
    # DANE microdata contains both 4-character and 3-character CIE-10 codes.
    # Build one dictionary with both levels so 3-character records are not discarded.
    causes4 = causes_raw[[code4_col, name4_col]].copy()
    causes4.columns = ["COD_MUERTE", "NOMBRE_CAUSA"]
    causes3 = causes_raw[[code3_col, name3_col]].copy()
    causes3.columns = ["COD_MUERTE", "NOMBRE_CAUSA"]
    causes = pd.concat([causes4, causes3], ignore_index=True)
    causes["COD_MUERTE"] = normalize_code(causes["COD_MUERTE"]).str.upper()
    causes["NOMBRE_CAUSA"] = causes["NOMBRE_CAUSA"].astype("string").str.strip()
    causes = causes.dropna(subset=["COD_MUERTE", "NOMBRE_CAUSA"])
    causes = causes[causes["COD_MUERTE"].str.fullmatch(r"[A-Z][0-9]{2}(?:[A-Z0-9])?", na=False)]
    causes = causes.drop_duplicates("COD_MUERTE")
    deaths = deaths.merge(causes, on="COD_MUERTE", how="left", validate="many_to_one")
    deaths["NOMBRE_CAUSA"] = deaths["NOMBRE_CAUSA"].fillna("Descripción no disponible en catálogo")

    # Sex codes in the DANE microdata: 1 male, 2 female, 3 indeterminate (other codes remain visible as unknown).
    deaths["SEXO_NOMBRE"] = deaths["SEXO"].map({1: "Hombres", 2: "Mujeres", 3: "Indeterminado"}).fillna("Sin dato")

    # DIVIPOLA coordinate worksheet: first row is a merged header; second row contains column names.
    geo_raw = pd.read_excel(divipola_path, sheet_name="Hoja3", header=1, engine="openpyxl")
    geo_raw.columns = [str(c).strip() for c in geo_raw.columns]
    geo_code_col = next((c for c in geo_raw.columns if c.startswith("Código") and ".1" in c), None)
    lon_col = next((c for c in geo_raw.columns if "Longitud" in c), None)
    lat_col = next((c for c in geo_raw.columns if "Latitud" in c), None)
    dep_code_col = next((c for c in geo_raw.columns if c.strip() == "Código"), None)
    geo_centroids = pd.DataFrame(columns=["COD_DEPARTAMENTO", "LONGITUD", "LATITUD"])
    if all([geo_code_col, lon_col, lat_col, dep_code_col]):
        geo_raw["COD_DEPARTAMENTO"] = normalize_code(geo_raw[dep_code_col], 2)
        geo_raw["COD_DANE"] = normalize_code(geo_raw[geo_code_col], 5)
        for c in (lon_col, lat_col):
            geo_raw[c] = pd.to_numeric(geo_raw[c].astype("string").str.replace(",", ".", regex=False), errors="coerce")
        geo_centroids = (geo_raw.dropna(subset=[lon_col, lat_col])
                         .groupby("COD_DEPARTAMENTO", as_index=False)
                         .agg(LONGITUD=(lon_col, "mean"), LATITUD=(lat_col, "mean")))

    quality = {
        "registros": int(len(deaths)),
        "municipios_sin_match": int(deaths["MUNICIPIO"].eq("SIN IDENTIFICAR").sum()),
        "causas_sin_descripcion": int(deaths["NOMBRE_CAUSA"].eq("Descripción no disponible en catálogo").sum()),
        "meses_invalidos": int((~deaths["MES"].between(1, 12)).sum()),
        "grupos_edad_sin_clasificar": int((~deaths["GRUPO_EDAD1"].isin(range(30))).sum()),
        "departamentos_con_coordenadas": int(geo_centroids["COD_DEPARTAMENTO"].nunique()) if not geo_centroids.empty else 0,
        "fuente": "DANE · Estadísticas Vitales · Defunciones no fetales 2019",
    }
    logger.info("Datos cargados y validados: %s registros", quality["registros"])
    return deaths, causes, geo_centroids, quality


def card(label, value, detail=""):
    return html.Div([html.Div(label, className="kpi-label"), html.Div(value, className="kpi-value"),
                     html.Div(detail, className="kpi-note")], className="kpi-card")


def empty_fig(message: str, height: int = 330):
    fig = go.Figure()
    fig.add_annotation(text=message, x=.5, y=.5, xref="paper", yref="paper", showarrow=False,
                       font={"size": 14, "color": "#66758a"})
    fig.update_layout(template="plotly_white", height=height, margin={"l": 10, "r": 10, "t": 35, "b": 10})
    return fig


def style_fig(fig, height=340):
    fig.update_layout(template="plotly_white", height=height, font={"family": "Arial, sans-serif", "color": "#24364b"},
                      paper_bgcolor="white", plot_bgcolor="white", margin={"l": 10, "r": 10, "t": 48, "b": 20},
                      hoverlabel={"font_size": 12})
    return fig

try:
    df, causes_catalogue, department_coords, DATA_QUALITY = load_data()
except Exception as exc:
    logger.exception("Error al inicializar el dashboard")
    # Fail loudly with a useful diagnostic instead of silently showing misleading empty charts.
    raise RuntimeError(f"No fue posible iniciar el dashboard con los archivos DANE: {exc}") from exc

app = Dash(__name__, title="Mortalidad en Colombia 2019", update_title="Actualizando análisis…")
server = app.server
server.config["JSON_SORT_KEYS"] = False

@server.get("/healthz")
def healthz():
    return jsonify({"status": "ok", "year": YEAR, "records_loaded": DATA_QUALITY["registros"]}), 200

@server.get("/api/summary")
def api_summary():
    return jsonify({"year": YEAR, "records": DATA_QUALITY["registros"],
                    "departments_with_coordinates": DATA_QUALITY["departamentos_con_coordenadas"],
                    "unmatched_municipality_records": DATA_QUALITY["municipios_sin_match"],
                    "unmatched_cause_descriptions": DATA_QUALITY["causas_sin_descripcion"],
                    "invalid_month_records": DATA_QUALITY["meses_invalidos"],
                    "unclassified_age_group_records": DATA_QUALITY["grupos_edad_sin_clasificar"],
                    "departments_with_coordinates": DATA_QUALITY["departamentos_con_coordenadas"]}), 200

app.layout = html.Div([
    html.Header([
        html.Div([html.Div("CENTRO DE ANALÍTICA · ESTADÍSTICAS VITALES", className="eyebrow"),
                  html.H1("Mortalidad en Colombia"),
                  html.P("Dashboard interactivo de defunciones no fetales · 2019", className="subtitle")], className="hero-copy"),
        html.Div([html.Span("DANE", className="source-pill"), html.Span("Python · Dash · Plotly", className="tech-pill")], className="hero-tags")
    ], className="hero"),
    html.Div([
        html.Div([html.Label("Departamento"), dcc.Dropdown(id="department-filter",
            options=[{"label": str(x).title(), "value": x} for x in sorted(df["DEPARTAMENTO"].dropna().unique())],
            placeholder="Todos los departamentos", clearable=True)], className="filter"),
        html.Div([html.Label("Sexo"), dcc.Dropdown(id="sex-filter",
            options=[{"label": x, "value": x} for x in ["Hombres", "Mujeres", "Indeterminado", "Sin dato"]],
            placeholder="Todos los sexos", clearable=True)], className="filter"),
        html.Div([html.Label("Mes"), dcc.Dropdown(id="month-filter",
            options=[{"label": v, "value": k} for k, v in MONTHS.items()],
            placeholder="Todo el año", clearable=True)], className="filter"),
        html.Button([html.Span("↺", className="button-icon"), " Limpiar filtros"], id="clear-filters", n_clicks=0, className="clear-button")
    ], className="filters"),
    html.Div(id="kpis", className="kpi-grid"),
    html.Div(id="quality-note", className="quality-note"),
    html.Div([
        html.Section([html.Div([html.H2("Distribución geográfica"), html.Span("01", className="section-number")], className="section-head"),
                      html.P("Conteo de defunciones por departamento. Cada burbuja se ubica en un centroide aproximado calculado con coordenadas municipales DIVIPOLA; no son límites departamentales oficiales."),
                      dcc.Graph(id="map-chart", config={"displayModeBar": True, "displaylogo": False})], className="panel"),
        html.Section([html.Div([html.H2("Evolución mensual"), html.Span("02", className="section-number")], className="section-head"),
                      html.P("Variación del número de registros durante los doce meses del año."),
                      dcc.Graph(id="monthly-chart", config={"displayModeBar": False})], className="panel")
    ], className="chart-grid"),
    html.Div([
        html.Section([html.Div([html.H2("Homicidios y agresiones con arma de fuego · X95"), html.Span("03", className="section-number")], className="section-head"),
                      html.P("Top cinco municipios con registros clasificados como homicidio o con código CIE-10 que comienza por X95. Cada registro se cuenta una sola vez; no equivale a una clasificación general de violencia."),
                      dcc.Graph(id="homicide-chart", config={"displayModeBar": False})], className="panel"),
        html.Section([html.Div([html.H2("Diez municipios con menor conteo"), html.Span("04", className="section-number")], className="section-head"),
                      html.P("Diez municipios con menos defunciones entre los que tienen registros en la selección. Es un conteo absoluto, no un índice ni una tasa ajustada por población; los municipios con cero registros no aparecen."),
                      dcc.Graph(id="lowest-chart", config={"displayModeBar": False})], className="panel")
    ], className="chart-grid"),
    html.Div([
        html.Section([html.Div([html.H2("Principales causas de muerte"), html.Span("05", className="section-number")], className="section-head"),
                      html.P("Diez códigos CIE-10 con más registros, ordenados de mayor a menor."),
                      dash_table.DataTable(id="causes-table", columns=[
                          {"name": "Código CIE-10", "id": "COD_MUERTE"},
                          {"name": "Descripción de la causa", "id": "NOMBRE_CAUSA"},
                          {"name": "Casos", "id": "CASOS", "type": "numeric", "format": {"specifier": ","}},
                      ], data=[], page_size=10, sort_action="native", export_format="csv", export_headers="display",
                      style_table={"overflowX": "auto"},
                      style_cell={"fontFamily": "Arial", "fontSize": "13px", "padding": "11px", "whiteSpace": "normal", "height": "auto", "textAlign": "left"},
                      style_header={"backgroundColor": "#eef3f8", "fontWeight": "bold", "color": "#1b3554"},
                      style_data_conditional=[{"if": {"row_index": "odd"}, "backgroundColor": "#fafbfd"}])], className="panel"),
        html.Section([html.Div([html.H2("Defunciones por sexo y departamento"), html.Span("06", className="section-number")], className="section-head"),
                      html.P("Barras apiladas para los quince departamentos con mayor número de registros en la selección."),
                      dcc.Graph(id="sex-chart", config={"displayModeBar": False})], className="panel"),
        html.Section([html.Div([html.H2("Mortalidad por etapa del ciclo de vida"), html.Span("07", className="section-number")], className="section-head"),
                      html.P("Agrupación operativa de GRUPO_EDAD1 conforme a los rangos de la guía. Verifica el diccionario DANE antes de interpretar las etiquetas como edades cronológicas."),
                      dcc.Graph(id="age-chart", config={"displayModeBar": False})], className="panel"),
    ], className="chart-grid single-column"),
    html.Footer([html.Div("Fuente: DANE · Estadísticas Vitales · Defunciones no fetales 2019 y DIVIPOLA."),
                 html.Div("Herramienta académica de análisis exploratorio. Los conteos no deben interpretarse como tasas ni como estimaciones de riesgo poblacional."),
                 html.Div([html.A("Estado del servicio", href="/healthz", target="_blank"), " · ", html.A("Resumen técnico", href="/api/summary", target="_blank")])], className="footer")
], className="page")

@app.callback(Output("department-filter", "value"), Output("sex-filter", "value"), Output("month-filter", "value"),
              Input("clear-filters", "n_clicks"), prevent_initial_call=True)
def clear_filters(_n):
    return None, None, None

@app.callback(
    Output("kpis", "children"), Output("quality-note", "children"), Output("map-chart", "figure"),
    Output("monthly-chart", "figure"), Output("homicide-chart", "figure"), Output("lowest-chart", "figure"),
    Output("causes-table", "data"), Output("sex-chart", "figure"), Output("age-chart", "figure"),
    Input("department-filter", "value"), Input("sex-filter", "value"), Input("month-filter", "value")
)
def update_dashboard(department, sex, month):
    filtered = df
    if department:
        filtered = filtered.loc[filtered["DEPARTAMENTO"].eq(department)]
    if sex:
        filtered = filtered.loc[filtered["SEXO_NOMBRE"].eq(sex)]
    if month:
        filtered = filtered.loc[filtered["MES"].eq(int(month))]

    total = len(filtered)
    dep_counts_all = filtered["DEPARTAMENTO"].value_counts()
    top_department = str(dep_counts_all.index[0]).title() if not dep_counts_all.empty else "Sin datos"
    month_counts = filtered["MES"].value_counts()
    top_month = MONTHS.get(int(month_counts.index[0]), "Sin datos") if not month_counts.empty else "Sin datos"
    cause_counts = filtered["NOMBRE_CAUSA"].value_counts()
    top_cause = str(cause_counts.index[0]) if not cause_counts.empty else "Sin datos"
    kpis = [card("Total de defunciones", f"{total:,}", "Registros de la selección"),
            card("Departamento con más casos", top_department, "Dentro de los filtros activos"),
            card("Mes con más defunciones", top_month, "Dentro de los filtros activos"),
            card("Causa más frecuente", top_cause, "Descripción según catálogo CIE-10")]
    quality_text = (f"Control de calidad · {DATA_QUALITY['registros']:,} registros del año 2019 · "
                    f"{DATA_QUALITY['municipios_sin_match']:,} sin correspondencia DIVIPOLA · "
                    f"{DATA_QUALITY['causas_sin_descripcion']:,} sin descripción CIE-10 · "
                    f"{DATA_QUALITY['meses_invalidos']:,} con mes inválido · "
                    f"{DATA_QUALITY['grupos_edad_sin_clasificar']:,} con grupo de edad fuera de 0–29 · "
                    f"{DATA_QUALITY['departamentos_con_coordenadas']} departamentos con coordenadas. "
                    "Los indicadores y gráficas se recalculan con los filtros activos.")

    dep_counts = filtered.groupby(["COD_DEPARTAMENTO", "DEPARTAMENTO"], dropna=False).size().rename("CASOS").reset_index()
    map_df = dep_counts.merge(department_coords, on="COD_DEPARTAMENTO", how="left").dropna(subset=["LATITUD", "LONGITUD"])
    if not map_df.empty:
        map_fig = px.scatter_geo(map_df, lat="LATITUD", lon="LONGITUD", size="CASOS", color="CASOS",
            hover_name="DEPARTAMENTO", hover_data={"CASOS": ":,", "LATITUD": False, "LONGITUD": False, "COD_DEPARTAMENTO": False},
            scope="south america", projection="natural earth", size_max=42, color_continuous_scale="Tealgrn",
            title="Defunciones registradas por departamento")
        map_fig.update_geos(lataxis_range=[-5, 14], lonaxis_range=[-82, -66], showcountries=True, showland=True,
                            landcolor="#f1f5f9", showocean=True, oceancolor="#eaf3fb", showcoastlines=True,
                            countrycolor="#9caaba", showframe=False)
        map_fig.update_layout(height=400, margin={"l": 0, "r": 0, "t": 48, "b": 0}, coloraxis_colorbar_title="Casos")
        style_fig(map_fig, 400)
    else:
        map_fig = empty_fig("No hay coordenadas geográficas disponibles para los filtros activos", 400)

    monthly_counts = filtered.groupby("MES").size()
    # If a month is selected, show only that month instead of drawing false zeros
    # for months excluded by the active filter.
    if month:
        monthly = monthly_counts.rename("CASOS").reset_index()
    else:
        monthly = monthly_counts.reindex(range(1, 13), fill_value=0).rename("CASOS").reset_index()
    monthly["MES_NOMBRE"] = monthly["MES"].map(MONTHS)
    monthly_fig = px.line(monthly, x="MES_NOMBRE", y="CASOS", markers=True, title="Defunciones por mes")
    monthly_fig.update_traces(line={"width": 3, "color": "#168c87"}, marker={"size": 7})
    monthly_fig.update_layout(xaxis_title="Mes", yaxis_title="Número de defunciones")
    style_fig(monthly_fig)

    # Operational definition for this chart: records classified as homicide OR
    # carrying an X95 code. OR avoids counting a record twice when both apply.
    homicide_mask = filtered["MANERA_MUERTE"].str.casefold().eq("homicidio") | filtered["COD_MUERTE"].str.startswith("X95", na=False)
    homicide = filtered.loc[homicide_mask]
    homicide_city = homicide.groupby(["MUNICIPIO", "DEPARTAMENTO"]).size().rename("CASOS").reset_index()
    homicide_city["CIUDAD"] = homicide_city["MUNICIPIO"].str.title() + " · " + homicide_city["DEPARTAMENTO"].str.title()
    homicide_city = homicide_city.nlargest(5, "CASOS").sort_values("CASOS")
    if not homicide_city.empty:
        homicide_fig = px.bar(homicide_city, x="CASOS", y="CIUDAD", orientation="h", text="CASOS",
                              title="Top 5 municipios · homicidio o código X95", color="CASOS", color_continuous_scale="Reds")
        homicide_fig.update_traces(textposition="outside", cliponaxis=False)
        homicide_fig.update_layout(xaxis_title="Casos", yaxis_title="", coloraxis_showscale=False)
        style_fig(homicide_fig)
    else:
        homicide_fig = empty_fig("No se encontraron registros X95 clasificados como homicidio con los filtros activos")

    city_source = filtered.loc[filtered["MUNICIPIO"].ne("SIN IDENTIFICAR")]
    city_counts = city_source.groupby(["MUNICIPIO", "DEPARTAMENTO"]).size().rename("CASOS").reset_index()
    city_counts["CIUDAD"] = city_counts["MUNICIPIO"].str.title() + " · " + city_counts["DEPARTAMENTO"].str.title()
    lowest = city_counts.nsmallest(10, "CASOS")
    if not lowest.empty:
        lowest_fig = px.pie(lowest, names="CIUDAD", values="CASOS", hole=.42, title="Menor conteo absoluto entre municipios con registros")
        lowest_fig.update_traces(textposition="inside", textinfo="percent", hovertemplate="%{label}<br>Casos: %{value:,}<br>Participación: %{percent}<extra></extra>")
        style_fig(lowest_fig)
        lowest_fig.update_layout(legend={"font": {"size": 10}})
    else:
        lowest_fig = empty_fig("No hay municipios para comparar con los filtros activos")

    causes_table = (filtered.groupby(["COD_MUERTE", "NOMBRE_CAUSA"]).size().rename("CASOS").reset_index()
                    .sort_values("CASOS", ascending=False).head(10))
    causes_table["CASOS"] = causes_table["CASOS"].astype(int)
    table_data = causes_table.to_dict("records")

    dep_sex = filtered.groupby(["DEPARTAMENTO", "SEXO_NOMBRE"]).size().rename("CASOS").reset_index()
    top_deps = filtered["DEPARTAMENTO"].value_counts().head(15).index.tolist()
    dep_sex = dep_sex.loc[dep_sex["DEPARTAMENTO"].isin(top_deps)]
    if not dep_sex.empty:
        sex_fig = px.bar(dep_sex, x="DEPARTAMENTO", y="CASOS", color="SEXO_NOMBRE", barmode="stack",
                         category_orders={"DEPARTAMENTO": top_deps},
                         color_discrete_map={"Hombres": "#2878b5", "Mujeres": "#e58a72", "Indeterminado": "#8a8f98", "Sin dato": "#b9c4d0"},
                         title="Departamentos con más registros por sexo")
        sex_fig.update_layout(xaxis_title="Departamento", yaxis_title="Número de defunciones", legend_title="Sexo", xaxis_tickangle=-40,
                              margin={"l": 10, "r": 10, "t": 48, "b": 100})
        style_fig(sex_fig, 430)
    else:
        sex_fig = empty_fig("No hay datos para comparar por sexo y departamento", 430)

    age_df = pd.DataFrame([{"ETAPA": label, "CASOS": int(filtered["GRUPO_EDAD1"].isin(list(codes)).sum())} for label, codes in AGE_GROUPS])
    age_fig = px.bar(age_df, x="ETAPA", y="CASOS", text="CASOS", title="Defunciones por grupo de edad")
    age_fig.update_traces(marker_color="#168c87", texttemplate="%{text:,}", textposition="outside", cliponaxis=False)
    age_fig.update_layout(xaxis_title="Categoría definida en la guía (GRUPO_EDAD1)", yaxis_title="Número de defunciones", xaxis_tickangle=-35,
                          margin={"l": 10, "r": 10, "t": 48, "b": 115})
    style_fig(age_fig, 400)
    return kpis, quality_text, map_fig, monthly_fig, homicide_fig, lowest_fig, table_data, sex_fig, age_fig

if __name__ == "__main__":
    # Render supplies PORT; local execution defaults to 8050.
    port = int(os.getenv("PORT", "8050"))
    app.run(debug=os.getenv("DASH_DEBUG", "false").lower() == "true", host="0.0.0.0", port=port)
