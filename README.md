# Bifurca

<img src="./project-logo.png" alt="Bifurca" width="200" />

> Simula tu próxima decisión de carrera en 50 vidas paralelas, con datos reales del trabajo en Chile, antes de tomarla.

Track: Simulations · Platanus Hack 26 Santiago, team 32

Las decisiones de carrera se toman una sola vez y nunca sabes cómo te habría ido con la otra. **Bifurca** es un simulador para ensayarlas antes: vive cada opción en 50 mundos paralelos con la misma suerte en todos, así que la diferencia entre caminos es efecto de la decisión y no del azar. Te muestra en cuántos mundos gana cada opción, el rango de sueldos posible y el riesgo de cesantía, y recién ahí eliges tú.

## Cómo funciona

1. **Armas tu copia.** Nueve datos: edad, estudios, rubro, cargo, sueldo, tipo de empresa y cuánto riesgo toleras. O le pasas un prompt a tu propio Claude, que ya te conoce, y pegas lo que te responde.
2. **Llega una decisión.** Una situación concreta: te ofrecen irte a una startup, te despiden, aparece un magíster, una recesión. Cuál llega depende de cómo vas.
3. **Miras los 50 mundos.** En cada uno, tu copia vive *todas* las opciones con la misma suerte: la misma recesión, el mismo despido, el mismo ascenso. Si en un mundo gana más cambiándose, es por la decisión y no por el azar. Ves en cuántos mundos gana cada opción, el abanico de sueldos (del 10% con peor suerte al 10% con mejor) y cuántos pasaron por la cesantía. Puedes abrir cualquier mundo y leer su historia.
4. **Eliges y tiras el dado.** Vives uno solo de esos caminos. La ficha amarilla eres tú dentro del abanico de tus copias.
5. **Al final** ves tu línea contra la de tus copias, año a año, y puedes simular otra vida con el mismo perfil para ver qué cambia.

## Datos de Chile, no opiniones de una IA

Ningún modelo inventa los números. El motor ejecuta un paquete de reglas con **40 decisiones, 16 eventos, 100 parámetros y 54 tablas** sacadas de encuestas y registros chilenos (ESI y ENE del INE, EPS, entre otras) y de estudios citados. El texto que narra cada decisión no toca ninguna cifra.

Cada parámetro dice si es **dato** medido, **mixto**, **sintético** o **supuesto**, con su fuente: hoy son 28, 35, 3 y 34. La mayoría de los supuestos son del escenario de IA y de los ciclos (auge del cobre, burbuja de IA), que extrapolan estudios a Chile. `make supuestos CALIDAD=supuesto` los lista.

Y lo probamos contra la realidad: simulamos 5.000 vidas de los 18 a los 50 y las comparamos con 37 metas de Chile. **Cuadran 33**, con las semillas 0 y 1. La desocupación por edad cuadra en los seis tramos sin que el motor use ese número. Los sueldos medianos quedan a menos de 10% de Chile hasta los 44 años; a los 45-49 el motor se pasa 17%. También fallan los independientes a los 35-39 y 45-49 y el empleo público a los 35-39. Contra ELSOC, que el motor no usa, cuadran 4 de 6 transiciones: el motor despide de más a los jóvenes y saca de la cesantía demasiado rápido a los 30-44. Cualquiera lo reproduce con `make validar N=5000`. El detalle está en [`docs/motor/VALIDACION.md`](docs/motor/VALIDACION.md).

Las ofertas nombran empresas reales del catálogo como ejemplo (SII, Get on Board, Y Combinator, empleospublicos.cl), con el aviso de que sus cifras y lo que les pasa son simulados. Un despido o un cierre nunca se cuenta con el nombre de una empresa real: ahí la historia usa una ficticia, y el narrador lo valida en código.

## Stack

- `backend/`: FastAPI y un motor Monte Carlo en numpy que lee el paquete de reglas de `backend/simulador/`
- `frontend/`: Vite, React y TypeScript

## Correr local

```bash
make install
make back    # http://localhost:8000/docs
make front   # http://localhost:5173
```

¿Sin navegador? El simulador también corre en el terminal:

```bash
make jugar DUDA=unirse_a_startup   # una simulación completa, decisión por decisión
make comparar DUDA=oferta_externa  # solo las copias de una decisión
make validar                       # cuántas metas de Chile cuadran
make supuestos CALIDAD=supuesto    # qué números siguen siendo supuestos
```

Cómo funciona, de dónde salen los números y cómo agregar cosas: [docs/COMO-FUNCIONA.md](docs/COMO-FUNCIONA.md). Arquitectura y detalles del motor en [DEV.md](DEV.md). Hay un video demo con subtítulos en [`docs/demo/`](docs/demo/).

## Equipo

- José Tomás Valdivia ([@jtvaldivia](https://github.com/jtvaldivia))
- Vicente Cruz ([@vicente-cruz-labra](https://github.com/vicente-cruz-labra))
- Cristóbal Pérez-cotapos ([@cristobalperez-cotapos](https://github.com/cristobalperez-cotapos))
- Benito Palacios Medeiros ([@benitopalaciosm](https://github.com/benitopalaciosm))
- Alonso Peralta Sarrat ([@aperaltas16](https://github.com/aperaltas16))
