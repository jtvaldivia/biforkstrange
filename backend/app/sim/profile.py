"""Perfil de entrada del gemelo (formato bifurca.perfil) y lo que el motor infiere de él."""

import json
from dataclasses import dataclass, field
from pathlib import Path

from app.sim.params import P
from app.sim.tables import tablas

NIVELES = ["junior", "semi senior", "senior", "jefatura", "gerencia"]
TAMANOS = ["startup", "pyme", "grande", "estado"]
BIG5 = ("O", "C", "E", "A", "N")

# ocupación ISCO-3 más probable según el rubro, si el perfil no la trae
_OCUP_POR_RUBRO = {
    "Información y comunicaciones": "251", "Finanzas y seguros": "241", "Servicios profesionales": "242",
    "Enseñanza": "233", "Salud": "222", "Comercio": "243", "Construcción": "214", "Minería": "214",
    "Industria manufacturera": "214", "Administración pública": "242", "Transporte": "432",
    "Hoteles y restaurantes": "513", "Agricultura y pesca": "611",
}

# arquetipos de personalidad_y_trabajo.md: z de (O, C, E, A, N, riesgo)
ARQUETIPOS = {
    "Resiliente estable": (0.5, 0.5, 0.5, 0.3, -0.7, 0.0),
    "Explorador emprendedor": (1.2, 0.0, 0.8, -0.3, -0.3, 1.5),
    "Ejecutor responsable": (0.0, 1.2, 0.0, 0.3, -0.3, -0.5),
    "Negociador duro": (0.3, 0.3, 0.5, -1.2, -0.3, 0.5),
    "Colaborador amable": (0.0, 0.3, 0.3, 1.2, 0.0, -0.5),
    "Ansioso cauteloso": (-0.3, 0.3, -0.8, 0.3, 1.2, -1.2),
    "Impulsivo inconstante": (0.3, -1.0, 0.5, -0.5, 0.5, 1.0),
}


@dataclass
class Perfil:
    nombre: str = "Gemelo"
    edad: int = 25
    sexo: str = "h"                      # "h" | "m"
    situacion: str = "trabajando"        # "trabajando" | "buscando"
    edu: str = "universitaria"           # media | tecnica | universitaria | postgrado
    ocupacion: str = "242"               # código ISCO-08 de 3 dígitos
    rubro: str = ""
    tipo_empleador: str = "pyme"
    nivel: int = 1
    antiguedad: float = 2.0
    sueldo: float = 900_000.0            # líquido mensual, CLP
    ahorros: float = 0.0
    deuda_estudios: float = 0.0
    hijos: int = 0
    pareja: bool = False
    contactos: float = 30.0
    riesgo: float = 0.0                  # z: tolerancia al riesgo
    ambicion: float = 0.0                # z
    big5: dict = field(default_factory=lambda: dict.fromkeys(BIG5, 0.0))
    supuestos: list = field(default_factory=list)   # lo que se infirió y no vino en el perfil

    def z(self, rasgo: str) -> float:
        return float(self.big5.get(rasgo, 0.0))

    @property
    def arquetipo(self) -> str:
        v = [self.z(r) for r in BIG5] + [self.riesgo]
        return min(ARQUETIPOS, key=lambda k: sum((a - b) ** 2 for a, b in zip(ARQUETIPOS[k], v)))

    @classmethod
    def desde_dict(cls, d: dict) -> "Perfil":
        tb, sup = tablas(), []
        sueldo = float(d.get("sueldo_liquido_mensual") or d.get("sueldo") or 900_000)
        rubro = d.get("rubro") or ""
        ocup = str(d.get("ocupacion") or "")
        if ocup not in tb.idx:
            ocup = _OCUP_POR_RUBRO.get(rubro, "242")
            sup.append(f"ocupación {ocup} ({tb.nombres[tb.idx[ocup]]}), inferida del rubro; cámbiala con --ocupacion")
        nivel_txt = str(d.get("nivel") or "semi senior").lower().replace("-", " ").replace("ssr", "semi senior")
        nivel = 1 if "semi" in nivel_txt else 0 if "junior" in nivel_txt or "jr" in nivel_txt else 2 if "senior" in nivel_txt or "sr" in nivel_txt else 1
        if "jef" in nivel_txt or "lead" in nivel_txt:
            nivel = 3
        if "geren" in nivel_txt or "direc" in nivel_txt:
            nivel = 4
        inst = str(d.get("institucion") or "").lower()
        edu = d.get("edu") or ("tecnica" if inst in ("cft", "ip", "instituto") else "universitaria" if inst else "media")
        ahorros = d.get("ahorros")
        if ahorros is None:
            ahorros = P.AHORRO_INICIAL_MESES * sueldo
            sup.append(f"ahorros de {P.AHORRO_INICIAL_MESES} sueldos (${ahorros / 1e6:.1f} M), porque el perfil no los trae; cámbialos con --ahorros")
        if d.get("antiguedad") is None:
            sup.append("2 años de antigüedad en el empleo actual")
        big5 = dict.fromkeys(BIG5, 0.0) | {k: float(v) for k, v in (d.get("big5") or {}).items() if k in BIG5}
        if not d.get("big5"):
            sup.append("Big Five en el promedio (no medido); riesgo y ambición sí vienen del perfil")
        tipo = d.get("tipo_empleador") if d.get("tipo_empleador") in TAMANOS else "pyme"
        return cls(
            nombre=d.get("nombre") or "Gemelo", edad=int(d.get("edad") or 25), sexo="m" if str(d.get("sexo", "h")).lower().startswith("m") else "h",
            situacion="buscando" if str(d.get("situacion", "trabajando")).lower() in ("buscando", "cesante") else "trabajando",
            edu=edu, ocupacion=ocup, rubro=rubro, tipo_empleador=tipo, nivel=nivel,
            antiguedad=float(d.get("antiguedad") if d.get("antiguedad") is not None else 2.0), sueldo=sueldo,
            ahorros=float(ahorros), deuda_estudios=float(d.get("deuda_estudios") or 0), hijos=int(d.get("hijos") or 0),
            pareja=bool(d.get("pareja")), contactos=float(d.get("contactos") or P.RED_REF),
            riesgo=(float(d.get("riesgo", 50)) - 50) / 25, ambicion=(float(d.get("ambicion", 50)) - 50) / 25,
            big5=big5, supuestos=sup,
        )

    @classmethod
    def desde_archivo(cls, ruta: str) -> "Perfil":
        return cls.desde_dict(json.loads(Path(ruta).read_text(encoding="utf-8")))
