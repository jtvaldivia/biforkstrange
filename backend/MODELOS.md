# Modelos del simulador

El motor vive en `backend/app/sim/`. Es una microsimulación de paso anual: el estado del gemelo se copia en N universos (1.000 por defecto), cada año se aplica una decisión y los módulos corren en orden fijo. No usa LLM.

## Probarlo en la terminal

Desde la raíz del repo:

```bash
make jugar PERFIL=perfiles/ejemplo.json      # partida interactiva, una decisión por año
make menu PERFIL=perfiles/ejemplo.json       # solo el menú de este año
make comparar PERFIL=perfiles/ejemplo.json   # planes completos, lado a lado
make supuestos                               # qué parámetros son dato y cuáles supuesto
make validar                                 # cohorte simulada contra ESI y EPS
```

O desde `backend/`, con todas las opciones:

```bash
uv run python -m app.cli jugar --perfil perfiles/ejemplo.json --seed 7 --ia rapida --ahorros 20000000
uv run python -m app.cli jugar --perfil perfiles/ejemplo.json --auto "trabajar_mas*2,magister,seguir"
uv run python -m app.cli comparar --perfil perfiles/ejemplo.json --anios 15 \
    --plan "sin cambios=seguir" --plan "magíster=magister" --plan "emprender a los 31=seguir*3,emprender"
uv run python -m app.cli ocupaciones --perfil perfiles/ejemplo.json   # a qué ocupaciones puedes pasar
uv run python -m app.cli ocupaciones --buscar ingenier                # buscar un código
```

El perfil es un JSON en formato `bifurca.perfil`. Los perfiles personales van en `backend/perfiles/` y están en `.gitignore` (el repo es público); solo se versiona `ejemplo.json`, que es ficticio. Si el perfil no trae ahorros, ocupación o Big Five, el motor los supone y lo dice al partir. Se corrigen con `--ahorros`, `--ocupacion` y `--O --C --E --A --N`.

## Qué modelo hace qué

| Modelo | Qué responde | Dónde | Datos |
|---|---|---|---|
| Gemelo contrafactual | "¿Qué habría pasado si elegía otra cosa?" El mismo gemelo vive cada opción con la misma suerte, y la diferencia se mide universo por universo | `luck.py`, `counterfactual.py` | No usa datos: es la técnica de números aleatorios comunes |
| Mercado laboral | Despido, oferta y ascenso compiten cada año; búsqueda desde la cesantía; cicatriz salarial al reemplearse | `modules/labor.py` | EPS 2024, ESI 2025, INE flujos laborales |
| Trayectorias | Qué ocupación viene después de la actual al cambiar de trabajo | `modules/labor.py`, `tables.py` | JobHop: 1,4 millones de transiciones entre 118 ocupaciones |
| Habilidades transferibles | Qué tan fácil es pasar a otra ocupación y cuánto cuesta. La afinidad se mide por la movilidad observada entre ocupaciones | `modules/labor.py` (reconversión), `counterfactual.py` | JobHop |
| Exposición a IA | Cuánto suben el despido y bajan las ofertas según la ocupación, el nivel y el año | `modules/labor.py`, `context.py` | Microsoft y Eloundou et al. por ocupación; Brynjolfsson et al. para el tamaño del efecto |
| Finanzas personales | Gasto con hábito, ahorro o deuda, indemnización, seguro de cesantía y costo de cada decisión | `modules/finance.py` | EPF IX (tasa de ahorro por quintil), CEP |
| Vida familiar | Pareja, separación, hijos y su efecto en el trabajo y el gasto | `modules/family.py` | INE (fecundidad por edad), EPS, COES |
| Bienestar | Energía (esfuerzo y recuperación), licencias por agotamiento, ánimo y tiempo con tu gente | `modules/wellbeing.py` | ELSOC, ENUT 2023, SUSESO |
| Red de contactos | Más contactos traen más ofertas y acortan la búsqueda; la red crece al cambiar de trabajo y se enfría sin trabajar | `modules/network.py` | Solo la dirección del efecto (Rajkumar et al. 2022) |
| Personalidad | Riesgo, ambición y Big Five mueven las tasas de los otros módulos | `profile.py`, `params.py` (`B_*`) | Caliendo et al. 2014, Mueller y Plug 2006 |
| Decisiones de los gemelos | Qué elegiría "gente como tú": logit sobre la frecuencia real de cada decisión, la personalidad y el resultado esperado de cada opción | `choice.py` | EPS, INE, ESI para las frecuencias base |

## Cómo se juega un año

1. El motor arma el menú: por cada decisión posible corre 1.000 futuros a 5 años con la misma suerte y resume ingreso (caso malo, típico y bueno), cesantía, ánimo, energía, ahorros y deuda.
2. Compara cada opción contra "seguir igual", futuro por futuro, y calcula cuántos gemelos como tú la elegirían.
3. Eliges. De los 1.000 futuros de ese año, uno es el que te tocó y la partida sigue desde ahí.
4. En paralelo vive tu sombra: el gemelo que nunca cambia nada y recibe tu misma suerte. Al final se comparan.

`POST /api/juego/turno` expone lo mismo para el frontend. No guarda estado: recibe el perfil, la semilla y las decisiones tomadas, y devuelve tu ficha, la de la sombra, lo que pasó cada año y el menú siguiente.

## Qué tan sólido es

`make supuestos` lista los 92 parámetros: 15 son datos leídos de una fuente, 16 son cálculos propios sobre una fuente y 61 son supuestos del equipo. Los supuestos pesan sobre todo en:

- **IA:** la brecha de 19% es dato, pero cómo crece en el tiempo y cómo se reparte por nivel es supuesto. Con los pesos actuales el efecto se concentra en juniors.
- **Reconversión:** la afinidad sale de JobHop; la probabilidad de lograr el cambio y el castigo de sueldo son supuestos.
- **Energía y agotamiento:** no hay fuente chilena de prevalencia de burnout.
- **Ánimo:** cesantía, reempleo, pareja y separación vienen de ELSOC; el resto solo sigue el signo de la literatura.

Límites que conviene decir en la demo:

- JobHop son currículums de Flandes. Sirve como patrón de movilidad entre ocupaciones, no como mercado chileno.
- El sueldo relativo entre ocupaciones solo distingue los 9 grandes grupos de la ESI, así que todas las ocupaciones profesionales pagan igual en el modelo.
- El puente entre las ocupaciones de EE.UU. (exposición a IA) y las ISCO es propio y aproximado, y las etiquetas ISCO se escribieron a mano.
- Los perfiles parten trabajando o buscando trabajo; todavía no hay etapa de estudios ni emigración.
- La pareja no tiene carrera propia y las finanzas son individuales (sin vivienda ni impuestos).
- El modelo valida distribuciones, no la vida de una persona.

## Regenerar las tablas

`backend/app/sim/data/tablas.json` (51 KB) son tablas agregadas. Los microdatos no van al repo. Con la carpeta `datos_laborales/` a mano:

```bash
make datos DATOS=../../datos_laborales
```
