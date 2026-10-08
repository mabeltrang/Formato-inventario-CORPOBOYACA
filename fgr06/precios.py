"""Precios de referencia de madera en pie ($/m³) por especie.

La tabla vive en plantilla/precios_madera.csv. Búsqueda:
  1. nombre científico exacto (normalizado)
  2. sinónimo → nombre aceptado (plantilla/sinonimos_especies.csv),
     p. ej. Hesperocyparis lusitanica → Cupressus lusitanica
  3. "Genero sp" del mismo género (respaldo, se avisa en la app)
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from .amenazas.nombres import norm_especie

RUTA_PRECIOS = Path(__file__).resolve().parent.parent / "plantilla" / "precios_madera.csv"
RUTA_SINONIMOS = Path(__file__).resolve().parent.parent / "plantilla" / "sinonimos_especies.csv"
COLUMNAS = ["nombre_cientifico", "nombre_comun", "precio_cop_m3_en_pie", "fuente", "fecha"]


def cargar_precios(ruta: Path | str = RUTA_PRECIOS) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype={"fuente": str, "fecha": str})
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = None
    return df[COLUMNAS]


@lru_cache(maxsize=1)
def sinonimos(ruta: Path | str = RUTA_SINONIMOS) -> dict[str, str]:
    """{sinónimo normalizado: nombre aceptado normalizado}."""
    df = pd.read_csv(ruta, dtype=str).dropna()
    return {norm_especie(s): norm_especie(a) for a, s in zip(df["nombre_aceptado"], df["sinonimo"])}


def buscar_precio(df: pd.DataFrame, nombre_cientifico: str) -> tuple[float | None, str]:
    """Devuelve (precio, origen). origen: 'especie', 'sinónimo', 'género' o 'sin precio'."""
    claves = df["nombre_cientifico"].map(norm_especie)
    n = norm_especie(nombre_cientifico)

    def _exacto(nombre: str) -> float | None:
        fila = df[claves == nombre]
        if not fila.empty and pd.notna(fila.iloc[0]["precio_cop_m3_en_pie"]):
            return float(fila.iloc[0]["precio_cop_m3_en_pie"])
        return None

    if (precio := _exacto(n)) is not None:
        return precio, "especie"
    aceptado = sinonimos().get(n)
    if aceptado and (precio := _exacto(aceptado)) is not None:
        return precio, "sinónimo"
    genero = (aceptado or n).split()[0] if n else ""
    for sufijo in ("sp", "spp"):
        fila = df[claves == f"{genero} {sufijo}"]
        if not fila.empty and pd.notna(fila.iloc[0]["precio_cop_m3_en_pie"]):
            return float(fila.iloc[0]["precio_cop_m3_en_pie"]), "género"
    return None, "sin precio"
