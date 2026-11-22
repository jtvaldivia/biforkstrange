import base64
"""Perfil desde un texto. No se llama al modelo: se prueba lo que la app hace con lo que el modelo devuelve."""

import pytest

from app.services import perfil_ia
from app.services.perfil_ia import ModeloNoDisponible, PerfilLeido

LEIDO = PerfilLeido(edad=33, sexo="m", edu="universitaria", carrera_id=166, rubro="Finanzas y seguros",
                    tipo_empleador="startup", nivel=2, sueldo=2_624_000, ocupacion=2, antiguedad=3, region="rm",
                    inferido=["sueldo: 82% de 3,2 millones brutos"])


def test_completar_usa_lo_leido_y_marca_lo_que_falta():
    r = perfil_ia.completar(LEIDO)
    assert r["perfil"]["edad"] == 33 and r["perfil"]["carrera_id"] == 166 and r["perfil"]["sueldo"] == 2_624_000
    assert r["perfil"]["riesgo"] == 5  # el texto no lo dice: valor por defecto
    assert [s["campo"] for s in r["supuestos"]] == ["riesgo", "ingles"]  # el CV no habla de idiomas
    assert r["inferido"] == LEIDO.inferido


def test_sin_sueldo_se_usa_la_mediana_de_su_edad_y_estudios():
    r = perfil_ia.completar(LEIDO.model_copy(update={"sueldo": None}))
    assert "sueldo" in [s["campo"] for s in r["supuestos"]]
    # ESI 2025, universitaria, 30-34 (valor literal de esi_perfil_edad_edu.csv)
    assert r["perfil"]["sueldo"] == 1_100_000


def test_valores_fuera_de_rango_o_inventados_se_descartan():
    raro = LEIDO.model_copy(update={"rubro": "Criptomonedas", "edad": 12, "carrera_id": 999, "nivel": 9})
    r = perfil_ia.completar(raro)
    faltan = {s["campo"] for s in r["supuestos"]}
    assert {"rubro", "edad", "nivel"} <= faltan
    assert r["perfil"]["rubro"] == "Servicios profesionales" and r["perfil"]["carrera_id"] == -1


def test_texto_vacio_o_demasiado_largo():
    with pytest.raises(ValueError):
        perfil_ia.leer("   ", "2026-11-21")
    with pytest.raises(ValueError):
        perfil_ia.leer("x" * (perfil_ia.MAX_CARACTERES + 1), "2026-11-21")


def test_sin_credenciales_ni_comando_se_avisa(monkeypatch):
    monkeypatch.setattr(perfil_ia, "_hay_credenciales", lambda: False)
    monkeypatch.setattr(perfil_ia.shutil, "which", lambda _: None)
    with pytest.raises(ModeloNoDisponible):
        perfil_ia.leer("Soy contadora", "2026-11-21")


def test_api_perfil(client, monkeypatch):
    monkeypatch.setattr(perfil_ia, "leer", lambda texto, hoy, pq=None, pdf=None: (LEIDO, "api"))
    r = client.post("/api/juego/perfil", json={"texto": "Soy Camila..."})
    assert r.status_code == 200
    cuerpo = r.json()
    assert cuerpo["perfil"]["tipo_empleador"] == "startup" and cuerpo["via"] == "api"
    # el perfil devuelto sirve tal cual para empezar una partida
    assert client.post("/api/juego/partida", json={"perfil": cuerpo["perfil"], "duda": "emprender", "gemelos": 0}).status_code == 200


def test_api_perfil_sin_modelo_da_503(client, monkeypatch):
    def falla(texto, hoy, pq=None, pdf=None):
        raise ModeloNoDisponible("sin credenciales")

    monkeypatch.setattr(perfil_ia, "leer", falla)
    assert client.post("/api/juego/perfil", json={"texto": "hola"}).status_code == 503
    assert client.post("/api/juego/perfil", json={"texto": ""}).status_code == 422



def test_api_perfil_desde_pdf(client, monkeypatch):
    recibido = {}

    def leer(texto, hoy, pq=None, pdf=None):
        recibido["pdf"] = pdf
        return LEIDO, "api"

    monkeypatch.setattr(perfil_ia, "leer", leer)
    pdf = base64.b64encode(b"%PDF-1.7 cv de prueba").decode()
    r = client.post("/api/juego/perfil", json={"pdf": f"data:application/pdf;base64,{pdf}"})
    assert r.status_code == 200 and recibido["pdf"] == b"%PDF-1.7 cv de prueba"


def test_api_perfil_rechaza_lo_que_no_es_pdf(client):
    otro = base64.b64encode(b"PK\x03\x04 un zip").decode()
    r = client.post("/api/juego/perfil", json={"pdf": otro})
    assert r.status_code == 422 and "no es un PDF" in r.json()["detail"]
    assert client.post("/api/juego/perfil", json={"pdf": "no es base64!!"}).status_code == 422


def test_el_pdf_va_como_documento_a_la_api(monkeypatch):
    llamada = {}

    class Mensajes:
        def parse(self, **k):
            llamada.update(k)
            return type("R", (), {"stop_reason": "end_turn", "parsed_output": LEIDO})()

    monkeypatch.setattr(perfil_ia.anthropic, "Anthropic", lambda **k: type("C", (), {"messages": Mensajes()})())
    perfil_ia._por_api("", "2026-11-21", perfil_ia.paquete(), b"%PDF-1.7")
    bloques = llamada["messages"][0]["content"]
    assert bloques[0]["type"] == "document" and bloques[0]["source"]["media_type"] == "application/pdf"
    assert llamada["model"] == "claude-haiku-5-5" and llamada["thinking"] == {"type": "disabled"}

# ── documento armado por el Claude de la persona ──────────────────────────────

from pathlib import Path

from app.services import perfil_doc

EJEMPLO = (Path(__file__).parents[2] / "docs" / "motor" / "perfil-ejemplo.md").read_text(encoding="utf-8")


def test_el_prompt_trae_el_formato_y_las_listas_validas():
    p = perfil_doc.prompt()
    assert "```gemelo-laboral" in p
    assert "Finanzas y seguros" in p and "unirse_a_startup (" in p
    assert "tener_hijo" not in p  # solo lo laboral


def test_el_documento_de_ejemplo_se_lee_exacto_y_sin_modelo(monkeypatch):
    monkeypatch.setattr(perfil_ia, "leer", lambda *a, **k: (_ for _ in ()).throw(AssertionError("no debe llamar al modelo")))
    r = perfil_ia.perfil_desde_texto(EJEMPLO, "2026-11-21")
    assert r["via"] == "documento" and r["duda"] == "emprender" and r["avisos"] == [] and r["supuestos"] == []
    from app.schemas.juego import PerfilIn

    # lo que el documento no trae (su historia del CV, cuánto le falta si estudia) queda en el valor por defecto
    assert r["perfil"] | {"ahorro": None} == PerfilIn().model_dump() | {
        "edad": 33, "sexo": "m", "edu": "universitaria", "carrera_id": 166, "rubro": "Finanzas y seguros",
        "tipo_empleador": "startup", "nivel": 2, "sueldo": 2_624_000, "riesgo": 4, "ocupacion": 2,
        "antiguedad": 3, "region": "rm", "ahorro": None, "ingles": 1, "skill": 57, "red": 35,
        "estado": "empleado", "meses_cesante": 0, "parcial": 0, "remoto": 0, "usa_ia": 0, "empresa_anos": 0,
        "empresa_fondos": 0, "anos_por_empleo": 3.0, "universidad_id": "", "empresa_nombre": "Fintual"}
    assert any("82%" in frase for frase in r["inferido"])


def test_documento_con_valores_libres_o_malos():
    doc = "```gemelo-laboral\nsexo: hombre\nestudios: técnica\ntipo_empresa: Estado\ncargo: jefatura\n" \
          "rubro: construccion\nsueldo_liquido: $1.250.000\nriesgo: 15\nedad: ?\nduda: volar\n```"
    r = perfil_doc.leer_documento(doc)
    p = r["perfil"]
    assert (p["sexo"], p["edu"], p["tipo_empleador"], p["nivel"], p["rubro"], p["sueldo"]) == \
           ("h", "tecnica", "publico", 3, "Construcción", 1_250_000)
    assert {"edad", "riesgo"} <= {s["campo"] for s in r["supuestos"]}
    assert any("riesgo" in a for a in r["avisos"]) and any("volar" in a for a in r["avisos"])
    assert r["duda"] is None


def test_cargo_por_nombre_no_borra_el_aviso_de_otro_campo():
    r = perfil_doc.leer_documento("```gemelo-laboral\ncargo: Senior\nantiguedad: tres\n```")
    assert r["perfil"]["nivel"] == 2
    assert not any(a.startswith("cargo:") for a in r["avisos"])
    assert any(a.startswith("antigüedad:") for a in r["avisos"])


def test_catalogo_trae_la_referencia_de_sueldos(client):
    ref = client.get("/api/juego/catalogo").json()["sueldos_ref"]
    fila = next(f for f in ref if f["educacion"] == "universitaria" and f["banda"] == "30-34")
    assert fila["p25"] < fila["p50"] < fila["p75"] and fila["p50"] % 10_000 == 0


def test_carrera_parecida_se_avisa_y_desconocida_queda_sin_carrera():
    pq = perfil_ia.paquete()
    cid, nota = perfil_doc._carrera("Ing. Civil Industrial", "U", pq)
    assert cid is not None and "se tomó como" in nota
    cid, nota = perfil_doc._carrera("Astrología cuántica", "U", pq)
    assert cid is None and "no está en el catálogo" in nota


def test_texto_sin_bloque_no_es_documento():
    assert perfil_doc.leer_documento("Soy contadora y trabajo en una pyme.") is None


def test_api_prompt(client):
    assert "```gemelo-laboral" in client.get("/api/juego/prompt").json()["prompt"]


def test_las_dudas_sugeridas_se_filtran_por_el_perfil():
    leido = LEIDO.model_copy(update={
        "dudas_sugeridas": [
            perfil_ia.DudaSugerida(decision="volar_a_marte", por_que="no existe"),
            perfil_ia.DudaSugerida(decision="emprender", por_que="Llevas años pensando en tu idea."),
            perfil_ia.DudaSugerida(decision="emprender", por_que="repetida"),
        ],
        "retrato": "  Eres contadora en una startup.  ",
    })
    r = perfil_ia.completar(leido)
    assert [d["decision"] for d in r["dudas_sugeridas"]] == ["emprender"]
    assert r["dudas_sugeridas"][0]["por_que"] == "Llevas años pensando en tu idea."
    assert r["retrato"] == "Eres contadora en una startup."


def test_ingles_experiencia_y_empresa_del_sii():
    leido = LEIDO.model_copy(update={"ingles": True, "anios_experiencia": 8, "empleadores": 3,
                                     "tipo_empleador": None, "rubro": None,
                                     "empresa_actual": "I. Municipalidad de Curicó"})
    r = perfil_ia.completar(leido)
    p = r["perfil"]
    assert (p["ingles"], p["skill"], p["red"]) == (1, 55, 35)
    # la empresa está en el SII: tamaño y rubro son dato, no supuesto
    assert r["empresa"]["tamano"] == "grande" and p["tipo_empleador"] == "grande"
    assert p["rubro"] == "Administración pública"
    assert not {"tipo_empleador", "rubro", "ingles"} & {s["campo"] for s in r["supuestos"]}


def test_sin_datos_nuevos_el_motor_usa_los_supuestos_de_siempre():
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial

    e = estado_inicial(Perfil(), paquete())
    assert (e["ingles"], e["skill"], e["red"]) == (0, 50, 30)
    e = estado_inicial(Perfil(ingles=1, skill=70, red=50), paquete())
    assert (e["ingles"], e["skill"], e["red"]) == (1, 70, 50)


def test_sin_cv_la_habilidad_se_estima_por_los_anios_desde_el_titulo():
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial

    pq = paquete()
    assert estado_inicial(Perfil(edad=24, edu="universitaria"), pq)["skill"] == 35  # recién titulado
    assert estado_inicial(Perfil(edad=45, edu="universitaria"), pq)["skill"] == 87
    assert estado_inicial(Perfil(edad=45, skill=40), pq)["skill"] == 40  # el dato del CV manda
    assert estado_inicial(Perfil.a_los_18(), pq)["skill"] == 50  # la cohorte de validación no cambia


def test_situacion_y_trayectoria_del_cv():
    leido = LEIDO.model_copy(update={"situacion": "buscando", "meses_sin_trabajo": 10, "remoto": True, "usa_ia": True,
                                     "anios_experiencia": 6, "empleadores": 5})
    p = perfil_ia.completar(leido)["perfil"]
    assert (p["estado"], p["meses_cesante"], p["remoto"], p["usa_ia"], p["anos_por_empleo"]) == ("buscando", 10, 1, 1, 1.2)


def test_la_situacion_llega_al_motor():
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial

    pq = paquete()
    e = estado_inicial(Perfil(estado="buscando", meses_cesante=10, sueldo=900_000), pq)
    assert (e["estado"], e["hueco"], e["meses_cesante"]) == ("buscando", 1, 10)
    e = estado_inicial(Perfil(parcial=1, remoto=1, usa_ia=1), pq)
    assert (e["horas"], e["remoto"], e["usa_ia"]) == (22, 1, 1)
    e = estado_inicial(Perfil(), pq)
    assert (e["hueco"], e["horas"], e["remoto"], e["usa_ia"]) == (0, 44, 0, 0)  # sin datos: como antes


def test_cuanto_le_falta_a_quien_estudia():
    estudia = LEIDO.model_copy(update={"situacion": "estudiando", "edad": 21, "edu": "media"})
    r = perfil_ia.completar(estudia.model_copy(update={"anio_egreso_esperado": 2028}), hoy="2026-11-21")
    assert r["perfil"]["semestres_restantes"] == 4 and r["perfil"]["anos_en_carrera"] is None
    assert any("2028" in f and "2 años más" in f for f in r["inferido"])
    r = perfil_ia.completar(estudia.model_copy(update={"anio_que_cursa": 3}), hoy="2026-11-21")
    assert r["perfil"]["anos_en_carrera"] == 2 and r["perfil"]["semestres_restantes"] is None
    r = perfil_ia.completar(estudia, hoy="2026-11-21")  # sin dato: el supuesto se dice como supuesto
    assert r["perfil"]["semestres_restantes"] is None and any("supuesto del equipo" in f for f in r["inferido"])
    # quien trabaja no recibe estos campos ni la frase, aunque el texto diga un año de egreso
    r = perfil_ia.completar(LEIDO.model_copy(update={"anio_egreso_esperado": 2028}), hoy="2026-11-21")
    assert r["perfil"]["semestres_restantes"] is None and not any("titular" in f for f in r["inferido"])


@pytest.mark.parametrize(("rasgo", "opcion"), [("volvio_a_su_nivel", "nivel"), ("freelance_entre_pegas", "informal"),
                                              ("emprendio_antes", "emprender")])
def test_en_la_cesantia_tus_gemelos_salen_como_saliste_tu(rasgo, opcion):
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial
    from app.sim.motor.politicas import PESOS_FORZADAS, pesos_personales

    # sin el dato: ni el estado ni los pesos cambian
    sin = estado_inicial(Perfil(), paquete())
    assert rasgo not in sin and pesos_personales(sin) == {}
    con = estado_inicial(Perfil(**{rasgo: 1}), paquete())
    pesos = pesos_personales(con)
    assert set(pesos) == {"cesantia"} and sum(pesos["cesantia"].values()) == pytest.approx(1, abs=1e-3)
    assert pesos["cesantia"][opcion] > PESOS_FORZADAS["cesantia"][opcion]
    r = perfil_ia.completar(LEIDO.model_copy(update={rasgo: True}))
    assert r["perfil"][rasgo] == 1 and any("si quedan cesantes" in f for f in r["inferido"])
    r = perfil_ia.completar(LEIDO.model_copy(update={rasgo: False}))
    assert r["perfil"][rasgo] == 0 and not any("si quedan cesantes" in f for f in r["inferido"])


def test_independiente_veterano_o_de_paso():
    from app.sim.motor.motor import P_INDEPENDIENTE_BUSCA_EMPLEO, p_independiente_busca_empleo
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial

    def p(**perfil):
        return p_independiente_busca_empleo(estado_inicial(Perfil(estado="independiente", **perfil), paquete()))

    assert P_INDEPENDIENTE_BUSCA_EMPLEO == 0.055 and p() == 0.055  # sin historia, la tasa calibrada de siempre
    assert p(anos_independiente=4) == 0.055 and p(anos_independiente=5) == pytest.approx(0.0275)
    assert p(freelance_entre_pegas=1) == pytest.approx(0.11)
    assert p(freelance_entre_pegas=1, anos_independiente=8) == pytest.approx(0.11)  # ya volvió una vez: manda eso
    # los años por su cuenta solo describen a quien hoy es independiente
    assert "anos_independiente" not in estado_inicial(Perfil(anos_independiente=8), paquete())

    indep = LEIDO.model_copy(update={"situacion": "independiente", "anos_independiente": 8})
    r = perfil_ia.completar(indep)
    assert r["perfil"]["anos_independiente"] == 8 and any("Llevas 8 años por tu cuenta" in f for f in r["inferido"])
    r = perfil_ia.completar(indep.model_copy(update={"anos_independiente": 2}))
    assert r["perfil"]["anos_independiente"] == 2 and not any("por tu cuenta" in f for f in r["inferido"])
    r = perfil_ia.completar(LEIDO.model_copy(update={"anos_independiente": 8}))  # empleado: no aplica
    assert r["perfil"]["anos_independiente"] is None


def test_la_practica_pesa_en_la_primera_pega():
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial
    from app.sim.motor.politicas import PESOS_FORZADAS, pesos_personales

    estudia = dict(edad=22, estado="estudiando", edu="media", sueldo=0, rubro="", tipo_empleador="", nivel=0)
    assert pesos_personales(estado_inicial(Perfil(**estudia), paquete())) == {}  # sin práctica, como siempre
    for practica, opcion in (("grande", "grande"), ("publico", "estado")):
        e = estado_inicial(Perfil(**estudia, practica=practica), paquete())
        pesos = pesos_personales(e)["primera_pega"]
        assert pesos[opcion] > PESOS_FORZADAS["primera_pega"][opcion]
        assert sum(pesos.values()) == pytest.approx(1, abs=1e-3)
    assert pesos_personales(estado_inicial(Perfil(**estudia, practica="pyme"), paquete())) == {}
    # solo a quien estudia o busca su primer empleo: a quien ya trabaja no le llega
    assert "practica" not in estado_inicial(Perfil(practica="grande"), paquete())

    r = perfil_ia.completar(LEIDO.model_copy(update={"situacion": "estudiando", "practica": "publico"}))
    assert r["perfil"]["practica"] == "publico" and any("práctica en el Estado" in f for f in r["inferido"])
    r = perfil_ia.completar(LEIDO.model_copy(update={"practica": "grande"}))  # empleado: no aplica
    assert r["perfil"]["practica"] == "" and not any("práctica" in f for f in r["inferido"])


def test_toda_su_carrera_en_el_estado_o_en_startups_sesga_el_reempleo():
    from app.sim.motor.paquete import K_PROPIOS, paquete
    from app.sim.motor.perfil import Perfil, estado_inicial

    pq = paquete()
    sorteo = pq.decisiones["tipo_de_empleador"]["opciones"][0]["resultados"]
    probs = lambda e: {r["id"]: pq.evaluar(r["prob"], e) for r in sorteo if r["prob"] != "resto"}  # noqa: E731
    # la fila de su origen (pyme) en la escalera de transiciones_tipo
    fila = {f["destino"]: float(f["prob"]) for f in pq.filas("transiciones_tipo") if f["origen"] == "pyme"}
    base = estado_inicial(Perfil(), pq)
    assert K_PROPIOS not in base  # sin historia, k() es el del paquete
    assert probs(base) == pytest.approx({d: fila[d] for d in ("publico", "grande", "pyme")})
    assert probs(base | {K_PROPIOS: {}}) == probs(base)  # el camino con parámetros propios, vacío, da lo mismo
    estado = probs(estado_inicial(Perfil(toda_su_carrera_en="publico"), pq))
    assert estado["publico"] == pytest.approx(0.40)  # piso sobre la fila
    assert estado["grande"] / estado["pyme"] == pytest.approx(fila["grande"] / fila["pyme"])  # el resto, como su fila
    startup = probs(estado_inicial(Perfil(toda_su_carrera_en="startup"), pq))
    assert startup["publico"] == pytest.approx(fila["publico"]) and 1 - sum(startup.values()) == pytest.approx(0.88 * 0.20)
    assert startup["grande"] / startup["pyme"] == pytest.approx(fila["grande"] / fila["pyme"])
    assert pq.k("P_REEMPLEO_PUBLICO") == 0.12  # el paquete no se toca: el parámetro es solo de esa vida

    r = perfil_ia.completar(LEIDO.model_copy(update={"toda_su_carrera_en": "publico"}))
    assert r["perfil"]["toda_su_carrera_en"] == "publico"
    assert any("vuelven al Estado al menos 40%" in f and "12%" in f for f in r["inferido"])


def test_quien_asciende_rapido_asciende_mas():
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, ascenso_extra, estado_inicial

    pq = paquete()
    assert estado_inicial(Perfil(), pq)["prob_ascenso_extra"] == 0  # sin dato, como siempre
    # se compara con el ritmo del paquete en los cargos que ya subió (ASCENSO 0,10 y 0,08 hasta senior)
    assert ascenso_extra(0.15, 2, pq) == pytest.approx(0.5 * (0.15 - 0.09))
    assert ascenso_extra(0.05, 2, pq) == 0  # más lento no resta
    assert ascenso_extra(1.0, 1, pq) == 0.04  # tope
    e = estado_inicial(Perfil(nivel=2, ascensos_por_ano=0.15), pq)
    assert e["prob_ascenso_extra"] == pytest.approx(0.03)

    leido = LEIDO.model_copy(update={"ascensos_internos": 2, "anios_experiencia": 8})  # nivel 2
    r = perfil_ia.completar(leido)
    assert r["perfil"]["ascensos_por_ano"] == 0.25 and any("ascendido 2 veces en 8 años" in f for f in r["inferido"])
    r = perfil_ia.completar(leido.model_copy(update={"ascensos_internos": 0}))
    assert r["perfil"]["ascensos_por_ano"] == 0 and not any("ascendido" in f for f in r["inferido"])
    r = perfil_ia.completar(leido.model_copy(update={"anios_experiencia": 1}))  # muy poco para hablar de ritmo
    assert r["perfil"]["ascensos_por_ano"] is None


def test_quien_ya_cerro_empresas_cierra_antes():
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial
    from app.sim.motor.politicas import pesos_personales

    fundador = dict(estado="fundador", empresa_anos=1)
    assert pesos_personales(estado_inicial(Perfil(**fundador), paquete())) == {}  # sin dato, como siempre
    cerrar = [pesos_personales(estado_inicial(Perfil(**fundador, empresas_cerradas=n), paquete()))
              ["seguir_con_tu_empresa"]["cerrar"] for n in (1, 3, 9)]
    assert cerrar == [0.10, 0.20, 0.20]  # 0,05 por empresa, hasta +0,15
    r = perfil_ia.completar(LEIDO.model_copy(update={"situacion": "fundador", "empresas_cerradas": 2}))
    assert r["perfil"]["empresas_cerradas"] == 2 and any("Ya cerraste 2 empresas" in f and "15%" in f
                                                         for f in r["inferido"])


def test_los_gemelos_se_cambian_como_tu():
    from app.sim.motor.politicas import pesos_personales

    assert pesos_personales({}) == {}
    seguido = pesos_personales({"anos_por_empleo": 1.0})["oferta_externa"]["cambiar"]
    quieto = pesos_personales({"anos_por_empleo": 8.0})["oferta_externa"]["cambiar"]
    assert quieto < 0.34 < seguido <= 0.65


TU_CLAUDE = """```gemelo-laboral
sueldo_liquido: 1.800.000
duda: ?
situacion: empleado
riesgo: 6
ingles: si
ia: no uso
proyecto: una app para reservar canchas de pádel
afuera: si
rubro_sonado: Artes y entretención
intereses: cine, filosofía, literatura rusa
retrato: Eres analista de datos y escribes crítica de cine los fines de semana.
```"""


def test_el_prompt_es_corto_y_pide_lo_que_un_cv_no_dice():
    p = perfil_doc.prompt()
    assert len(p) < 3500  # cabe en el link que abre Claude o ChatGPT con el prompt escrito
    for campo in ("sueldo_liquido:", "proyecto:", "afuera:", "rubro_sonado:", "intereses:", "Nada de salud"):
        assert campo in p


def test_el_prompt_pide_tu_cargo_y_tus_pegas_anteriores_sin_suponerlas():
    p = perfil_doc.prompt()
    for campo in ("empresa:", "cargo:", "nivel:", "pegas_anteriores:", "no las supongas"):
        assert campo in p


def test_tu_cargo_y_tus_pegas_anteriores_entran_al_perfil():
    unica = perfil_doc.leer_documento("```gemelo-laboral\nempresa: BancoEstado\ncargo: Analista de riesgo\n"
                                      "nivel: Semi senior\npegas_anteriores: ninguna\n```")
    p = unica["perfil"]
    assert (p["empresa_nombre"], p["cargo_nombre"], p["nivel"]) == ("BancoEstado", "Analista de riesgo", 1)
    assert {"empresa_nombre", "cargo_nombre", "nivel", "red"} <= set(unica["dados"]) and unica["avisos"] == []
    dos = perfil_doc.leer_documento("```gemelo-laboral\npegas_anteriores: Falabella, analista; Entel, practicante\n```")
    assert dos["perfil"]["red"] > p["red"]  # tres empleadores contra uno
    # sin saber si hubo otras, no se supone nada
    assert "red" not in perfil_doc.leer_documento("```gemelo-laboral\npegas_anteriores: ?\nedad: 30\nriesgo: 4\n```")["dados"]


def test_lo_que_cuenta_tu_claude_sugiere_dudas_y_entra_al_perfil():
    r = perfil_doc.leer_documento(TU_CLAUDE)
    p = r["perfil"]
    assert (p["sueldo"], p["ingles"], p["usa_ia"], p["rubro_sonado"]) == (1_800_000, 1, 0, "Artes y entretención")
    assert r["intereses"] == ["cine", "filosofía", "literatura rusa"]
    assert r["retrato"].startswith("Eres analista")
    sugeridas = [d["decision"] for d in r["dudas_sugeridas"]]
    assert sugeridas[0] == "emprender" and len(sugeridas) == 3 and r["duda"] == "emprender"
    assert "pádel" in r["dudas_sugeridas"][0]["por_que"]
    assert {"sueldo", "riesgo", "ingles", "usa_ia", "estado", "rubro_sonado"} <= set(r["dados"])
    assert "edad" not in r["dados"]  # no la dijo: no debe pisar la del CV


def test_el_rubro_sonado_es_la_opcion_por_defecto_al_cambiarse():
    from app.sim.motor.azar import Dados
    from app.sim.motor.motor import Vida
    from app.sim.motor.paquete import paquete
    from app.sim.motor.perfil import Perfil, estado_inicial
    from app.sim.motor.politicas import parametros_por_defecto

    pq = paquete()
    vida = Vida(estado_inicial(Perfil(rubro_sonado="Artes y entretención"), pq), Dados(0, "jugador"), pq)
    opcion = next(o for o in vida.opciones("cambiar_de_rubro") if o.id == "cambiar")
    assert parametros_por_defecto(vida, opcion)["rubro_destino"] == "Artes y entretención"
    sin = Vida(estado_inicial(Perfil(), pq), Dados(0, "jugador"), pq)
    assert parametros_por_defecto(sin, opcion)["rubro_destino"] != "Artes y entretención"  # sin dato, como antes



def test_el_esquema_de_la_api_cabe_en_los_limites_de_structured_outputs():
    # la API acepta hasta 24 campos opcionales y 16 con tipo unión; con más responde 400
    import json

    esquema = perfil_ia.esquema_api().model_json_schema()
    texto = json.dumps(esquema)
    assert texto.count("anyOf") == 0 and texto.count('"type": [') == 0
    assert set(esquema["properties"]) == set(esquema["required"])


def test_desde_api_vuelve_los_no_se_a_none():
    crudo = {k: -1 for k, v in perfil_ia.esquema_api().model_json_schema()["properties"].items() if v.get("type") == "integer"}
    crudo |= {"sexo": "?", "edu": "universitaria", "ingles": "no", "remoto": "si", "rubro": "", "inferido": [],
              "dudas_sugeridas": [], "edad": 33}
    leido = perfil_ia.desde_api(crudo)
    assert (leido.edad, leido.edu, leido.sexo, leido.ingles, leido.remoto, leido.rubro, leido.sueldo) == \
           (33, "universitaria", None, False, True, None, None)


def test_el_bloque_sin_cercas_se_lee_igual():
    texto = "sueldo_liquido: 1800000\nduda: ?\nsituacion: empleado\nedad: 25\nestudios: universitaria\n" \
            "rubro: Finanzas y seguros\ntipo_empresa: startup\nrubro_sonado: ?\nproyecto: Virgilio, un second brain"
    r = perfil_doc.leer_documento(texto)
    assert r is not None and r["perfil"]["edad"] == 25 and r["perfil"]["tipo_empleador"] == "startup"
    assert "rubro_sonado" not in r["dados"] and r["dudas_sugeridas"][0]["decision"] == "emprender"
    assert perfil_doc.leer_documento("Hola, soy Benito y trabajo en una startup.") is None


def test_si_se_pega_la_conversacion_entera_se_lee_la_respuesta():
    texto = perfil_doc.prompt() + "\n\n```gemelo-laboral\nsueldo_liquido: 2.100.000\nedad: 31\n```"
    r = perfil_doc.leer_documento(texto)
    assert (r["perfil"]["sueldo"], r["perfil"]["edad"]) == (2_100_000, 31) and r["avisos"] == []


def test_numeros_como_los_escribe_una_persona():
    casos = {"1.800.000": 1_800_000, "$1,5 millones": 1_500_000, "2M": 2_000_000, "900 mil": 900_000, "25": 25}
    assert {k: perfil_doc._entero(k) for k in casos} == casos


def test_lo_que_esta_fuera_de_rango_no_cuenta_como_dicho():
    r = perfil_doc.leer_documento("```gemelo-laboral\nedad: 55\nsueldo_liquido: 1500000\n```")
    assert "edad" not in r["dados"] and "sueldo" in r["dados"]


def test_ritmo_de_cambio_absurdo_no_rompe():
    leido = LEIDO.model_copy(update={"anios_experiencia": 1, "empleadores": 25})
    assert perfil_ia.completar(leido)["perfil"]["anos_por_empleo"] == 0.1
