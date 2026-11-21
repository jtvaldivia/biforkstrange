"""Arma derivados/modelo_magister.json.

Entradas: salida de magister_oferta.py (SIES 2026 + selectividad DEMRE) y la Figura C1 de DIPRES 2026
digitalizada con magister_digitaliza_fig_c1.py (pagina 47 renderizada a 3x).
Uso: python -I magister_ensamblar.py <oferta_magister.json> <salida.json>
"""
import json, sys

of = json.load(open(sys.argv[1]))
URL26 = "https://www.dipres.gob.cl/598/articles-406754_doc_pdf.pdf"
# Figura C1 (panel inferior), USD mensuales, IC 95 %, digitalizada; error de lectura ~ +-5 USD
C1 = {
    "competitiva": {0: (-6, -77, 65), 1: (-46, -154, 61), 2: (194, 53, 335), 3: (256, 94, 418),
                    4: (207, 27, 388), 5: (115, -63, 295), 6: (213, 18, 407), 7: (269, 71, 468)},
    "no_competitiva": {0: (-118, -196, -40), 1: (-193, -286, -100), 2: (-27, -131, 78), 3: (75, -41, 192),
                       4: (105, -27, 236), 5: (-8, -143, 125), 6: (32, -106, 173), 7: (6, -148, 159)},
}
def serie(g):
    return {f"t{t}": {"usd_mes": e, "ic95": [lo, hi]} for t, (e, lo, hi) in C1[g].items()}
def media57(g):
    return round(sum(C1[g][t][0] for t in (5, 6, 7)) / 3)

pool = 150  # USD/mes al ano 7, DIPRES 2026 resumen p. 4 (la base del 7 % que ya usa el motor)
prima = {
    "fuente": "DIPRES mar. 2026, 'Radiografia de la formacion de postgrado', Anexo, Figura C1 panel inferior (p. 47) y texto p. 31 y p. 45-46",
    "url": URL26,
    "metodo": "estudio de eventos con efectos fijos de dos vias, becarios Magister Nacional vs no becarios, renta total mensual SII en USD; t = anos desde la adjudicacion",
    "pooled_referencia": {"usd_mes_ano_7": pool, "rango_usd_mes_fig8": [130, 170], "estado": "vista",
                          "pagina": "p. 4 y Fig. 8 (p. 29)", "motor_actual_pct": 0.07},
    "competitiva": {
        "serie": serie("competitiva"), "media_t5_t7_usd_mes": media57("competitiva"),
        "estado": "calculada (digitalizacion de la Figura C1; los valores no estan tabulados en el informe)",
        "lectura": "IC excluye cero en t2, t3, t4, t6, t7; costo de estudiar (t0-t1) chico y no significativo",
    },
    "no_competitiva": {
        "serie": serie("no_competitiva"), "media_t5_t7_usd_mes": media57("no_competitiva"),
        "estado": "calculada (digitalizacion de la Figura C1)",
        "lectura": "caida significativa durante los estudios (t0 -118, t1 -193 USD); desde t2 el IC siempre incluye cero",
    },
    "en_pct_escalado": {
        "competitiva_t7": round(0.07 * C1["competitiva"][7][0] / pool, 3),
        "competitiva_media_t5_t7": round(0.07 * media57("competitiva") / pool, 3),
        "no_competitiva_t7": round(0.07 * C1["no_competitiva"][7][0] / pool, 3),
        "no_competitiva_media_t5_t7": round(0.07 * media57("no_competitiva") / pool, 3),
        "estado": "calculada",
        "supuesto": "escala el 7 % del motor (equivalente a 150 USD pooled) en proporcion a los USD de cada grupo; supone la misma renta base en ambos grupos, cosa que el informe no reporta",
    },
    "advertencia": ("El informe se contradice: el cuerpo (p. 31) dice que las competitivas sostienen la prima y en las no competitivas "
                    "se diluye con IC que incluye cero; el anexo (p. 45-46) dice que los IC de ambos grupos se traslapan en t2-t7 "
                    "y que no hay diferencia significativa entre ellos (puntos de las competitivas 'en torno a 200 y 300 USD'). "
                    "Lo defendible: prima positiva y distinta de cero solo en competitivas; diferencia entre grupos no significativa."),
    "jornada_o_duracion": "DIPRES 2026 no separa por jornada ni duracion del programa (ver sin_dato)",
    "dipres_2024": {"estado": "vista", "url": "https://www.dipres.gob.cl/597/articles-341575_informe_final.pdf",
                    "nota": "No trae cortes por institucion ni por selectividad; solo efectos agregados (Tabla A.20, magister nacional, ningun coeficiente significativo)."},
}

defsel = {
    "criterio_dipres": ("Anexo p. 44-45: se ordena a todos los postulantes por puntaje de admision (PAA/PSU) en 10 deciles; una universidad es "
                        "'competitiva' si la proporcion de sus estudiantes en deciles 8-10 supera a la de deciles 1-7 (mas de la mitad en el 30 % superior)."),
    "estado_criterio": "vista",
    "lista_dipres": "sin_dato: el informe no publica que universidades quedan en cada grupo",
    "ambiguedad": "El anexo titula 'Clasificacion ... (Pregrado)' y habla de 'institucion de origen'; no queda claro si clasifica la universidad del pregrado del becario o la del magister. Aqui se aplica a la universidad que dicta el magister.",
    "replica": {
        "estado": "calculada",
        "script": "datos_laborales/scripts/modelo/magister_selectividad.py",
        "datos": "DEMRE/Mineduc datos abiertos, PAES 2024 y 2025: Inscritos-Puntajes y Matricula (https://datosabiertos.mineduc.cl/pruebas-de-admision-a-la-educacion-superior/)",
        "puntaje": "PROMEDIO_CM_MAX (promedio Competencia Lectora + Matematica 1)",
        "poblacion_deciles": "inscritos con puntaje > 0 (270.604 en 2025; 268.915 en 2024). DIPRES usa 'universo total de postulantes'; si se usaran solo postulantes, los cortes suben y la lista podria achicarse.",
        "corte_decil_8": {"paes2025": 675.5, "paes2024": 664.0},
        "regla_final": "selectiva = 'si' si es competitiva en 2024 y 2025; 'borde' si cambia entre anos; 'no' si no lo es en ninguno; null si no admite por el sistema DEMRE",
        "selectivas": [r["nombre"] for r in of["universidades"] if r["selectiva"] == "si"],
        "borde": [r["nombre"] for r in of["universidades"] if r["selectiva"] == "borde"],
        "limite": "Cohortes 2024-2025, no las cohortes PSU que uso DIPRES; universidades fuera del Sistema de Acceso quedan sin clasificar.",
    },
}

res = {
    "_meta": {
        "generado": "2026-11-21",
        "scripts": ["magister_selectividad.py", "magister_oferta.py", "magister_digitaliza_fig_c1.py", "magister_ensamblar.py"],
        "oferta_fuente": "SIES/mifuturo Oferta_Academica_2026_SIES_05_06_2026_WEB_E.xlsx, https://www.mifuturo.cl/bases-de-datos-de-oferta-academica/",
        "oferta_universo": "Nivel Carrera = Magister, Vigencia = 'Vigente con estudiantes nuevos'. Cada fila es un codigo unico (programa x sede x jornada x version), no un programa distinto.",
        "arancel": "Arancel Anual en pesos; 130 filas en UF convertidas con UF 05-06-2026 = 40.695,38 (SII, https://www.sii.cl/valores_y_fechas/uf/uf2026.htm); aranceles en 0 excluidos (20 filas)",
        "duracion": "Duracion Total de SIES (semestres, incluye titulacion)",
        "jornadas_sies": "Diurna, Vespertina, Semipresencial, A Distancia, Otra. No hay categoria 'fin de semana' ni 'tiempo parcial'.",
    },
    "prima": prima,
    "definicion_selectiva": defsel,
    "universidades": of["universidades"],
    "por_jornada": {"estado": "calculada", "por_jornada": of["por_jornada"], "diurna_vs_no_diurna": of["diurna_vs_no_diurna"],
                    "sistema": of["sistema"], "por_selectiva": of["por_selectiva"], "por_selectiva_y_jornada": of["por_selectiva_y_jornada"]},
    "sin_dato": [
        "Prima salarial por jornada (vespertina, semipresencial, a distancia vs diurna): ni DIPRES 2026 ni DIPRES 2024 la estiman.",
        "Lista de universidades competitivas usada por DIPRES 2026: no se publica; se replico la regla con DEMRE.",
        "Prima en % por grupo: DIPRES solo da USD; el % es un escalado del equipo.",
        "Dedicacion horaria (horas por semana) de los programas: SIES no la trae; 'jornada' es solo horario o modalidad.",
        "Programas de fin de semana o tiempo parcial como categoria: SIES no la distingue (quedan dentro de Vespertina, Semipresencial u Otra).",
        "Diferencia de duracion por jornada: la mediana es 4 semestres en todas las jornadas (p25-p75 = 4-4), sin variacion utilizable.",
    ],
}
json.dump(res, open(sys.argv[2], "w"), ensure_ascii=False, indent=1)
print(json.dumps(res["prima"]["en_pct_escalado"]), defsel["replica"]["selectivas"], defsel["replica"]["borde"])
