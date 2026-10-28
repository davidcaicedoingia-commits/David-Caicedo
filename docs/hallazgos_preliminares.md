# Hallazgos preliminares — Mortalidad en Colombia, 2019

Este resumen se calculó directamente sobre los tres archivos suministrados (microdatos DANE, catálogo CIE-10 y DIVIPOLA). Son conteos descriptivos del archivo analizado, no tasas poblacionales ni conclusiones causales.

## Calidad de los datos

- Registros de defunciones no fetales de 2019: **244.355**.
- Registros sin correspondencia de municipio en DIVIPOLA: **0**.
- Registros cuyo código CIE-10 no tiene descripción al combinar los niveles de tres y cuatro caracteres: **0**.
- Registros con mes fuera del intervalo 1–12: **0**.
- Departamentos con coordenadas representativas disponibles para el mapa: **33**.

## Evolución mensual

| Mes | Defunciones |
|---|---:|
| Enero | 21.354 |
| Febrero | 17.974 |
| Marzo | 19.952 |
| Abril | 19.233 |
| Mayo | 20.292 |
| Junio | 20.742 |
| Julio | 21.372 |
| Agosto | 21.160 |
| Septiembre | 19.778 |
| Octubre | 20.490 |
| Noviembre | 20.330 |
| Diciembre | 21.678 |

Diciembre registró el mayor conteo mensual (21.678) y febrero el menor (17.974). Esta variación describe el número de registros por mes y, por sí sola, no explica sus causas.

## Departamentos con más registros

| Departamento | Defunciones |
|---|---:|
| Bogotá, D.C. | 38.760 |
| Antioquia | 34.473 |
| Valle del Cauca | 28.443 |
| Atlántico | 14.804 |
| Santander | 11.894 |

Los conteos absolutos dependen, entre otros factores, del tamaño de la población. No deben interpretarse como riesgo individual ni utilizarse para comparar el riesgo entre territorios sin denominadores poblacionales.

## Causas más frecuentes

| Código CIE-10 | Descripción | Casos |
|---|---|---:|
| I219 | Infarto agudo del miocardio, sin otra especificación | 35.088 |
| J449 | Enfermedad pulmonar obstructiva crónica, no especificada | 7.210 |
| J440 | Enfermedad pulmonar obstructiva crónica con infección aguda de las vías respiratorias inferiores | 6.445 |
| J189 | Neumonía, no especificada | 5.798 |
| C169 | Tumor maligno del estómago, parte no especificada | 5.125 |
| C349 | Tumor maligno de los bronquios o del pulmón, parte no especificada | 4.438 |
| X954 | Agresión con disparo de otras armas de fuego y las no especificadas, calles y carreteras | 4.396 |
| C509 | Tumor maligno de la mama, parte no especificada | 3.619 |
| C61 | Tumor maligno de la próstata | 3.437 |
| I10 | Hipertensión esencial (primaria) | 3.317 |

La clasificación combina códigos de tres y cuatro caracteres porque ambos niveles aparecen en los microdatos. El software conserva el nivel original del código y lo vincula con la descripción correspondiente del catálogo.

## Homicidios con código X95

Aplicando el criterio operativo `MANERA_MUERTE = Homicidio` y código CIE-10 que comienza por `X95`, los cinco municipios con más registros son:

| Municipio | Departamento | Casos |
|---|---|---:|
| Santiago de Cali | Valle del Cauca | 971 |
| Bogotá, D.C. | Bogotá, D.C. | 601 |
| Medellín | Antioquia | 428 |
| Barranquilla | Atlántico | 260 |
| San José de Cúcuta | Norte de Santander | 206 |

Este filtro corresponde al criterio específico de la actividad; no equivale al total de homicidios por todos los mecanismos.

## Defunciones por sexo

| Código de sexo en el microdato | Casos |
|---|---:|
| 1 | 134.573 |
| 2 | 109.689 |
| 3 | 93 |

La aplicación etiqueta los códigos como Hombres, Mujeres e Indeterminado, respectivamente. Se deben interpretar como categorías codificadas por el microdato DANE.

## Distribución por ciclo de vida

| Categoría de la actividad | Casos |
|---|---:|
| Mortalidad neonatal (0–4) | 4.520 |
| Mortalidad infantil (5–6) | 2.771 |
| Primera infancia (7–8) | 1.518 |
| Niñez (9–10) | 1.993 |
| Adolescencia (11) | 3.795 |
| Juventud (12–13) | 11.840 |
| Adultez temprana (14–16) | 17.276 |
| Adultez intermedia (17–19) | 29.105 |
| Vejez (20–24) | 115.453 |
| Longevidad / centenarios (25–28) | 56.061 |
| Edad desconocida (29) | 23 |

La agrupación sigue los rangos de `GRUPO_EDAD1` especificados en la guía. Las categorías deben describirse con esos rangos operativos; no se deben reinterpretar como edades exactas cuando el código representa un intervalo.

## Limitaciones importantes

1. El mapa utiliza burbujas ubicadas en centroides aproximados calculados con coordenadas municipales DIVIPOLA. No representa polígonos oficiales de límites departamentales.
2. La visualización de los diez municipios con menor conteo utiliza números absolutos entre municipios con registros. Para construir un índice o una tasa de mortalidad se requieren denominadores poblacionales comparables y una definición explícita de la tasa.
3. El análisis es descriptivo. No identifica causas de las variaciones ni establece relaciones causales.
4. Las capturas de pantalla deben obtenerse ejecutando la aplicación localmente o desde la URL pública una vez desplegada.
