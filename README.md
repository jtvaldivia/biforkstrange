# Agarra la pala

<img src="./project-logo.png" alt="Agarra la pala" width="200" />

> ¿Me cambio de pega? ¿Hago el magíster? ¿Emprendo? Que la crisis existencial la tenga tu gemelo y no tú.

Track: Simulations · Platanus Hack 26 Santiago, team 32

Las decisiones de carrera se toman una sola vez y nunca sabes cómo te habría ido con la otra. **Agarra la pala** se las pasa a tu gemelo digital: él prueba cada opción en 100 mundos distintos, con la misma suerte en todos, y recién ahí eliges tú.

## Cómo funciona

1. **Armas tu gemelo.** Nueve datos: edad, estudios, rubro, cargo, sueldo, tipo de empresa y cuánto riesgo toleras. O le pasas un prompt a tu propio Claude, que ya te conoce, y pegas lo que te responde.
2. **Llega una decisión.** Una situación concreta: te ofrecen irte a una startup, te despiden, aparece un magíster, una recesión. Cuál llega depende de cómo vas.
3. **Miras los 100 mundos.** En cada uno, tu gemelo vive *todas* las opciones con la misma suerte: la misma recesión, el mismo despido, el mismo ascenso. Si en un mundo gana más cambiándose, es por la decisión y no por el azar. Ves en cuántos mundos gana cada opción, el abanico de sueldos (del 10% con peor suerte al 10% con mejor) y cuántos pasaron por la cesantía. Puedes abrir cualquier mundo y leer su historia.
4. **Eliges y tiras el dado.** Vives uno solo de esos caminos. La ficha amarilla eres tú dentro del abanico de tus gemelos.
5. **Al final** ves tu línea contra la de tus gemelos, año a año, y puedes simular otra vida con el mismo perfil para ver qué cambia.

## Datos de Chile, no opiniones de una IA

Ningún modelo inventa los números. El motor ejecuta un paquete de reglas con **43 decisiones, 16 eventos, 67 parámetros y 50 tablas** sacadas de encuestas y registros chilenos (ESI y ENE del INE, EPS, entre otras). El texto que narra cada decisión no toca ninguna cifra.

Cada parámetro dice si es **dato** medido, **mixto** o **supuesto** nuestro, con su fuente. Y lo probamos contra la realidad: simulamos 5.000 vidas de los 18 a los 50 y las comparamos con 37 metas de Chile. **Cuadran 25.** La desocupación por edad cuadra en los seis tramos sin que el motor use ese número. Los sueldos simulados quedan 12% a 32% bajo los reales, y lo decimos. El detalle está en [`docs/motor/VALIDACION.md`](docs/motor/VALIDACION.md).

Las opciones de trabajo traen empleadores u ofertas reales como ejemplo (SII, Get on Board, Y Combinator, empleospublicos.cl), pero la historia de cada decisión usa empresas ficticias para no inventar hechos sobre empresas que existen.

## Stack

- `backend/`: FastAPI y un motor Monte Carlo en numpy que lee el paquete de reglas de `backend/simulador/`
- `frontend/`: Vite, React y TypeScript
- `supabase/`: esquema y migraciones

## Correr local

```bash
make install
make back    # http://localhost:8000/docs
make front   # http://localhost:5173
```

¿Sin navegador? El simulador también corre en el terminal:

```bash
make jugar DUDA=unirse_a_startup   # una simulación completa, decisión por decisión
make comparar DUDA=oferta_externa  # solo los gemelos de una decisión
make validar                       # cuántas metas de Chile cuadran
make supuestos CALIDAD=supuesto    # qué números siguen siendo supuestos
```

Arquitectura y detalles del motor en [DEV.md](DEV.md). Hay un video demo con subtítulos en [`docs/demo/`](docs/demo/).

## Equipo

- José Tomás Valdivia ([@jtvaldivia](https://github.com/jtvaldivia))
- Vicente Cruz ([@vicente-cruz-labra](https://github.com/vicente-cruz-labra))
- Cristóbal Pérez-cotapos ([@cristobalperez-cotapos](https://github.com/cristobalperez-cotapos))
- Benito Palacios Medeiros ([@benitopalaciosm](https://github.com/benitopalaciosm))
- Alonso Peralta Sarrat ([@aperaltas16](https://github.com/aperaltas16))
