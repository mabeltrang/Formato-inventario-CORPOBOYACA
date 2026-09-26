"""Cálculos dasométricos y de coordenadas para el FGR-06.

Convenciones (las mismas del inventario de origen):
    DAP (m)  = CAP / π
    AB (m²)  = π · (DAP / 2)²
    ABT (m²) = suma de las AB de todos los fustes
    VT (m³)  = HT · ABT · factor de forma  (misma HT para todos los fustes)
"""

from __future__ import annotations

import math

FACTOR_FORMA_DEFECTO = 0.7


def dap_desde_cap(cap_m: float) -> float:
    """DAP en metros a partir del CAP en metros."""
    return cap_m / math.pi


def area_basal(cap_m: float) -> float:
    """Área basal (m²) de un fuste a partir de su CAP (m)."""
    dap = dap_desde_cap(cap_m)
    return math.pi * (dap / 2) ** 2


def volumen_total(caps_m: list[float], altura_m: float, factor_forma: float = FACTOR_FORMA_DEFECTO) -> float:
    """VT (m³) = HT · Σ AB · ff."""
    abt = sum(area_basal(c) for c in caps_m if c)
    return altura_m * abt * factor_forma


def decimal_a_gms(valor: float, decimales_seg: int = 2) -> tuple[int, int, float]:
    """Convierte grados decimales a (grados, minutos, segundos) en valor absoluto.

    Redondea los segundos y propaga el acarreo (59.999" -> +1').
    """
    x = abs(valor)
    grados = int(x)
    minutos_dec = (x - grados) * 60
    minutos = int(minutos_dec)
    segundos = round((minutos_dec - minutos) * 60, decimales_seg)
    if segundos >= 60:
        segundos = round(segundos - 60, decimales_seg)
        minutos += 1
    if minutos >= 60:
        minutos -= 60
        grados += 1
    return grados, minutos, segundos
