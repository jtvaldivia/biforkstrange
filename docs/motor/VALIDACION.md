# El motor frente a Chile (M6)

Reproducir, desde `backend/`: `python -m app.sim.motor.validacion [n] [semilla]` (5.000 personas, 10 a 12 segundos). Tests: `pytest tests/test_motor_validacion.py` (7 segundos).

## Resumen

1. **25 de 37 metas cuadran** (26 con otra semilla). Antes de calibrar cuadraban 18 (19 y 16 con otras semillas).
2. **Las 7 metas que se ganaron son todas de conducta calibrada**: educación, independientes y cambio de empleador. Calibrar no mejoró ninguna meta que el motor no use: ahí eran 9 de 18 y siguen siendo 9 de 18.
3. **Lo que valida de verdad: la desocupación por edad cuadra en los seis tramos** (error máximo 1,8 puntos). El motor no usa ese número; sale de los despidos y de la duración de la cesantía.
4. **Lo que no cuadra son los sueldos: 9 de 12 fallan.** El sueldo mediano simulado queda 12% a 32% bajo Chile y la brecha crece con la edad. No es un problema de pesos: son tres reglas del paquete y un error del motor (ver "Qué no cuadra").
5. Además fallan el empleo público a los 35-39 y el cambio de empleador a los 45-59, los dos por reglas del paquete.
6. Contra ELSOC, que no es insumo: 5 de 6 filas comparables cuadraban; desde los arreglos del punto 8, 6 de 6. La salida de la cesantía a los 30-44 sigue alta (el motor devuelve al empleo a 67% al año; ELSOC, entre 49% y 60%), pero entra en la tolerancia de 8 puntos.
7. **Empresas, cargos y escenario de IA (22 de noviembre de 2026).** Con el catálogo de empresas (`empresas_catalogo.csv`), los cargos y el escenario de IA sorteado por gemelo cuadran 24 de 37 metas con la semilla 0, contra 25 sin ellos. Solo cambia de estado la de asalariados públicos a los 45-49: queda en 10,1%, que ya estaba documentada como al borde. Ese cambio no viene del sueldo: con el multiplicador de sueldo en 1 sale igual. El multiplicador de sueldo de cada empresa se normaliza con media geométrica 1, porque las metas son medianas. Con media aritmética 1, los sueldos medianos bajaban entre 2% y 3,5%. Con media geométrica quedan a menos de 2% de los de antes.
8. **Arreglos del motor (rama `fix/motor-bugs`).** `cesantia/rapido` ya no sube con los meses que lleva buscando (sumaba hasta +0,3; `MESES_CESANTIA` supone una salida constante). Con eso la salida de la cesantía a los 30-44 baja de 68,6% a 67,1% (semilla 1: 68,0% a 66,5%) y entra en la tolerancia: ELSOC cuadra 6 de 6. Las metas quedan en 24 de 37 con 5.000 personas y semillas 0 y 1, antes y después. Los demás arreglos de la rama (duda con forzadas, bootcamp encadenado, estudiante sin carrera, primer empleo, nivel al titularse, emigrar solo con trabajo) mueven las metas menos de un punto.

8. **El alza anual ya no baja el sueldo (22 de noviembre de 2026).** El alza de quien sigue en su pega tenía ruido que podía dejarla negativa: en 3 de cada 10 años en la misma pega, el sueldo bajaba. Ahora el piso del alza es cero (`alza_anual` en `eventos.json`). Con la semilla 0 cuadran 31 de 37 metas, contra 24: los seis sueldos medianos, de los 18 a los 49 años, quedan a menos de 13% de Chile, y el 25% más alto a los 45-49 también cuadra. Siguen fallando el 25% más bajo a los 25-29 y a los 35-39 (los independientes), el empleo público y el cambio de empleador. La tabla de abajo es de antes de este cambio.

9. **Decisiones del modelo (rama `fix/modelo-decisiones`).** Cuatro reglas que decidió el equipo, una por commit. Metas con 5.000 personas, semillas 0 y 1:

   | Cambio | Metas (s0 / s1) | ELSOC (s0 / s1) | Sueldo mediano 30-34 / 45-49 (s0) |
   |---|---|---|---|
   | Antes | 33 / 31 | 5 / 5 | 708 / 807 mil (−3% / +3%) |
   | 1. El alza anual descuenta el ascenso promedio (`ASCENSO_POBLACION`), no el tuyo | 33 / 31 | 5 / 5 | 707 / 805 mil (−3% / +3%) |
   | 2. El fundador que ya tenía empresa parte de su sueldo declarado (`base_empresa`) | 33 / 31 | 5 / 5 | igual (la cohorte parte a los 18: nadie trae empresa) |
   | 3. El independiente recibe el alza de la cuenta propia de su edad (`alza_independiente`) | 33 / 32 | 5 / 5 | 712 / 808 mil (−2% / +4%) |

   ELSOC 5 de 6 no es nuevo: la salida de la cesantía a los 30-44 da 69,1% y 67,8% contra un techo de 67,7% (59,7 + 8), igual que antes de estos cambios.

   - **1.** En promedio el alza no cambia (el descuento promedio es el mismo), así que los sueldos de la cohorte se mueven menos de 1% y ninguna meta cambia. Lo que cambia es quién gana: con los mismos dados, el sueldo final medio con oficio 80 queda 2,0% sobre el de oficio 30 a 10 años (antes, 0,8%, y solo porque el piso de cero del alza corta la resta). `ASCENSO_POBLACION` es la `prob_ascenso` promedio de los años de empleado de esta cohorte por tramo de edad (0,045 a 0,061); `tests/test_motor_validacion.py` revisa que siga siendo el promedio.
   - **2.** La validación da exactamente lo mismo: en la cohorte nadie parte con empresa y quien emprende sigue ganando según `MICRO_MEDIANA`. En el juego, un fundador con 2 años de empresa que declara 1,4 millones ganaba ~690 mil el primer año (mediana de 400 gemelos) y uno con 3 años que declara 4 millones, ~830 mil; ahora 1,40 y 4,00 millones, y desde ahí crecen con la regla de siempre (× (1 + años de empresa / 4), con la misma suerte del año).
   - **3.** Nuevo evento `alza_independiente`: cada año el ingreso por cuenta propia se multiplica por `1 + crecimiento_cuenta_propia`, la mediana de cuenta propia de la banda de edad siguiente sobre la actual en `esi_ingreso_categoria_formalidad` (ESI 2025; formal o informal según `formal`), anualizada y acotada a ±6%. Es la misma lectura del corte transversal que hace `crecimiento_esi` para los asalariados. Crece menos que el asalariado y a veces cae: formal +3,8%, +5,5%, −1,2%, +4,9%, −2,7% y 0% por banda desde los 18-24; informal +6% (tope) a los 18-24 y 0% después, porque su mediana queda en 300 mil. Los sueldos medianos de la cohorte se mueven entre −0,5% y +2,7%, y con la semilla 1 entra el 25% más bajo a los 35-39 (de −16% a −14%). En el juego, un independiente formal de 30 años con 700 mil termina en 838 mil a los 10 años (antes, 700 mil) y uno de 40 años, en 612 mil.

## Cómo se midió

5.000 personas, mitad hombres y mitad mujeres, desde los 18 años (`Perfil.a_los_18`) hasta los 50, decidiendo como la población (`Poblacion`), solo lo laboral. Las 3 metas del grupo "Vida" quedan fuera: quedan 37.

- Un año-persona es un año vivido. Su edad es la que la persona tenía al empezarlo; su estado, sueldo y empleador son los del cierre.
- El tipo de empleador solo se lee en años cerrados como empleado. El motor no lo borra cuando alguien se independiza.
- Despidos y cambios se dividen por los años en que la persona estaba empleada al momento de sortear los eventos.
- "Cambio de empleador" es la definición de la EPS: pasar a otro empleador sin cesantía entremedio. No cuenta al despedido que encuentra trabajo en el mismo año.
- La cohorte llega a los 50, así que las metas 45-59 se miden con 45-49.
- Las 37 metas se pudieron medir. Ninguna vida terminó con error después de calibrar (una de 5.000 antes; ver "Problemas encontrados").

Cada meta lleva una etiqueta:

| Etiqueta | Qué significa | Metas | Cuadran |
|---|---|---|---|
| validación | El motor no usa ese número | 6 | 6 |
| parcial | El motor usa la misma encuesta para otra cosa (el primer sueldo y su alza salen del perfil ESI) | 12 | 3 |
| calibrada | Los pesos de `politicas.py` se ajustaron contra ella | 10 | 8 o 9 |
| insumo | El motor lee ese mismo número. Reproducirlo no valida nada | 9 | 8 |

## La tabla completa

"Antes" y "Simulado" son con semilla 0. "Al borde" significa que cuadra con una semilla y no con la otra.

| Meta | Chile | Antes | Simulado | Semilla 1 | ¿Cuadra? | Qué es |
|---|---|---|---|---|---|---|
| Ingreso mediano de ocupados, 18-24 | 548.572 | 413.974 | 448.204 | 439.969 | **No** | parcial |
| Ingreso mediano de ocupados, 25-29 | 650.000 | 557.347 | 574.319 | 560.776 | Sí | parcial |
| Ingreso mediano de ocupados, 30-34 | 728.106 | 545.187 | 566.142 | 563.684 | **No** | parcial |
| Ingreso mediano de ocupados, 35-39 | 760.000 | 542.312 | 564.288 | 560.130 | **No** | parcial |
| Ingreso mediano de ocupados, 40-44 | 797.924 | 538.347 | 559.802 | 552.627 | **No** | parcial |
| Ingreso mediano de ocupados, 45-49 | 780.000 | 513.452 | 530.481 | 534.102 | **No** | parcial |
| Ingreso del 25% más bajo, 25-29 | 500.000 | 300.127 | 342.318 | 335.967 | **No** | parcial |
| Ingreso del 25% más alto, 25-29 | 980.414 | 949.466 | 926.454 | 927.957 | Sí | parcial |
| Ingreso del 25% más bajo, 35-39 | 527.627 | 300.127 | 300.127 | 300.127 | **No** | parcial |
| Ingreso del 25% más alto, 35-39 | 1.200.000 | 1.086.728 | 1.043.616 | 1.057.996 | Sí | parcial |
| Ingreso del 25% más bajo, 45-49 | 518.651 | 300.000 | 300.127 | 300.127 | **No** | parcial |
| Ingreso del 25% más alto, 45-49 | 1.400.000 | 1.067.553 | 997.771 | 1.043.703 | **No** | parcial |
| Desocupación, 18-24 | 21,9% | 24,5% | 21,8% | 22,0% | Sí | validación |
| Desocupación, 25-29 | 11,8% | 12,0% | 11,6% | 12,2% | Sí | validación |
| Desocupación, 30-34 | 7,5% | 6,7% | 5,7% | 6,1% | Sí | validación |
| Desocupación, 35-39 | 6,8% | 6,2% | 5,7% | 5,7% | Sí | validación |
| Desocupación, 40-44 | 5,8% | 6,3% | 5,7% | 5,8% | Sí | validación |
| Desocupación, 45-49 | 6,0% | 6,4% | 5,5% | 5,6% | Sí | validación |
| Asalariados públicos entre ocupados, 25-29 | 12,8% | 10,2% | 11,8% | 12,0% | Sí | calibrada |
| Empleadores y cuenta propia entre ocupados, 25-29 | 13,3% | 21,8% | 14,1% | 13,7% | Sí | calibrada |
| Asalariados públicos entre ocupados, 35-39 | 16,7% | 10,2% | 10,9% | 11,0% | **No** | calibrada |
| Empleadores y cuenta propia entre ocupados, 35-39 | 18,7% | 22,4% | 20,2% | 19,4% | Sí | calibrada |
| Asalariados públicos entre ocupados, 45-49 | 13,3% | 9,6% | 10,1% | 10,8% | Al borde | calibrada |
| Empleadores y cuenta propia entre ocupados, 45-49 | 23,9% | 23,5% | 24,6% | 23,1% | Sí | calibrada |
| Asalariados privados en empresas de 200 o más personas | 39,9% | 40,4% | 40,6% | 41,0% | Sí | insumo |
| Años trabajando en una startup, entre años de asalariado | 1,0% | 1,0% | 1,2% | 1,1% | Sí | insumo |
| Nivel media a los 30-34 | 50,0% | 40,9% | 50,2% | 50,3% | Sí | calibrada |
| Nivel universitaria a los 30-34 | 31,5% | 36,4% | 31,1% | 31,2% | Sí | calibrada |
| Nivel técnica a los 30-34 | 16,4% | 22,0% | 16,8% | 16,6% | Sí | calibrada |
| Nivel postgrado a los 30-34 | 2,1% | 0,7% | 1,9% | 1,9% | Sí | calibrada |
| Despido o fin de contrato al año, 18-29 | 14,3% | 14,5% | 14,4% | 14,6% | Sí | insumo |
| Despido o fin de contrato al año, 30-44 | 6,6% | 6,5% | 6,5% | 6,3% | Sí | insumo |
| Despido o fin de contrato al año, 45-59 | 5,0% | 4,7% | 4,7% | 4,9% | Sí | insumo |
| Cambio de empleador al año, 18-29 | 21,8% | 26,5% | 20,2% | 20,2% | Sí | insumo |
| Cambio de empleador al año, 30-44 | 13,8% | 21,0% | 15,8% | 15,9% | Sí | insumo |
| Cambio de empleador al año, 45-59 | 10,2% | 18,5% | 14,0% | 14,2% | **No** | insumo |
| Sigue sin pega un año después de quedar cesante | 34,0% | 32,3% | 32,9% | 34,0% | Sí | insumo |

Tolerancia: 15% del valor en los sueldos, 3 puntos en el resto (1 punto en startups).

### ELSOC (no es insumo del motor)

Matriz anual: dónde está la persona un año y dónde al siguiente. Valores en %.

| Transición | Tramo | ELSOC | Simulado | Semilla 1 | ¿Cuadra? |
|---|---|---|---|---|---|
| Ocupado → cesante | 18-29 | 4,2 | 6,5 | 6,9 | Sí |
| | 30-44 | 3,3 | 4,0 | 4,1 | Sí |
| | 45-59 | 3,0 | 3,7 | 3,8 | Sí |
| Cesante → ocupado | 18-29 | 60,7 a 77,4 | 68,7 | 68,8 | Sí |
| | 30-44 | 49,4 a 59,7 | 69,2 | 67,8 | **No** |
| | 45-59 | 56,4 a 69,2 | 64,0 | 65,2 | Sí |
| Ocupado → no ocupado (no cuenta) | 18-29 | 12,8 | 6,5 | 6,9 | Fuera de alcance |
| | 30-44 | 8,0 | 4,0 | 4,1 | Fuera de alcance |
| | 45-59 | 8,2 | 3,7 | 3,8 | Fuera de alcance |

Qué comparación es justa:

- **Ocupado → cesante.** Es lo que el motor modela. Tolerancia 3 puntos. El motor queda sobre ELSOC en los tres tramos (+0,7 a +2,7): manda a la cesantía a gente que en la realidad se va a la inactividad.
- **Cesante → ocupado.** En ELSOC, 17% a 22% de los cesantes pasa a inactivo; en el motor, nadie. Por eso la referencia es un rango: el dato tal cual (piso) y el dato solo entre quienes siguen activos (techo). Tolerancia 8 puntos sobre el rango, porque la fila tiene 135 a 190 casos.
- **Ocupado → no ocupado.** Se muestra y no cuenta. El motor no tiene salida a la inactividad (cuidados, salud, desaliento) porque el juego es solo laboral. Faltan 4 a 6 puntos al año: es el tamaño de lo que quedó fuera.
- **Fila de inactivos.** No se compara: los inactivos del motor son estudiantes.

## Qué cambió con la calibración

Solo cambiaron pesos de `politicas.py` y la constante de `motor.py`. Ninguna tabla, parámetro ni fórmula.

| Peso | Antes | Ahora | Contra qué meta |
|---|---|---|---|
| `salir_del_colegio.universidad` | 0,40 | 0,36 | Universitaria + postgrado a los 30-34 (33,6%); daba 37,1% |
| `salir_del_colegio.instituto` | 0,13 | 0,10 | Técnica a los 30-34 (16,4%); daba 22,0% |
| `salir_del_colegio.cft` | 0,10 | 0,07 | Ídem |
| `salir_del_colegio.trabajar` | 0,33 | 0,43 | Media a los 30-34 (50,0%); daba 40,9% |
| `magister.beca` | 0,03 | 0,08 | Postgrado a los 30-34 (2,1%); daba 0,7% |
| `magister.vespertino` | 0,07 | 0,20 | Ídem |
| `primera_pega.independiente` | 0,14 | 0,05 | Independientes a los 25-29 (13,3%); daba 21,8% |
| `cesantia.informal` | 0,14 | 0,09 | Independientes a los 25-29 y 35-39; daba 21,8% y 22,4% |
| `P_INDEPENDIENTE_BUSCA_EMPLEO` | 0,08 | 0,055 | Independientes a los 45-49 (23,9%): con menos entradas hace falta menos salida para que el grupo crezca con la edad como en Chile |
| `primera_pega.estado` | 0,08 | 0,12 | Públicos a los 25-29 (12,8%); daba 10,2% |
| `primera_pega.grande` / `pyme` | 0,30 / 0,44 | 0,32 / 0,47 | Reparto de lo que liberó `independiente`, manteniendo la proporción entre ambos (empresa grande: 40,6%, meta 39,9%) |
| `cesantia.rapido` / `nivel` | 0,45 / 0,38 | 0,48 / 0,40 | Reparto de lo que liberó `informal`, manteniendo la proporción entre ambos |
| `oferta_externa.cambiar` | 0,45 | 0,34 | Cambio de empleador 18-29 y 30-44 (21,8% y 13,8%); daba 26,5% y 21,0% |
| `oferta_externa.contraoferta` | 0,12 | 0,09 | Ídem, misma proporción |

No se tocaron `seguir_o_desertar` (la educación cuadró sin moverlo), `independizarse` ni ningún otro peso.

Resultado por grupo, semilla 0:

| | Antes | Después |
|---|---|---|
| Educación (4) | 1 | 4 |
| Independientes (3) | 1 | 3 |
| Cambio de empleador (3) | 0 | 2 |
| Públicos (3) | 1 | 1 |
| Desocupación (6) | 6 | 6 |
| Sueldos (12) | 3 | 3 |
| Resto, insumos (6) | 6 | 6 |
| **Total** | **18** | **25** |

Con una segunda y una tercera semilla: 19 → 26 y 16 → 25. Las metas que cambian entre semillas son `publico_45-49` y, antes de calibrar, `desocupacion_18-24` y `publico_25-29`.

Efecto no buscado: al corregir la educación (había 9 puntos de más con estudios superiores) el sueldo mediano no subió. La cohorte anterior estaba mejor educada que Chile y eso tapaba parte de la brecha de sueldos.

## Qué no cuadra y por qué

### Sueldos (9 metas)

El sueldo mediano simulado va de 448 mil (18-24) a 530 mil (45-49). En Chile sube de 549 mil a 780 mil. Tres grupos explican la brecha:

- **Asalariados sin estudios superiores (la mitad de la cohorte).** Aun sin contar los sueldos cero, su sueldo mediano va de 436 mil (18-24) a 389 mil (45-49): baja con la edad. En la ESI sube de 493 mil a 600 mil.
- **Independientes (14% a 25% de los ocupados).** La mitad gana 300 mil o menos, y cada uno gana lo mismo toda la vida.
- **Empleados con sueldo cero.** 2% de los años de empleado antes de los 30 y 6% después.

Causas, con lo que mueve cada una (semilla 0, 5.000 personas; pruebas hechas fuera del repo, sin tocar el motor ni el paquete):

| Si se cambia | Tipo | Sueldo mediano 30-34 | 45-49 | Metas que cuadran |
|---|---|---|---|---|
| Nada (motor de hoy, con sueldos cero) | | 566 mil | 530 mil | 25 |
| Se corrige el sueldo cero | Regla del motor | 597 mil | 589 mil | 25 |
| Sueldo cero corregido y quien no estudió recibe el alza de la ESI desde el primer año | Regla del paquete | 637 mil | 619 mil | 27 |
| Sueldo cero corregido y la cesantía no baja el sueldo de referencia (`CAIDA_REEMPLEO` = 0) | Regla del paquete | 646 mil | 643 mil | 27 |
| Las tres cosas, y nadie acepta "lo primero que salga" | | 703 mil | 708 mil | 31 |
| Chile | | 728 mil | 780 mil | |

1. **Regla del motor: empleados con sueldo cero.** Quien parte como independiente o fundador sin haber sido empleado tiene `sueldo_ref` = 0. Cuando vuelve a buscar trabajo (la salida de 5,5% al año que agrega el motor, o el cierre de su empresa) y encuentra, la regla del paquete le paga `sueldo_ref` por un factor: cero, y las alzas multiplican cero. Le pasa a 7% de las vidas. Antes de calibrar era peor (hasta 18% de los años de empleado a los 45-49), porque había más independientes jóvenes.
2. **Regla del paquete: sin carrera no hay alza los primeros 4 años.** `alza_anual` usa `crecimiento_carrera` mientras `anos_titulado < 4`. Para quien no estudió, `crecimiento_carrera` es 0. Pierden justo los años en que la ESI da 3,3% anual.
3. **Regla del paquete: la pérdida por cesantía se cuenta dos veces.** El alza anual sale del perfil ESI por edad, que ya es el promedio de todos, incluidos los que pasaron por cesantías. Encima, cada cesantía baja el sueldo de referencia 15% (`CAIDA_REEMPLEO`) y "lo primero que salga" otro 16% en promedio, para siempre. Con 14% de despidos al año antes de los 30, el sueldo de quien no estudió termina cayendo.
4. **Regla del paquete: el ingreso del independiente es un solo número.** Entra con la mediana de cuenta propia de su tramo de edad (200 mil a los 18-24, 300 mil informal), sin dispersión. Desde la decisión 3 del punto 9 cambia con la edad como la mediana de la ESI, pero la mediana informal es 300 mil a toda edad después de los 25. En la ESI, la cuenta propia va de 200 mil (25% más bajo) a 700 mil (25% más alto). Por eso el 25% más bajo simulado es exactamente 300.127 a los 35-39 y a los 45-49: es el valor de la tabla.
5. **Los sueldos altos dejan de crecer a los 35.** El universitario mediano simulado gana 1,19 millones a los 30-34 y 1,22 a los 45-49; en la ESI, 1,10 y 1,50. Misma causa que el punto 3.

No queda ninguna meta de sueldo que se pueda arreglar con pesos sin salirse de la regla "cada peso contra la meta que mide esa conducta". El reparto entre `cesantia.rapido` y `cesantia.nivel` mueve los sueldos 5%, pero no hay ninguna meta que mida esa conducta, así que no se tocó.

### Empleo público a los 35-39 (y al borde a los 45-49)

**Regla del paquete.** Cada vez que alguien cambia de empleador o sale de la cesantía, `tipo_de_empleador` sortea de nuevo con `P_REEMPLEO_PUBLICO` = 0,12, venga de donde venga. Con una oferta cada dos años, el empleo público queda clavado en 13,5% de los asalariados a toda edad (13,7 / 13,6 / 13,4). Chile necesita 14,8% a los 25-29, 20,5% a los 35-39 y 17,5% a los 45-49. Subir el peso de postular al Estado en la primera pega solo mueve el tramo 25-29: de 0,08 a 0,15 sube 1,3 puntos ahí y 0,3 después.

### Cambio de empleador a los 45-59

**Regla del paquete y del motor.** La oferta llega por dos vías: el evento `oferta_llega` y la carta `oferta_externa`. El evento baja con la edad como en la EPS (41%, 27% y 20% de los años). La carta no: compite con las demás cartas del año, y después de los 45 quedan menos cartas, así que sale más seguido. El resultado es un perfil más plano que el de la EPS: 20,2 / 15,8 / 14,0 contra 21,8 / 13,8 / 10,2. Un solo peso de aceptar no puede cuadrar los tres tramos: se dejó el que cuadra con holgura los dos primeros (errores de −1,6 y +2,0).

### Salida de la cesantía a los 30-44 (ELSOC)

El motor devuelve al empleo a 68% o 69% de los cesantes en un año; ELSOC da entre 49% y 60%. Es la misma observación del informe del paso laboral anterior (`docs/trayectoria-v1/VALIDACION.md`): `MESES_CESANTIA` reproduce la salida de los primeros 12 meses de un episodio nuevo, pero quien parte el año cesante ya lleva tiempo y sale más lento. Regla del paquete.

### Metas que no son del todo comparables

- **Tramo 45-59** (despido y cambio): la cohorte llega a los 50. Se mide con 45-49.
- **Sigue sin pega un año después:** en pasos anuales, "un año después" es el cierre del año siguiente, entre 12 y 24 meses desde que la persona quedó cesante. Cuadra, pero es insumo.
- **Años en startup:** la meta la puso el equipo, no es una medición.
- **Inactividad:** el juego no la modela. No afecta a las 37 metas (todas son sobre ocupados o sobre la fuerza de trabajo), pero sí a cualquier número del tipo "cuánta gente trabaja".

## Problemas encontrados

Regla del motor (no se tocó; propuesta concreta):

1. **Empleado con sueldo cero.** En `_cerrar`, quien queda buscando con `sueldo_ref <= 0` debería pasar por `primera_pega` (`primer_empleo = 1`), que le pone el sueldo ESI de su edad y educación. Probado fuera del repo: los sueldos cero desaparecen y el sueldo mediano sube 5% a 11%.
2. **Una vida revienta.** Semilla 0, gemelo 4903, antes de calibrar: `ErrorExpresion: clave '' no está en MULT_DESPIDO_TIPO`. Mujer de 23 años, educación media, que partió como independiente, volvió a buscar, tomó `cesantia → bootcamp` y quedó `colocado`: el paquete la deja `empleado` sin `tipo_empleador` y el evento de despido falla. Propuesta: que `_completar_empleo` sortee `tipo_de_empleador` cuando alguien queda empleado sin tipo (o que `bootcamp.colocado` lleve `luego: tipo_de_empleador` en el paquete). Después de calibrar no apareció en tres semillas, pero el camino sigue abierto.
3. **La oferta externa llega dos veces.** Sacar `oferta_externa` del sorteo de cartas de la población y dejar solo el evento `oferta_llega`. Con eso la frecuencia de ofertas (hoy una cada dos años de empleo) y su perfil por edad dependen de un solo parámetro.
4. **Tiempo.** 5.000 personas toman 51 segundos en un proceso y 10 a 12 con ocho (lo que hace `validar` por defecto). El 42% del tiempo se va en `politicas.elecciones_internas`, que vuelve a parsear las expresiones de la opción en cada decisión (`parsear` + `nombres`); otro 19% en `Vida.opciones`, que arma las opciones de todas las decisiones en cada año (incluidas las 252 carreras), y 14% en `derivar`. Guardar por opción qué variables usa (un caché por decisión y opción) debería quitar la mayor parte de ese 42%.

Regla o dato del paquete:

5. **Alza anual sin carrera:** usar `si(y(carrera_id >= 0, anos_titulado < 4), crecimiento_carrera, crecimiento_esi)`.
6. **Pérdida por cesantía sobre un perfil que ya la incluye:** o el alza anual es la de quien no pierde el empleo (mayor que la del perfil ESI), o `CAIDA_REEMPLEO` se revierte con los años.
7. **Ingreso del independiente:** sortearlo de la distribución de la tabla (`azar_lognormal(p10, p50, p90)`). Actualizarlo por tramo de edad ya está hecho (`alza_independiente`).
8. **`P_REEMPLEO_PUBLICO`:** 0,12 parece ser la parte de los ocupados; como parte de los asalariados debería estar cerca de 0,17. Y quien ya es público no debería sortear de nuevo en cada cambio.
9. **Salto de edad:** `magister.beca` suma 1 año y `doctorado` suma 3 o 4 dentro de un solo año de juego. Esos años no se viven: no hay sueldo, eventos ni cierre. Pasa en 0,1% de los años.
10. **`emigrar` no pide estar empleado:** 0,7% de los años después de los 30 son de alguien sin empleo que figura con empleador extranjero.

Ya corregido por otro ticket mientras se hacía esta validación: quien salía del Estado a una empresa privada conservaba el rubro "Administración pública" (32% de los años de empleado después de los 30). Se volvió a correr con ese arreglo: las mismas 25 y 26 metas, y cifras que cambian en decimales.

## Qué decir en la pantalla

- "25 de 37 metas cuadran" es cierto, pero 8 de esas 25 son insumos y 8 son conductas calibradas. Las otras 9 son las 6 de desocupación y 3 de sueldos.
- La frase honesta: **"La desocupación por edad cuadra sin haberla usado (6 de 6). La educación, los independientes y los cambios de empleador cuadran porque se calibraron. Los sueldos todavía no: quedan 12% a 32% bajo Chile."**
- Los pesos son supuestos del equipo ajustados a frecuencias de encuestas. No son datos.
