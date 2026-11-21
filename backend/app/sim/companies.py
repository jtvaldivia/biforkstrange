"""Empleadores con nombre. Las empresas grandes y las startups son reales; las pymes van
como descripción genérica, porque seis de cada diez asalariados privados trabajan en empresas
de menos de 200 personas (ESI 2025) y casi ninguna tiene un nombre conocido."""

import numpy as np

from app.sim.profile import TAMANOS

GRANDES = {
    "Minería": ["Codelco", "Minera Escondida", "Antofagasta Minerals", "SQM", "Anglo American", "Collahuasi", "Albemarle"],
    "Finanzas y seguros": ["Banco de Chile", "Santander Chile", "Bci", "Itaú", "Scotiabank", "AFP Habitat", "Consorcio"],
    "Información y comunicaciones": ["Entel", "Movistar", "Claro", "WOM", "Sonda", "Mercado Libre", "Globant"],
    "Comercio": ["Falabella", "Cencosud", "Walmart Chile", "Ripley", "SMU", "Copec", "Sodimac"],
    "Salud": ["Clínica Alemana", "RedSalud", "Clínica Las Condes", "Clínica Santa María", "UC Christus", "Cruz Verde"],
    "Enseñanza": ["Pontificia Universidad Católica", "Duoc UC", "Inacap", "Universidad Andrés Bello", "Universidad Adolfo Ibáñez"],
    "Servicios profesionales": ["Deloitte", "EY", "PwC", "KPMG", "Accenture", "Carey", "Arcadis"],
    "Construcción": ["SalfaCorp", "Sigdo Koppers", "Besalco", "Echeverría Izquierdo", "Socovesa", "Ingevec"],
    "Industria manufacturera": ["CMPC", "Arauco", "CCU", "Carozzi", "Concha y Toro", "Embotelladora Andina"],
    "Transporte": ["LATAM Airlines", "Sky Airline", "Starken", "Chilexpress", "Turbus"],
    "Agricultura y pesca": ["Agrosuper", "Hortifrut", "AquaChile", "Camanchaca", "Viña Santa Rita"],
    "Hoteles y restaurantes": ["Sodexo", "Aramark", "Enjoy", "Starbucks Chile", "Juan Maestro"],
    "Artes y entretención": ["Mega", "Chilevisión", "Canal 13"],
    "Servicios administrativos": ["Adecco", "Randstad", "Manpower", "Konecta", "Prosegur"],
    "Otros servicios": ["una empresa grande de servicios"],
}
PYMES = {
    "Minería": ["una contratista minera", "una empresa de mantención minera", "una consultora de geología"],
    "Finanzas y seguros": ["una corredora de seguros", "una cooperativa de ahorro", "una corredora de bolsa"],
    "Información y comunicaciones": ["una agencia de software", "una consultora de datos", "una agencia de marketing digital", "un estudio de diseño web"],
    "Comercio": ["una distribuidora", "una ferretería", "una tienda de ropa", "una importadora"],
    "Salud": ["un centro médico", "una clínica dental", "un laboratorio clínico", "un centro de kinesiología"],
    "Enseñanza": ["un colegio particular subvencionado", "un preuniversitario", "un instituto de idiomas"],
    "Servicios profesionales": ["un estudio contable", "un estudio de abogados", "una consultora chica", "una oficina de arquitectura"],
    "Construcción": ["una constructora mediana", "una empresa de instalaciones eléctricas", "una inmobiliaria chica"],
    "Industria manufacturera": ["una fábrica de alimentos", "una maestranza", "una imprenta", "una fábrica de muebles"],
    "Transporte": ["una empresa de transporte de carga", "una empresa de buses", "una bodega de logística"],
    "Agricultura y pesca": ["un fundo frutícola", "un packing", "una viña familiar"],
    "Hoteles y restaurantes": ["un restaurante del barrio", "un hotel boutique", "una cafetería"],
    "Artes y entretención": ["una productora audiovisual", "un centro cultural", "un gimnasio"],
    "Servicios administrativos": ["una empresa de aseo", "una empresa de seguridad", "un call center"],
    "Otros servicios": ["un taller mecánico", "una peluquería"],
}
# Startups chilenas reales; varias pasaron por Y Combinator (directorio público, sede en Chile)
STARTUPS = ["Fintual", "Fintoc", "Houm", "AgendaPro", "Examedi", "Chipax", "Toku", "Plutto", "RUUF", "Koywe", "Instacrops",
            "NotCo", "Betterfly", "Buk", "Xepelin", "Racional", "Frogmi", "Lemontech"]
PUBLICOS = ["el Servicio de Impuestos Internos", "el Ministerio de Educación", "una municipalidad", "BancoEstado", "Metro de Santiago",
            "el Ministerio de Hacienda", "ChileCompra", "un hospital público", "la Universidad de Chile", "TVN"]

RUBROS = list(GRANDES)
RUBRO_DEFECTO = "Servicios profesionales"
# rubros a los que se mueve un profesional cuando cambia de rubro
_MOVILES = [RUBROS.index(r) for r in ("Finanzas y seguros", "Información y comunicaciones", "Comercio", "Servicios profesionales",
                                     "Industria manufacturera", "Minería", "Salud", "Enseñanza", "Construcción", "Transporte")]

# índice 0 = la empresa con que parte el perfil
NOMBRES = ["tu empresa actual"]
_pools: dict[tuple[int, int], list[int]] = {}
for _r, _rubro in enumerate(RUBROS):
    for _t, _listas in enumerate((STARTUPS, PYMES[_rubro], GRANDES[_rubro], PUBLICOS)):   # mismo orden que TAMANOS
        _ids = []
        for _n in _listas:
            if _n not in NOMBRES:
                NOMBRES.append(_n)
            _ids.append(NOMBRES.index(_n))
        _pools[_r, _t] = _ids
assert len(TAMANOS) == 4
_K = max(len(v) for v in _pools.values())
POOL = np.zeros((len(RUBROS), 4, _K), np.int16)
LARGO = np.zeros((len(RUBROS), 4), np.int16)
for (_r, _t), _ids in _pools.items():
    POOL[_r, _t, : len(_ids)] = _ids
    LARGO[_r, _t] = len(_ids)


def elegir_empresa(rubro: np.ndarray, tam: np.ndarray, u: np.ndarray, actual: np.ndarray) -> np.ndarray:
    """Sortea un empleador del rubro y tamaño dados, distinto del actual."""
    n = LARGO[rubro, tam]
    j = np.minimum((u * n).astype(int), n - 1)
    elegido = POOL[rubro, tam, j]
    otro = POOL[rubro, tam, (j + 1) % n]
    return np.where(elegido == actual, otro, elegido)


def otro_rubro(u: np.ndarray) -> np.ndarray:
    return np.array(_MOVILES)[np.minimum((u * len(_MOVILES)).astype(int), len(_MOVILES) - 1)]


def nombre_empresa(idx: int, propia: str = "") -> str:
    return (propia or NOMBRES[0]) if idx == 0 else NOMBRES[idx]
