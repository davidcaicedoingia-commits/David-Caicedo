# Mortalidad en Colombia — Dashboard interactivo 2019

Aplicación web de analítica exploratoria construida con Python, Dash y Plotly sobre microdatos DANE de defunciones no fetales de 2019.

## Funcionalidades
- Filtros reactivos por departamento, sexo y mes.
- Indicadores clave que se recalculan con los filtros.
- Mapa interactivo de burbujas por departamento, con coordenadas representativas calculadas desde DIVIPOLA (no es un mapa de polígonos oficiales).
- Evolución mensual, municipios con más registros clasificados como homicidio o con código CIE-10 X95 (un registro se cuenta una sola vez), municipios con menor conteo absoluto, tabla de causas, barras apiladas por sexo y distribución por categorías GRUPO_EDAD1.
- Exportación CSV desde la tabla de causas.
- Endpoint de salud `/healthz` y resumen técnico `/api/summary` para comprobar el servicio publicado; incluye registros con mes inválido y cobertura geográfica.
- Validación de archivos y columnas al iniciar; registro de errores en logs.

## Estructura
```text
mortalidad_colombia_2019/
├── app.py
├── requirements.txt
├── runtime.txt
├── render.yaml
├── validar_datos.py
├── README.md
├── docs/
│   └── hallazgos_preliminares.md
├── .gitignore
├── assets/
│   └── style.css
└── data/
    ├── NoFetal2019.xlsx
    ├── CodigosDeMuerte.xlsx
    └── Divipola.xlsx
```

## Requisitos
- Python 3.11 recomendado
- Dependencias fijadas en `requirements.txt`

## Validar los datos antes de ejecutar
Desde la carpeta raíz del proyecto, ejecuta:
```powershell
python validar_datos.py
```
El script comprueba la estructura de los Excel, la correspondencia con DIVIPOLA, la cobertura del catálogo CIE-10 de tres y cuatro caracteres y la validez de los meses. El reporte de hallazgos preliminares está en `docs/hallazgos_preliminares.md`.

## Ejecutar localmente en Windows
1. Instala Python 3.11 desde la página oficial y marca la opción para añadir Python al PATH.
2. Descomprime el ZIP y abre una terminal en la carpeta del proyecto.
3. Crea un entorno virtual:
   ```powershell
   py -3.11 -m venv .venv
   .venv\Scripts\Activate.ps1
   ```
4. Instala las librerías:
   ```powershell
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
5. Ejecuta la aplicación:
   ```powershell
   python app.py
   ```
6. Abre `http://127.0.0.1:8050`.
7. Verifica el estado en `http://127.0.0.1:8050/healthz`.

## Publicar en Render
1. Crea un repositorio en GitHub y carga el contenido de esta carpeta.
2. En Render, selecciona **New + → Web Service** y conecta el repositorio.
3. Usa estos comandos:
   - Build command: `pip install -r requirements.txt`
   - Start command: `gunicorn app:server --workers 2 --timeout 120`
4. Configura `healthCheckPath` como `/healthz` (también está en `render.yaml`).
5. Despliega. Render asignará una URL pública; comprueba que la página principal y `/healthz` respondan correctamente.

> No se puede crear una URL pública real desde el código solamente: el despliegue requiere iniciar sesión en GitHub y Render y autorizar el repositorio.

## Visualizaciones e interpretación
Incluye las siete visualizaciones requeridas por la guía. Los hallazgos preliminares verificados con los microdatos se documentan en `docs/hallazgos_preliminares.md`. Para completar el informe de entrega, ejecuta la aplicación, toma capturas de pantalla de cada sección y describe los resultados junto a cada imagen.

## Criterios metodológicos
- El mapa representa cada departamento mediante una burbuja en un centroide aproximado calculado con coordenadas municipales DIVIPOLA. No son polígonos de límites administrativos oficiales.
- El gráfico de violencia aplica el criterio operativo `MANERA_MUERTE = Homicidio` **o** código CIE-10 que comienza por `X95`. La condición OR incluye registros que cumplen cualquiera de los criterios y evita duplicarlos. No equivale a una clasificación exhaustiva de toda la violencia; si la guía del docente define otra regla, debe ajustarse.
- El gráfico de municipios con menor mortalidad presenta conteos absolutos entre municipios que tienen al menos un registro en la selección. No es una tasa ni un índice ajustado por población. Para calcular tasas se requieren denominadores poblacionales comparables.
- Los rangos de `GRUPO_EDAD1` se aplican según la tabla de la actividad. Las etiquetas se muestran como categorías operativas de la guía; se debe consultar el diccionario DANE antes de interpretarlas como edades literales.
- Los registros sin correspondencia DIVIPOLA o sin descripción en el catálogo se conservan y se notifican en el panel de calidad, evitando descartarlos silenciosamente.

## Software
Python, Dash, Plotly, pandas, openpyxl, Gunicorn, Git, GitHub y Render.

## Revisión antes de entregar
- Ejecutar `python validar_datos.py` y revisar el resultado.
- Probar filtros, limpieza de filtros, tabla y siete visualizaciones.
- Abrir `/healthz` y `/api/summary` después del despliegue.
- Tomar capturas reales de la aplicación publicada y pegarlas en el informe.
- Confirmar que el repositorio de GitHub sea público o esté conectado a Render con los permisos correctos.
- No publicar los datos si la guía académica o la licencia de los archivos establece restricciones.

## Integrantes
David Caicedo Grajales. Completar con los demás integrantes si corresponde.
