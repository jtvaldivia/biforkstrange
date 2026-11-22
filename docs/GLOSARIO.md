# Glosario

Las palabras del juego y qué significa cada una. Úsalas siempre igual: en el código, en la UI, en los PRs y al conversar. Si una palabra nueva no calza con ninguna de estas, agrégala aquí antes de usarla.

Al lado de cada término van las palabras que no usamos para eso (_No usar_), porque confunden.

## La persona y su partida

**Persona**:
Quien juega. En la UI se le habla de tú.
_No usar_: usuario, jugador

**Perfil**:
Quién es la persona hoy. Nueve datos básicos (edad, sexo, estudios, carrera, rubro, tipo de empleador, nivel, sueldo y tolerancia al riesgo) y, si da su CV, su situación (remoto, media jornada, usa IA, buscando) y su historia (cada cuántos años se cambia de pega).
_No usar_: formulario, ficha

**Partida**:
Los 10 años que vive la persona, decisión por decisión. Queda definida por el perfil, la semilla y las opciones que eligió.
_No usar_: sesión, juego (para una partida en particular)

**Semilla**:
El número que fija los 100 mundos y el tuyo. Con la misma semilla, la partida sale igual.

**Cierre**:
La pantalla final: la vida de la persona comparada con los 100 mundos.

## Los mundos

**Mundo**:
La unidad del juego. Es todo lo que le pasa a la persona, año a año, sin que dependa de ella: alzas, ascensos, despidos, ofertas, recesiones, y qué resultado le toca al elegir. No hay otra palabra para esto: se dice desde el mundo ("en este mundo hay recesión el año 8"). Hay 100 mundos para mirar y uno más, el de la persona (el 101), que es el único que se vive. Todo se cuenta en mundos: "gana en 54 de 100 mundos".
_No usar_: simulación, escenario, universo, "100 copias", suerte, dado, sorteo

**Copia**:
La persona dentro de un mundo. Sirve para contar ("en este mundo, tu copia se cambió"), nunca para contar cuántas hay: hay una copia por mundo.
_No usar_: gemelo, clon, avatar. En el código, `gemelo`, `N_GEMELOS` y `gemelos.py` siguen con el nombre viejo: es solo el identificador, en lo que lee una persona se dice "copia".

**Vida**:
Los 10 años de una copia en un mundo con una opción. Todas las vidas de un mundo viven la misma recesión el mismo año. Lo de la pega (ascenso, despido, oferta) lo comparten mientras siguen en el mismo trabajo; si una se cambia, tiene su propia suerte en la pega nueva. En cada mundo hay una vida por cada opción de la decisión.
_No usar_: trayectoria, rama

**Ganador del mundo**:
La opción con la que la copia termina ganando más al año 10 en ese mundo. Si las dos mejores quedan a menos de 0,5%, el mundo es **empate**.

**Ritmo de la IA**:
Qué tan rápido avanza la IA en un mundo: lenta, a ritmo medio o rápida. Cada mundo trae uno, igual para todas sus vidas, como la recesión. Sale con las probabilidades que economistas y superforecasters dieron a cada escenario al 2030 (FRI 2026, `P_RITMO_IA`). Solo existe con la incertidumbre de IA prendida.
_No usar_: escenario de IA (en el código, `escenario_ia` sigue con el nombre viejo), régimen, velocidad

**Cómo te toca la IA**:
Si la IA automatiza tu ocupación, la complementa, no se sabe (incógnita) o no la toca, según la OIT (2025). En el código, `ia_tipo`.

**Adaptabilidad**:
Qué tan bien te recuperas si la IA te saca de tu pega (0 a 1): edad, estudios, Santiago o región, ahorro y si ya usas IA (Manning y Aguirre 2026).

## Lo que le toca decidir

**Decisión**:
Una pregunta de trabajo con sus opciones: "Otra empresa te ofrece trabajo. ¿Te cambias?". Cada año le llega una a la persona. Viven en `decisiones.json`, que es el banco.
_No usar_: carta, pregunta (es solo el texto de la decisión), escenario. En el código y en el paquete todavía aparece "carta"; se va reemplazando.

**Por qué te toca**:
Cómo llega una decisión un año:
- **obligada**: la vida obliga a decidir (te despidieron, tienes que buscar);
- **te llega**: una propuesta que no buscaste (una oferta, una startup que te llama, que te ofrezcan ser jefe);
- **la buscas tú**: en un año tranquilo, eliges moverte (pedir aumento, estudiar, emprender);
- **consecuencia**: la trae una opción que elegiste antes.

En el paquete se llaman `forzada`, `carta` y `luego`. Cuáles "llegan" y cuáles "se buscan" está en `LLEGAN` de `motor.py`. El paquete es un formato compartido, así que no se renombra.

**Año tranquilo**:
Un año en que no te llegó ninguna propuesta. No te obliga a decidir: puedes seguir igual o buscar algo tú. A tu copia le pasa lo mismo, y busca con la frecuencia de la gente real.
_No usar_: año vacío, año sin carta

**Peso**:
Qué tan seguido sale una decisión al azar frente a las otras. Sale de qué tan seguido le pasa eso a gente como la persona.

**Duda**:
La pregunta real que trae la persona de su vida ("¿me estoy especializando demasiado?"). Si se parece a una decisión del banco, puede ser su primera decisión, en vez de una al azar. Es opcional.

**Opción**:
Una de las respuestas posibles a una decisión: "Cambiarte", "Usarla para negociar", "Quedarte".

**Resultado**:
Lo que puede pasar al elegir una opción, con su probabilidad: "El cambio te sube el sueldo (54 de 100)". Una opción tiene uno o más resultados.
Tú eliges la opción, y te puede tocar cualquiera de sus resultados, según su probabilidad.
_No usar_: outcome, consecuencia, alternativa (se confunde con opción)

**Efecto**:
El cambio que un resultado o un evento le hace a la copia: el sueldo se multiplica por 1,1, la antigüedad vuelve a 0. Puede durar unos años y revertirse.

**Evento**:
Algo que pasa solo, sin que nadie decida: alza anual, ascenso, despido, una oferta que llega. Un **evento del mundo** (hoy, la recesión) le pasa a todas las vidas de ese mundo a la vez.
_No usar_: suceso (en la UI sí se dice "lo que pasó")

**Población**:
Cómo responde la gente real a cada decisión: ante una oferta, 34% se cambia, 9% negocia y 57% se queda. En cada mundo, la copia responde así a todo lo que no es la decisión que se compara, ajustado a la historia de la persona: si se cambia seguido de pega, acepta más ofertas.
_No usar_: IA de la copia, bot

**Medida final**:
Lo que se compara al año 10: sueldo, cargo, meses sin trabajo y estado (empleado, cesante, independiente). Si alguien propone "agregar outcomes", casi siempre se refiere a una medida final nueva.
_No usar_: outcome, KPI, puntaje

## Los números

**Paquete de datos**:
La carpeta `backend/simulador/`: decisiones, eventos, parámetros, tablas y fuentes. Todo número del juego sale de ahí.
_No usar_: banco de preguntas (es solo una parte), base de datos

**Parámetro**:
Un número del modelo con nombre, unidad, fuente, calidad y rango: `P_SUBE_CAMBIO = 0,54`.

**Fuente**:
De dónde sale un parámetro: cita, enlace y país. "Banco Central de Chile, IPoM diciembre 2018."

**Calidad**:
Qué tan respaldado está un número:
- **dato**: medido en Chile o leído en la fuente original;
- **mixto**: dato de otro país, o dato chileno con un ajuste nuestro;
- **supuesto**: sin fuente, lo puso el equipo.

**Validación**:
Simular 5.000 personas y revisar si reproducen las metas de Chile (desempleo, sueldos por edad, cambios de trabajo). Se corre con `make validar`.
