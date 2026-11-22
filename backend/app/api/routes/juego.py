"""El juego sobre el motor del paquete. Sin estado: cada llamada trae la partida completa
(perfil, semilla, duda y elecciones) y el servidor la vuelve a jugar."""

from datetime import date
from functools import lru_cache

from fastapi import APIRouter, HTTPException, Query

from app.schemas.juego import DudasIn, EnJuegoIn, MundoIn, PartidaIn, PesoCvIn, TextoPerfilIn
from app.services import perfil_ia
from app.sim.motor import partida, peso, supuestos, validacion
from app.sim.motor.paquete import paquete
from app.sim.motor.perfil import NIVELES

router = APIRouter(prefix="/juego", tags=["juego"])


@router.get("/catalogo")
def catalogo():
    """Alternativas para llenar el perfil."""
    pq = paquete()
    ocupaciones = {int(f["origen"]): f["origen_nombre"] for f in pq.filas("jobhop_transiciones")}
    return {
        "rubros": [r for r in pq.variables["rubro"]["dominio"] if r],
        "tipos_empleador": pq.variables["tipo_empleador"]["dominio"][:-1],
        "niveles": [{"nivel": i, "nombre": n} for i, n in enumerate(NIVELES)],
        "educacion": pq.variables["edu"]["dominio"],
        "ocupaciones": [{"grupo": g, "nombre": n} for g, n in sorted(ocupaciones.items())],
        "carreras": [
            {"carrera_id": int(f["carrera_id"]), "carrera": f["carrera"], "tipo_institucion": f["tipo_institucion"],
             "area": f["area"]}
            for f in pq.filas("mifuturo_carreras")
        ],
        # sueldo líquido de gente con la misma edad y estudios (ESI 2025): la referencia del slider de sueldo
        "sueldos_ref": [
            {"educacion": f["educacion"], "banda": f["banda"],
             **{p: int(round(float(f[p]), -4)) for p in ("p25", "p50", "p75")}}  # redondeado a $10.000
            for f in pq.filas("esi_perfil_edad_edu")
        ],
    }


@router.get("/supuestos")
def supuestos_del_motor():
    """Cada parámetro del motor con su calidad (dato, mixto o supuesto), su fuente y su país."""
    return supuestos.listar()


@lru_cache(maxsize=4)
def _validacion(n: int, semilla: int) -> dict:
    resultado = validacion.validar(n, semilla, procesos=1)  # sin procesos hijos dentro del servidor
    return {k: v for k, v in resultado.items() if k not in ("fallas", "decisiones")}


@router.get("/validacion")
def validacion_contra_chile(n: int = Query(1000, ge=200, le=5000), semilla: int = Query(0, ge=0)):
    """Una cohorte simulada desde los 18 años comparada con las metas de Chile (ESI, EPS, ENE) y con ELSOC.

    Cada meta dice si es insumo del motor, calibrada o validación de verdad (no entró al motor).
    La primera llamada simula la cohorte (unos segundos con n=1000); después queda en memoria.
    """
    return _validacion(n, semilla)


@router.post("/dudas")
def dudas(body: DudasIn):
    """Decisiones del banco que esta persona puede elegir como su duda inicial."""
    return partida.dudas_posibles(body.perfil.a_perfil())


@router.post("/partida")
def jugar(body: PartidaIn):
    """Estado de la partida: historia, decisión pendiente con lo que vivieron los gemelos, o el cierre."""
    try:
        return partida.vista(
            body.perfil.a_perfil(), body.semilla, body.duda,
            [e.model_dump() for e in body.elecciones], body.gemelos, body.parametros,
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(422, str(error)) from error


@router.post("/mundo")
def ver_mundo(body: MundoIn):
    """Un mundo de la comparación de la decisión pendiente: lo que te pasa en él con cada opción, año por año."""
    try:
        return partida.mundo_pendiente(
            body.perfil.a_perfil(), body.semilla, body.duda,
            [e.model_dump() for e in body.elecciones], body.mundo, body.parametros,
        )
    except (ValueError, KeyError) as error:
        raise HTTPException(422, str(error)) from error


@router.get("/prompt")
def prompt_perfil():
    """El prompt que la persona le pega a su propio Claude para que le arme su documento de perfil."""
    from app.services.perfil_doc import prompt

    return {"prompt": prompt()}


@router.post("/perfil")
def perfil_desde_texto(body: TextoPerfilIn):
    """Claude lee el texto de la persona y llena el perfil para que ella lo revise.

    Devuelve el perfil, qué campos quedaron con un valor por defecto (`supuestos`) y qué dedujo
    Claude sin que estuviera literal (`inferido`). Con 503, el cliente muestra el formulario a mano.
    """
    try:
        pdf = perfil_ia.pdf_desde_base64(body.pdf) if body.pdf else None
        return perfil_ia.perfil_desde_texto(body.texto, date.today().isoformat(), pdf=pdf)
    except perfil_ia.ModeloNoDisponible as error:
        raise HTTPException(503, str(error)) from error
    except ValueError as error:
        raise HTTPException(422, str(error)) from error


@router.post("/peso-cv")
def peso_del_cv(body: PesoCvIn):
    """Lo que vale cada línea de tu CV en tu duda: la misma comparación, con los mismos dados, sin ese dato.

    Devuelve los datos que más mueven el resultado (en cuántos mundos gana cada opción y su sueldo típico,
    con el dato y sin él). Con la misma semilla y gemelos, "con" coincide con la carta de la duda.
    """
    try:
        return peso.peso_cv(body.perfil.a_perfil(), body.duda, body.semilla, body.gemelos)
    except (ValueError, KeyError) as error:
        raise HTTPException(422, str(error)) from error


@router.post("/dudas-en-juego")
def dudas_en_juego(body: EnJuegoIn):
    """De las dudas que sugiere el CV, cuánto se juega la persona en cada una y cuál es la que más.

    Corre la comparación de cada duda (las que no aplican a este perfil se saltan) y marca en
    `mas_en_juego` la de mayor rango entre la mala y la buena suerte, sobre el sueldo típico de quedarse.
    """
    try:
        return peso.en_juego(body.perfil.a_perfil(), tuple(body.dudas), body.semilla, body.gemelos)
    except KeyError as error:
        raise HTTPException(422, f"no existe la decisión {error}") from error
