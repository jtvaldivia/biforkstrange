# Decisiones de diseño

Lo que decidimos a propósito y por qué. Si algo de aquí te parece raro o quieres cambiarlo, conversémoslo antes de tocar el código: cada una tiene una razón que no se ve leyendo el código.

Las palabras siguen el [glosario](GLOSARIO.md). Para agregar una decisión, súmala al final con el número que sigue. Si una deja de valer, no la borres: márcala como reemplazada y di por cuál.

## 1. Los números salen de los datos; la IA hace todo lo demás

Ninguna probabilidad ni efecto de la simulación sale de un LLM: los pone el motor con el paquete de datos. Fuera de eso, la IA no tiene límite fijo. Hoy lee el texto de la persona para llenar su perfil. Puede contar cada decisión con la historia de la persona, hacerle preguntas para conocerla, traducir su duda a una decisión del banco o buscar fuentes nuevas para los datos.

**Por qué.** El valor del juego es que los números tienen respaldo. Si un LLM pone uno, ya no podemos decir de dónde sale, y dos partidas iguales podrían dar números distintos.

## 2. Los números viven en el paquete, con su fuente

Toda probabilidad y todo efecto está en `backend/simulador/` como parámetro con fuente y calidad. El código no tiene números escritos a mano. La excepción son los pesos de población de `politicas.py` y los valores por defecto de `perfil.py`, y están marcados.

**Por qué.** Así cualquiera puede responder "¿de dónde sale este número?" con `make supuestos`, y cambiar un número no exige tocar código. Un número sin fuente se puede usar, pero va marcado como supuesto.

## 3. En un mismo mundo, lo del país es igual para todas las vidas y lo de la pega va con el trabajo

Todo lo que decide el azar se identifica por mundo, año y sitio. La recesión es igual para todas las vidas de un mundo: si en el mundo 37 hay recesión el año 3, la hay en todas. Lo de la pega (ascenso, despido, oferta, alza) se comparte mientras las vidas están en el mismo trabajo; cuando una se cambia, su suerte en la pega pasa a ser otra (`SUERTE_POR_PEGA` en `motor.py`).

**Lo que descartamos.**
- Compartir todo, como era antes: las dos vidas ascendían el mismo año aunque trabajaran en empresas distintas. Con Tomás pasaba en 17 de 40 mundos, y la historia de cada mundo se veía artificial.
- Que todo sea al azar: si pides aumento y no te lo dan, sigues en la misma pega, pero las dos vidas ascenderían en años distintos por pura casualidad, y el juego mostraría como resultado de la decisión algo que es ruido.

**Por qué.** Así la suerte solo se separa cuando la decisión separa los caminos. Con Tomás, irse a la startup pasó de ganar en 0 a ganar en 28 de 100 mundos: en la startup puede tener mejor suerte que en su pega. El sueldo típico de cada opción casi no cambió, y el ruido entre semillas subió poco (de ±1,8 a ±2,4 mundos), así que 100 mundos siguen bastando.

## 4. La copia toma solo la decisión que se compara; lo demás lo responde como la gente real

En cada mundo, la copia toma la opción que se compara y después vive con la misma regla que la persona (decisión 13): le llegan propuestas, tiene años tranquilos y a veces busca algo. Todo lo que no es la decisión que se compara lo responde con los pesos de la población, ajustados a tu historia: si tu CV muestra que te cambias seguido de pega, tu copia acepta más ofertas (`pesos_personales` en `politicas.py`).

**Lo que descartamos.** Que la copia decida todo al azar, o que juegue como la persona. Con el azar, el resultado depende de decisiones que nadie tomó; jugar como la persona no se puede, porque todavía no ha elegido.

**Por qué.** Así se mide el efecto de una decisión: lo demás es lo que haría la gente real, no lo que haría la persona. Antes la copia quedaba quieta después de la decisión, y eso hacía que quedarse pareciera más estable de lo que es.

## 5. 100 mundos

Antes eran 500. Bajamos a 100.

**Por qué.** "Gana en 54 de 100 mundos" se lee sin hacer cuentas, y cada mundo cabe como un punto que se puede tocar para ver qué le pasó. Responde más rápido. El costo es precisión: con 100, una diferencia de menos de unos 10 mundos entre opciones puede ser ruido. No hay que presentar diferencias chicas como si fueran claras.

## 6. Tú eres el mundo 101

La partida de la persona es un mundo más, aparte de los 100.

**Por qué.** Los 100 mundos son para mirar antes de decidir. Si la persona viviera uno de ellos, sabría lo que le va a pasar.

## 7. Se compara por la medida final, no por un puntaje

El ganador de cada mundo es la opción con mayor sueldo al año 10. También se muestran el cargo, los meses sin trabajo y el estado. No hay un puntaje de felicidad, y el ánimo y la energía no se muestran.

**Por qué.** El sueldo y los meses sin trabajo tienen datos detrás; un puntaje de felicidad no. El ánimo y la energía existen en el modelo, pero casi no cambian entre opciones de trabajo, así que mostrarlos haría creer que medimos algo que no medimos.

## 8. No es para maximizar

El juego no premia elegir la opción que gana más seguido, y no lo vamos a cambiar.

**Por qué.** Sirve para ver el abanico de lo que le pasa a gente como tú antes de una decisión real. La opción que gana más plata puede ser también la más riesgosa, y a la persona le pueden importar otras cosas. Si el juego empuja a maximizar, deja de servir para pensar.

## 9. Solo lo laboral

Lo de la vida personal (hijos, pareja, vivienda, cuidado de un familiar, duelos, herencias y la carta de cuánto ahorras) se sacó del paquete. Solo queda el cáncer: está en el paquete, pero apagado en el juego (`EVENTOS_PERSONALES` en `motor.py`).

**Por qué.** Mezclar "¿me cambio de pega?" con "te diagnostican cáncer" distrae de la duda de trabajo y toca temas que no queremos tratar a la ligera en un juego. Lo personal ya estaba apagado y no movía lo que se compara, así que mantenerlo solo sumaba variables, parámetros y fuentes que nadie usaba.

## 10. La primera decisión también sale al azar

La partida parte con una decisión al azar, como las demás. Elegir la primera duda sigue siendo posible, pero es opcional.

**Por qué.** Así todas las decisiones funcionan igual, y cada una puede decir por qué te tocó y con qué probabilidad.

## 11. Empresas reales solo como ejemplo

Las empresas reales (SII, Get on Board, Y Combinator, empleospublicos.cl) aparecen como ejemplo al lado de una opción. La historia de cada decisión usa empresas ficticias.

**Por qué.** La simulación trabaja con rubro, tamaño y tipo de empleador, no con empresas. Si la historia usara una empresa real, el juego inventaría hechos sobre ella ("la startup cierra").

## 12. La partida no se guarda

El servidor no guarda partidas. Cada llamada trae el perfil, la semilla y las opciones elegidas, y la partida se vuelve a jugar entera. Con la misma semilla sale igual.

**Por qué.** No hay base de datos que mantener ni partidas que se desincronicen, y cualquier partida se puede repetir para revisar un error. Si algún día hay que guardar partidas, se guardan esos datos de entrada, no el resultado.

## 13. No todos los años hay que decidir

Cada año, para la persona y para sus copias:

1. Si la vida obliga (un despido), se decide eso.
2. Si no, a veces llega una propuesta sin buscarla (`LLEGAN` en `motor.py`: una oferta, una startup, una jefatura).
3. Si no llega nada, es un año tranquilo. El juego le hace una sola sugerencia: la decisión que el motor sorteó con los ponderadores del paquete, acompañada de la estadística oficial de qué tan seguido la gente hace eso (la evidencia con uso "frecuencia"; si no hay, la primera cifra de su evidencia). La persona la mira o sigue igual, y puede abrir la lista completa si quiere hacer otra cosa. La copia considera esa misma sugerencia y la responde como la gente real (casi siempre, nada).

**Lo que descartamos.** Que cada año salga una decisión sí o sí, como era antes. Te obligaba a decidir aunque no te pasara nada, y una decisión rara salía siempre que fuera la única que calzaba.

**Por qué.** Es más realista: la mayoría de los años no pasa nada grande. Es más entretenido: las decisiones pesan más si no son constantes, y buscar algo por tu cuenta da control. Y la persona y las copias siguen la misma regla, así que compararlos es justo.

**Pendiente.** Qué tan seguido llega una propuesta sale de los pesos relativos del paquete, no de una probabilidad anual medida. Para las ofertas hay dato (EPS, NY Fed); para el resto, convertir los pesos en probabilidades anuales es trabajo de los frentes de Cris y Valdi.
