# Dashboard interactivo de mortalidad en Colombia — 2019

**Proyecto académico de análisis de Estadísticas Vitales (defunciones no fetales) de Colombia para el año 2019.**

- **Aplicación web:** https://david-caicedo.onrender.com/
- **Repositorio GitHub:** https://github.com/davidcaicedoingia-commits/David-Caicedo
- **Plataforma de despliegue:** Render
- **Tecnologías principales:** Python, Dash, Plotly y pandas.

> **Integrantes:** Andrés David Caicedo Grajales.  
> Si el trabajo fue realizado por más integrantes, agrega aquí sus nombres completos. La actividad exige que cada integrante realice su entrega individual en el aula virtual.

---

## 1. Introducción

Este proyecto desarrolla un dashboard web interactivo para explorar las defunciones no fetales registradas en Colombia durante 2019. La aplicación organiza y presenta información de las Estadísticas Vitales del Departamento Administrativo Nacional de Estadística (DANE), con el propósito de facilitar la consulta descriptiva de los registros por departamento, sexo, mes, municipio, causa de muerte y grupo de edad.

El tablero permite aplicar filtros y observar cómo cambian los indicadores y las visualizaciones según los criterios seleccionados. Los resultados corresponden a conteos de registros y deben interpretarse dentro del alcance y las limitaciones de los datos disponibles.

## 2. Objetivo

Construir y desplegar una aplicación web interactiva que permita consultar y analizar descriptivamente las defunciones no fetales ocurridas en Colombia durante 2019, mediante indicadores, filtros y visualizaciones que faciliten la exploración temporal, geográfica y demográfica de los registros, así como la identificación de las principales causas de muerte y de los registros asociados a homicidios clasificados bajo el código CIE-10 X95.

## 3. Fuente de información y archivos de datos

Se utilizan los archivos suministrados para la actividad, correspondientes a las Estadísticas Vitales del DANE:

| Archivo de origen solicitado | Archivo incluido en el proyecto | Uso |
|---|---|---|
| `NoFetal2019.xlsx` | `data/NoFetal2019.xlsx` | Microdatos de defunciones no fetales de 2019. |
| `CodigosDeMuerte.xlsx` | `data/CodigosDeMuerte.xlsx` | Diccionario/catálogo de códigos de causas de muerte. |
| `Divipola.xlsx` | `data/Divipola.xlsx` | Referencia de la División Político-Administrativa de Colombia. |

Portal de referencia: [Estadísticas Vitales — DANE](https://www.dane.gov.co/index.php/estadisticas-por-tema/salud/nacimientos-y-defunciones/defunciones-no-fetales).

Los archivos se encuentran incorporados en la carpeta `data/` del repositorio. Para la ejecución de producción, la aplicación utiliza tablas agregadas y comprimidas generadas previamente a partir de los archivos Excel. De esta manera, no necesita procesar los microdatos completos cada vez que inicia o cuando el usuario cambia un filtro.

## 4. Visualizaciones e interpretación

El dashboard contiene filtros por **departamento, sexo y mes**, indicadores generales y las siguientes visualizaciones:

### 4.1. Distribución geográfica de las defunciones

Mapa de burbujas que representa los conteos de defunciones por departamento. El tamaño y el color de las burbujas permiten comparar visualmente la magnitud de los registros.

**Consideración:** la ubicación se representa mediante coordenadas aproximadas derivadas de referencias municipales de DIVIPOLA. No corresponde a un mapa coroplético ni dibuja los límites oficiales de cada departamento.

### 4.2. Evolución mensual

Gráfico de líneas que presenta el total de defunciones registradas en cada mes de 2019. Permite observar variaciones en el número de registros a lo largo del año e identificar los meses con mayores o menores conteos.

### 4.3. Municipios con más registros de homicidios/agresiones con arma de fuego — CIE-10 X95

Gráfico de barras horizontales con los cinco municipios que presentan los mayores conteos de registros clasificados bajo el criterio utilizado para homicidio/agresión con arma de fuego, asociado al código CIE-10 X95.

**Consideración:** se presentan conteos absolutos de registros, no tasas de homicidio ni una clasificación general de violencia municipal. La interpretación depende de la definición y los códigos incluidos en el procesamiento.

### 4.4. Diez municipios con menor conteo de defunciones

Gráfico de barras horizontales que compara diez municipios con los menores conteos absolutos entre los municipios que aparecen en los registros.

**Consideración:** un conteo menor no significa necesariamente un menor riesgo o una menor tasa de mortalidad. Para calcular tasas se necesitarían denominadores poblacionales comparables.

### 4.5. Principales causas de muerte

Tabla ordenada por número de casos que presenta el código CIE-10, la descripción de la causa y el total de registros. Permite identificar las causas con mayor frecuencia en la base analizada.

### 4.6. Defunciones por sexo y departamento

Gráfico de barras apiladas que compara los conteos de defunciones por sexo en los departamentos con mayor número de registros. Facilita observar la composición de los conteos según sexo y departamento.

### 4.7. Defunciones por grupo de edad

Gráfico de barras que presenta los conteos agrupados a partir de la variable `GRUPO_EDAD1`, según la agrupación operativa implementada en el procesamiento.

**Consideración:** antes de interpretar las categorías como etapas del ciclo de vida o rangos cronológicos específicos, se debe contrastar la codificación con el diccionario oficial de variables del DANE. La visualización actual es un gráfico de barras por categorías, no un histograma estadístico de una variable continua.

### 4.8. Filtros interactivos e indicadores

Los filtros de departamento, sexo y mes permiten actualizar las visualizaciones y los indicadores del tablero. El control **Limpiar filtros** restablece la consulta general.

Los indicadores resumen el total de registros de la selección y destacan categorías con mayores conteos según los datos procesados.

### Capturas de pantalla y hallazgos

Agrega en esta sección capturas tomadas de la aplicación desplegada. Se recomienda incluir una captura general del dashboard y, si es posible, capturas ampliadas del mapa, evolución mensual, causas de muerte y distribución por sexo y edad.

Guarda las imágenes dentro de una carpeta `docs/capturas/` en el repositorio y utiliza rutas relativas, por ejemplo:

```markdown
![Vista general del dashboard](docs/capturas/dashboard_general.png)
```

**Hallazgos descriptivos:** redacta aquí los resultados que observes directamente en la aplicación y que hayas contrastado con los datos. Por ejemplo, indica qué mes, departamento o causa presenta el mayor conteo en la selección analizada. No incluyas conclusiones que no hayas verificado.

## 5. Estructura del proyecto

```text
David-Caicedo/
├── app.py
├── build_summaries.py
├── validar_datos.py
├── requirements.txt
├── runtime.txt
├── render.yaml
├── README.md
├── assets/
│   └── style.css
├── data/
│   ├── NoFetal2019.xlsx
│   ├── CodigosDeMuerte.xlsx
│   ├── Divipola.xlsx
│   └── summary/
│       ├── overview.csv.gz
│       ├── municipios.csv.gz
│       ├── homicidios.csv.gz
│       ├── causas.csv.gz
│       ├── edades.csv.gz
│       ├── coordenadas.csv.gz
│       └── quality.json
└── docs/
    └── capturas/
```

| Archivo o carpeta | Descripción |
|---|---|
| `app.py` | Código principal de la aplicación Dash, diseño del dashboard, filtros, indicadores y callbacks de las visualizaciones. |
| `build_summaries.py` | Procesa los archivos Excel y genera las tablas agregadas comprimidas que consume la aplicación. |
| `validar_datos.py` | Script de apoyo para revisar la estructura y calidad de los datos procesados. |
| `requirements.txt` | Dependencias de Python necesarias para ejecutar el proyecto. |
| `runtime.txt` | Versión de Python utilizada en el despliegue. |
| `render.yaml` | Configuración de referencia para el servicio en Render. |
| `assets/style.css` | Estilos visuales y reglas de diseño adaptable. |
| `data/` | Archivos originales suministrados para el análisis. |
| `data/summary/` | Tablas agregadas y comprimidas que utiliza la aplicación en producción. |
| `docs/capturas/` | Capturas de pantalla que documentan las visualizaciones y resultados. |

## 6. Requisitos de software y librerías

El proyecto utiliza **Python 3.12.11**. Las dependencias principales están fijadas en `requirements.txt`:

| Librería | Versión | Uso |
|---|---:|---|
| Dash | 3.2.0 | Construcción de la aplicación web interactiva. |
| pandas | 2.2.3 | Lectura, transformación y análisis de datos. |
| Plotly | 6.0.1 | Construcción de gráficos interactivos. |
| openpyxl | 3.1.5 | Lectura de archivos Excel. |
| Gunicorn | 23.0.0 | Servidor WSGI utilizado en el despliegue. |

Herramientas utilizadas: Python, Visual Studio Code (u otro editor compatible), Git, GitHub y Render.

## 7. Instalación y ejecución local

### 7.1. Clonar el repositorio

```bash
git clone https://github.com/davidcaicedoingia-commits/David-Caicedo.git
cd David-Caicedo
```

### 7.2. Crear y activar un entorno virtual

En Windows:

```bash
py -3.12 -m venv venv
venv\Scripts\activate
```

En macOS o Linux:

```bash
python3.12 -m venv venv
source venv/bin/activate
```

### 7.3. Instalar las dependencias

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

### 7.4. Ejecutar la aplicación

```bash
python app.py
```

Luego, abrir en el navegador:

```text
http://127.0.0.1:8050
```

### 7.5. Regenerar las tablas agregadas (opcional)

La aplicación ya incluye los archivos procesados en `data/summary/`. Solo si se modifican o reemplazan los archivos Excel originales, se deben regenerar las tablas:

```bash
python build_summaries.py
```

Después de regenerarlas, se deben revisar los resultados y subir al repositorio los archivos actualizados de `data/summary/`.

## 8. Despliegue en Render (PaaS)

La aplicación está desplegada como un servicio web en Render y puede consultarse en:

**URL pública:** https://david-caicedo.onrender.com/

Configuración utilizada:

- **Tipo de servicio:** Web Service.
- **Repositorio:** GitHub, conectado al servicio de Render.
- **Build command:**

```bash
pip install -r requirements.txt
```

- **Start command:**

```bash
gunicorn app:server --workers 1 --threads 2 --timeout 120
```

- **Versión de Python:** `3.12.11`, especificada en `runtime.txt`.
- **Health check:** `/healthz`.

### Pasos generales de despliegue

1. Subir el proyecto completo al repositorio de GitHub, incluyendo `app.py`, `requirements.txt`, `runtime.txt`, `assets/` y `data/summary/`.
2. Crear un servicio **Web Service** en Render y conectar el repositorio.
3. Configurar los comandos de construcción y ejecución indicados anteriormente.
4. Confirmar que la versión de Python corresponda a `3.12.11`.
5. Ejecutar el despliegue y esperar a que Render indique que el servicio está disponible.
6. Abrir la URL pública y comprobar que el dashboard y sus filtros funcionen.

**Nota sobre el plan gratuito:** Render puede suspender temporalmente un servicio gratuito después de un periodo sin actividad. La primera visita posterior puede tardar mientras el servicio vuelve a iniciar. Esto no requiere mantener abierto el computador desde el cual se desarrolló el proyecto.

## 9. Validación y consideraciones metodológicas

El proyecto incluye tablas resumidas y un archivo `quality.json` con controles básicos de procesamiento. En la versión documentada, el total de registros de origen reportado es **244.355**. Este valor es un conteo de registros procesados y no debe confundirse con una tasa de mortalidad.

Para interpretar correctamente los resultados:

- Diferenciar conteos absolutos de tasas poblacionales.
- No interpretar los municipios con menos registros como los de menor riesgo sin incorporar población de referencia.
- Tener presente que el mapa utiliza coordenadas aproximadas y no polígonos oficiales departamentales.
- Verificar la codificación de `GRUPO_EDAD1` con el diccionario oficial del DANE antes de asignar nombres de etapas del ciclo de vida.
- Interpretar los resultados como análisis descriptivos de los registros disponibles para 2019.

## 10. Entrega de la actividad

Para realizar la entrega en el aula virtual, incluir en el comentario:

- **Nombre completo de los integrantes:** Andrés David Caicedo Grajales y los demás integrantes, si aplica.
- **URL de la aplicación desplegada:** https://david-caicedo.onrender.com/
- **URL del repositorio GitHub:** https://github.com/davidcaicedoingia-commits/David-Caicedo

La actividad indica que cada integrante debe realizar su entrega individualmente desde su respectiva aula virtual. Antes de entregar, comprobar que la aplicación esté accesible públicamente y que el repositorio incluya este `README.md`, el código y los archivos de datos requeridos.

---

**Proyecto académico — Estadísticas Vitales, defunciones no fetales de Colombia, 2019.**
