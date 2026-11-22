"""Constantes y formato de texto que comparten todos los subcomandos."""

ANCHO = 100
ANCHO_BARRA = 30
EDAD_MIN, EDAD_MAX = 18, 59  # el mismo rango que acepta la API
FUENTES = "Fuentes: EPS 2024, Chile (término del empleo y cesantía); CVs de Flandes (duración y destinos)."


class EntradaInvalida(Exception):
    """Lo que escribió la persona no sirve; el mensaje se le muestra tal cual."""


# ── formato ──────────────────────────────────────────────────────────────────


def _pct(p: float) -> str:
    """Porcentaje entero; lo que existe pero redondea a cero se muestra como <1%."""
    if 0 < p < 0.005:
        return "<1%"
    return f"{round(p * 100)}%"


def _de_cada_100(partes: list[float]) -> list[int]:
    """Reparte round(100 * suma) entre las partes sin que el redondeo descuadre el total."""
    total = round(sum(partes) * 100)
    exactos = [p * 100 for p in partes]
    enteros = [int(x) for x in exactos]
    por_resto = sorted(range(len(partes)), key=lambda i: exactos[i] - enteros[i], reverse=True)
    for i in por_resto[: max(total - sum(enteros), 0)]:
        enteros[i] += 1
    return enteros


def _duracion(anios: float) -> str:
    meses = round(anios * 12)
    a, m = divmod(meses, 12)
    partes = []
    if a:
        partes.append("1 año" if a == 1 else f"{a} años")
    if m or not a:
        partes.append("1 mes" if m == 1 else f"{m} meses")
    return " y ".join(partes)


def _miles(x: float) -> str:
    return f"{round(x / 1000):,}".replace(",", ".")


def _pesos(x: float) -> str:
    return "$" + f"{round(x):,}".replace(",", ".")


def _cortar(texto: str, ancho: int) -> str:
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def _barras(filas: list[tuple[str, float]], sangria: str = "  ") -> list[str]:
    """Una línea por fila: nombre, barra proporcional a la probabilidad y porcentaje."""
    ancho_nombre = max(len(n) for n, _ in filas)
    mayor = max(p for _, p in filas) or 1.0
    ancho_barra = min(ANCHO_BARRA, ANCHO - len(sangria) - ancho_nombre - 2 - 5)
    lineas = []
    for nombre, p in filas:
        barra = "█" * max(round(p / mayor * ancho_barra), 1 if p > 0 else 0)
        lineas.append(f"{sangria}{nombre:<{ancho_nombre}}  {barra:<{ancho_barra}} {_pct(p):>4}")
    return lineas
