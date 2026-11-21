# Datos del simulador

Esta carpeta trae todo lo necesario para revisar de dónde sale cada número del motor, sin los microdatos de personas.

| Carpeta | Qué hay |
|---|---|
| `tablas/` | CSV con las tablas agregadas que usa el motor. Se generan con `backend/scripts/exportar_csv.py`. |
| `estimaciones/` | Los JSON con cada estimación: valor, unidad, fuente, script, tamaño de muestra, error estándar o intervalo, y nota. |
| `scripts/` | Los scripts que calculan esas estimaciones a partir de los microdatos. |

## Las tablas

| Archivo | Contenido | Fuente |
|---|---|---|
| `parametros.csv` | Los 68 parámetros del motor, con estado (dato o derivado), país y fuente | `backend/app/sim/params.py` |
| `ocupaciones.csv` | Las 118 ocupaciones (ISCO-08, 3 dígitos): empleos observados, probabilidad de cambiar de grupo, duración mediana, exposición a IA y sueldo relativo | JobHop; Microsoft y Eloundou et al.; ESI 2023-2025 |
| `transiciones_ocupacion.csv` | A qué ocupación pasa la gente de cada ocupación cuando cambia de grupo | JobHop |
| `sueldo_edad_educacion.csv` | Percentiles del ingreso por edad y educación | ESI 2025 |
| `universidades_magister.csv` | 51 universidades con magíster: selectividad, número de programas, arancel anual mediano, duración y fracción no diurna | SIES 2026; selectividad con la PAES 2024-2025 de DEMRE |
| `tablas_ine_y_paneles.csv` | Fecundidad, nupcialidad, mortalidad, despido por rubro y tamaño, desocupación, tasa de ahorro por quintil y otros parámetros de los paneles | INE, EPF, EPS, ELSOC |
| `empresas.csv` | Los nombres de empresas que usa el juego | Lista armada a mano; no sale de una base de datos |

## Las estimaciones

| Archivo | Qué estima | Datos |
|---|---|---|
| `modelo_paneles.json` y sus `_detalle` | Despido, antigüedad, encontrar trabajo, pausas, emprendimiento, pareja, hijos, bienestar | EPS 2024, ELSOC 2016-2022 |
| `modelo_ofertas.json` | Ofertas, sueldo de reserva, sueldo relativo por ocupación, tipo de empleador, independientes | SCE (Fed de Nueva York), ESI 2023-2025, Get on Board, empleos públicos |
| `modelo_literatura.json` | Cifras leídas en papers e informes, con URL y página | Ver cada clave |
| `modelo_magister.json` | Prima del magíster por selectividad, universidades y aranceles | DIPRES 2026, SIES 2026, DEMRE |
| `modelo_beneficios.json` y sus `_detalle` | Efecto de trabajar 50 o 55 horas, de bajar el ritmo y de dejar de trabajar | ESI 2023-2025, ELSOC |
| `modelo_emprender_esi.json` | Ingreso de empleadores y de trabajadores por cuenta propia frente a asalariados | ESI 2023-2025 |
| `base_bienestar.json` | Satisfacción y salud de partida por edad | ELSOC |
| `calibracion*.json`, `objetivos_esi.json` | Calibraciones de la primera ronda: perfiles de sueldo, fecundidad, mortalidad, EPF, flujos laborales | ESI, INE, EPS, ELSOC |

## Por qué no están los microdatos

- Pesan unos 500 MB y varios archivos pasan el límite de 100 MB de GitHub.
- La Encuesta de Protección Social tiene condiciones de uso para investigación, y este repo es público.
- Las tablas y estimaciones de esta carpeta son agregadas: ningún archivo tiene datos de una persona.

## Cómo reproducir las estimaciones

1. Baja los microdatos en una carpeta `datos_laborales/`, al lado del repo:

   | Carpeta | Fuente | Dónde |
   |---|---|---|
   | `eps/` | Encuesta de Protección Social 2024 (y 2020) | Subsecretaría de Previsión Social, previsionsocial.gob.cl |
   | `elsoc/` | ELSOC 2016-2022, versión larga y ancha | COES, dataverse.harvard.edu (licencia CC0) |
   | `esi_ine/` | Encuesta Suplementaria de Ingresos 2023, 2024 y 2025 | ine.gob.cl, sección Bases de datos |
   | `sce_nyfed/` | SCE Labor Market Survey, microdatos públicos | newyorkfed.org/microeconomics/sce |
   | `jobhop/` | JobHop v2 (parquet) | Hugging Face, licencia CC BY 4.0 |
   | `exposicion_ia/` | Microsoft, "Working with AI", y Eloundou et al. | Repositorios públicos de cada estudio |
   | `mifuturo/`, `empleos_publicos/`, `getonbrd/` | Mineduc, Servicio Civil y API de Get on Board | mifuturo.cl, datos.gob.cl, getonbrd.com |

2. Corre los scripts de `scripts/modelo/` desde esa carpeta. La mayoría dice en su encabezado qué lee y qué escribe; los de Python se corren con `uv run --with pandas --with numpy --with pyreadstat --with statsmodels python -I script.py`.
3. Regenera las tablas del motor y los CSV desde `backend/`:

   ```bash
   uv run scripts/build_sim_data.py --datos "../../datos_laborales"
   uv run python scripts/exportar_csv.py ../datos/tablas
   ```
