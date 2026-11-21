# Modelo del simulador

El motor vive en `backend/app/sim/`. Es una microsimulación de paso anual: el estado del gemelo se copia en N universos (1.000 por defecto), cada año se aplica una decisión y los módulos corren en orden fijo. No usa LLM.

**Regla:** todo parámetro sale de un dato. Los 64 parámetros de `sim/params.py` son 55 datos (leídos o estimados de una fuente) y 9 derivados (una operación escrita sobre datos). No hay supuestos del equipo: lo que no tiene dato no está en el modelo. `make supuestos` los lista con su fuente y su país.

## Probarlo en la terminal

Desde la raíz del repo:

```bash
make jugar PERFIL=perfiles/ejemplo.json      # partida, una decisión por año
make menu PERFIL=perfiles/ejemplo.json       # solo las cartas de este año
make comparar PERFIL=perfiles/ejemplo.json   # planes completos, lado a lado
make supuestos                               # cada parámetro con su fuente
make validar                                 # cohorte simulada contra ESI y EPS
```

Desde `backend/`, con todas las opciones:

```bash
uv run python -m app.cli jugar --perfil perfiles/ejemplo.json --seed 7 --ahorros 20000000
uv run python -m app.cli menu --perfil perfiles/ejemplo.json --todas     # todas las decisiones, no solo las cartas
uv run python -m app.cli comparar --perfil perfiles/ejemplo.json --anios 15 \
    --plan "sin cambios=seguir" --plan "magíster=magister" --plan "emprender a los 31=seguir*3,emprender"
uv run python -m app.cli ocupaciones --perfil perfiles/ejemplo.json      # a qué ocupaciones pasa la gente de la tuya
```

Los perfiles personales van en `backend/perfiles/` y están en `.gitignore` (el repo es público); solo se versiona `ejemplo.json`, que es ficticio. Si el perfil no trae ahorros, ocupación o Big Five, el motor lo dice al partir: los ahorros parten en 0, la ocupación se toma del rubro y la personalidad queda en el promedio.

## Módulos y fuentes

| Módulo | Qué hace | Fuente |
|---|---|---|
| Despido | Riesgo anual por edad, multiplicado por antigüedad, tipo de empleador y rubro | EPS 2024 (edad, antigüedad, Estado); INE flujos laborales (pyme, grande, rubro) |
| Ofertas | Llegan sin buscar; se aceptan si superan tu sueldo de reserva. Buscar multiplica las ofertas por 1,7 | Tasa chilena: cambios voluntarios de la EPS divididos por la aceptación de la SCE. Sueldo de la oferta y umbrales: SCE (EE.UU.) |
| Búsqueda | Probabilidad de encontrar trabajo por edad, más baja tras un año cesante o tras una pausa | EPS 2024 |
| Sueldo al reemplearse | 0,117 log menos que el último, que se recupera casi entero en un año | SCE (EE.UU.) y Carranza, Prieto y Sehnbruch 2025 (Chile) |
| Ascensos | Tasa por nivel y alza de 5,8% | Baker, Gibbs y Holmstrom 1994 (una empresa de EE.UU.) |
| Sueldo en el tiempo | Perfil por edad y educación, más el reajuste real de la economía, sin el alza esperada por ascensos | ESI 2025, INE índice de remuneraciones |
| Ocupación | Al cambiar de empleador, la ocupación siguiente sale de 1,4 millones de transiciones; se traspasa 25% del sueldo relativo del nuevo grupo y se pierde la experiencia en la ocupación | JobHop (Flandes), ESI 2023-2025, Kambourov y Manovskii 2009 |
| Tipo de empleador | Pyme, grande o Estado del nuevo empleador | Panel ESI 2023-2025 |
| IA | Jóvenes de hasta 25 años en el quintil más expuesto reciben 19% menos ofertas; sin efecto para el resto | Brynjolfsson, Chandar y Chen 2025; Humlum y Vestergaard (Dinamarca) |
| Capacitación | Curso SENCE de más de 140 horas: +0,6% de sueldo, sin efecto en empleo | Comisión revisora 2011, vía BCN 2019 |
| Magíster | +7% de sueldo al titularte; dos años de arancel | DIPRES 2026; arancel de la U. de Chile |
| Emprender | Ingreso relativo al asalariado comparable con su dispersión; cierre de 31% el primer año | ESI 2023-2025, EPS 2024, Caliendo et al. 2014 |
| Familia | Pareja, separación e hijos por edad y situación de pareja; las madres pierden ingreso o salen | ELSOC, INE estadísticas vitales, EPS, COES |
| Finanzas | Gasto según la tasa de ahorro de tu tramo de ingreso, más el costo de cada hijo y el arancel | EPF IX, UNICEF y Ministerio de la Mujer 2025 |
| Bienestar | Satisfacción con la vida y salud por edad; efecto del ingreso, la cesantía, el reempleo, la pareja y la separación; síntomas depresivos según horas; tiempo con tu gente según horas | ELSOC, ENUT 2023 |
| Gente como tú | Cada carta dice qué fracción de la gente de tu edad toma esa decisión al año | EPS, ESI, ELSOC, SCE |

## Cómo se juega un año

1. El juego reparte dos o tres cartas (`hand.py`): "seguir", la oferta del año si llega una (empresa con nombre, sueldo y cambio contra lo que ganas) y decisiones posibles sorteadas con la suerte del año.
2. Por cada carta el motor corre 1.000 futuros a 5 años con la misma suerte y la compara contra "seguir": plata a todo el horizonte, satisfacción y tiempo con tu gente al cierre del año.
3. Eliges. De los 1.000 futuros de ese año, uno es el que te tocó y la partida sigue desde ahí.
4. En paralelo vive tu sombra: el mismo gemelo que nunca cambia nada, con tu misma suerte.

`POST /api/juego/turno` expone lo mismo para el frontend. No guarda estado: recibe el perfil, la semilla y las decisiones, y devuelve tu ficha, la de la sombra, lo que pasó cada año y las cartas siguientes. Los logros y el puntaje final son marcas del juego: no cambian lo que simula el modelo.

## Lo que se sacó por falta de datos

Pedir aumento (no hay dato del tamaño del aumento), postular a un ascenso, cambiarte de ocupación a voluntad, hacer redes, cuidarte, priorizar a tu gente, pitutos, bajar el ritmo, bajar pretensiones, tener un hijo a voluntad, energía, agotamiento, habilidades, reputación, contactos, intereses del ahorro y de la deuda, y la velocidad de llegada de la IA. Los hijos siguen ocurriendo con las tasas del INE y ELSOC.

## Límites que conviene decir en la demo

- Ocho parámetros vienen de EE.UU. (ofertas, umbrales, sueldo al reemplearse, ascensos, IA) y dos de Alemania (personalidad y emprendimiento). `make supuestos` los marca.
- JobHop son currículums de Flandes: sirven como patrón de movilidad entre ocupaciones.
- El sueldo relativo entre ocupaciones solo distingue los grandes grupos de la ESI.
- El modelo no tiene shocks propios al sueldo: no hay un número chileno que los separe de los cambios y despidos que ya simula. Por eso la dispersión del sueldo de quien se queda en su empleo es menor que en la ESI (`make validar` lo muestra).
- Los síntomas depresivos se sortean cada año sin persistencia: ELSOC da la incidencia, no la duración.
- El arancel del magíster es de un programa de la U. de Chile; falta un promedio nacional oficial.
- El modelo valida distribuciones, no la vida de una persona.

## Regenerar las tablas

`backend/app/sim/data/tablas.json` son tablas agregadas; los microdatos no van al repo. Los parámetros estimados están en `datos_laborales/derivados/modelo_paneles.json`, `modelo_ofertas.json` y `modelo_literatura.json`, con sus scripts en `datos_laborales/scripts/modelo/`. Con la carpeta `datos_laborales/` a mano:

```bash
make datos DATOS=../../datos_laborales
```
