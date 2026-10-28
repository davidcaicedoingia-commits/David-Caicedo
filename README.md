# Dashboard de mortalidad en Colombia · 2019

Dashboard académico de defunciones no fetales del DANE construido con Dash, pandas y Plotly. Incluye filtros por departamento, sexo y mes; cuatro indicadores; mapa con centroides aproximados; evolución mensual; homicidios/X95; municipios con menor conteo; causas CIE-10; sexo por departamento y grupos de edad.

## Optimización de memoria y velocidad

La versión de producción **no abre los archivos Excel durante el arranque ni al cambiar filtros**. `build_summaries.py` procesa los Excel una sola vez y crea tablas agregadas comprimidas en `data/summary/`. Render carga únicamente esas tablas pequeñas, con dimensiones repetitivas convertidas a `category` y conteos numéricos compactos. Esto conserva los conteos y las dimensiones necesarias para los filtros sin mantener las 244.355 filas individuales en RAM.

Las tablas resumidas generadas para este proyecto son:

- `overview.csv.gz`: 842 filas
- `municipios.csv.gz`: 18.163 filas
- `homicidios.csv.gz`: 4.151 filas
- `causas.csv.gz`: 92.906 filas
- `edades.csv.gz`: 16.006 filas
- `coordenadas.csv.gz`: 33 filas
- `quality.json`: métricas de calidad y conteo de registros de origen

Las seis tablas CSV comprimidas ocupan aproximadamente 1,2 MB en disco. En una medición local de pandas, después de convertir dimensiones repetidas a categorías y conteos a enteros compactos, las tablas ocuparon aproximadamente 2,5 MB de memoria. **Esta cifra no representa la RAM total del proceso**: Python, Dash, Plotly, Flask y Gunicorn también consumen memoria.

## Estructura

```text
.
├── app.py
├── build_summaries.py
├── requirements.txt
├── runtime.txt
├── render.yaml
├── assets/
│   └── style.css
└── data/
    ├── NoFetal2019.xlsx
    ├── CodigosDeMuerte.xlsx
    ├── Divipola.xlsx
    └── summary/
        ├── overview.csv.gz
        ├── municipios.csv.gz
        ├── homicidios.csv.gz
        ├── causas.csv.gz
        ├── edades.csv.gz
        ├── coordenadas.csv.gz
        └── quality.json
```

## Ejecutar localmente

Requiere Python 3.12.11 (también indicado en `runtime.txt`). Desde la carpeta del proyecto:

```bash
python -m pip install -r requirements.txt
python app.py
```

Abre `http://127.0.0.1:8050`.

### Regenerar las tablas resumidas

Solo si se actualizan los Excel de origen, ejecuta:

```bash
python build_summaries.py
```

Este paso se hace localmente antes de subir cambios. No es necesario para iniciar la app en Render, porque el proyecto ya incluye las tablas resumidas generadas.

## Publicar en Render

1. Sube el contenido de esta carpeta al repositorio GitHub conectado a Render, incluida toda la carpeta `data/summary/`.
2. En Render, verifica que el servicio sea **Web Service**, con runtime Python.
3. Build command: `pip install -r requirements.txt`.
4. Start command: `gunicorn app:server --workers 1 --threads 2 --timeout 120`.
5. Python: `3.12.11`. `runtime.txt` ya especifica esa versión; si el servicio tiene una variable `PYTHON_VERSION`, debe coincidir.
6. Health check path: `/healthz`.
7. Ejecuta **Manual Deploy → Deploy latest commit** después de subir los archivos.

El plan Free de Render puede tardar en despertar después de un periodo sin tráfico; eso no significa necesariamente que el código esté lento. El primer arranque en frío del servicio y la velocidad de carga en el navegador son cosas diferentes.

## Comprobaciones

- `/healthz`: estado y número de registros de origen representados en las tablas.
- `/api/summary`: control de calidad y número de filas por tabla agregada.
- El total de casos de `overview.csv.gz` debe sumar **244.355**.

## Notas metodológicas

- El mapa usa centroides aproximados construidos a partir de coordenadas municipales de DIVIPOLA; no dibuja límites oficiales departamentales.
- El gráfico de menor conteo es una comparación de conteos absolutos entre municipios con registros, no una tasa poblacional.
- `GRUPO_EDAD1` se presenta como agrupación operativa. Debe contrastarse con el diccionario oficial del DANE antes de interpretar sus categorías como edades cronológicas.
- Los resultados son descriptivos y no representan por sí solos tasas, riesgos ni inferencia causal.
