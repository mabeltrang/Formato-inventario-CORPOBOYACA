"""Precios de referencia de madera en pie ($/m³) por especie.

La tabla vive en plantilla/precios_madera.csv. Búsqueda:
  1. nombre científico exacto (normalizado)
  2. "Genero sp" del mismo género (respaldo, se avisa en la app)
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .amenazas.nombres import norm_especie

RUTA_PRECIOS = Path(__file__).resolve().parent.parent / "plantilla" / "precios_madera.csv"
COLUMNAS = ["nombre_cientifico", "nombre_comun", "precio_cop_m3_en_pie", "fuente", "fecha"]


def cargar_precios(ruta: Path | str = RUTA_PRECIOS) -> pd.DataFrame:
    df = pd.read_csv(ruta, dtype={"fuente": str, "fecha": str})
    for c in COLUMNAS:
        if c not in df.columns:
            df[c] = None
    return df[COLUMNAS]


def buscar_precio(df: pd.DataFrame, nombre_cientifico: str) -> tuple[float | None, str]:
    """Devuelve (precio, origen). origen: 'especie', 'género' o 'sin precio'."""
    claves = df["nombre_cientifico"].map(norm_especie)
    n = norm_especie(nombre_cientifico)
    fila = df[claves == n]
    if not fila.empty and pd.notna(fila.iloc[0]["precio_cop_m3_en_pie"]):
        return float(fila.iloc[0]["precio_cop_m3_en_pie"]), "especie"
    genero = n.split()[0] if n else ""
    for sufijo in ("sp", "spp"):
        fila = df[claves == f"{genero} {sufijo}"]
        if not fila.empty and pd.notna(fila.iloc[0]["precio_cop_m3_en_pie"]):
            return float(fila.iloc[0]["precio_cop_m3_en_pie"]), "género"
    return None, "sin precio"
