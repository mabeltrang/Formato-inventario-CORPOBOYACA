"""Tablas de resumen para la app (vista previa y búsqueda por especie)."""

from __future__ import annotations

import pandas as pd

from .lector import Inventario


def tabla_arboles(inv: Inventario, decimales_seg: int = 2) -> pd.DataFrame:
    """Vista previa árbol por árbol, tal como irá al FGR-06."""
    from .escritor import filas_fgr

    filas, _ = filas_fgr(inv, decimales_seg)
    n = inv.max_fustes
    registros = []
    for f in filas:
        reg = {"ID": f["id"], "Nombre común": f["nombre"], "Nombre científico": f["cientifico"]}
        for j in range(max(n, 3)):
            reg[f"DAP {chr(65 + j)} (cm)"] = round(f["daps"][j], 2) if j < len(f["daps"]) else 0.0
        reg["HT (m)"] = f["ht"]
        reg["VT (m³)"] = round(f["vol"], 4)
        reg["Latitud"] = f"{f['lat'][0]}° {f['lat'][1]}' {f['lat'][2]:.{decimales_seg}f}\""
        reg["Longitud"] = f"{f['lon'][0]}° {f['lon'][1]}' {f['lon'][2]:.{decimales_seg}f}\""
        registros.append(reg)
    return pd.DataFrame(registros)


def resumen_especies(inv: Inventario) -> pd.DataFrame:
    """Número de árboles, fustes, AB y volumen total por especie."""
    df = pd.DataFrame([
        {
            "Nombre científico": a.nombre_cientifico,
            "Nombre común": a.nombre_comun,
            "Familia": a.familia,
            "Fustes": len(a.caps),
            "AB (m²)": a.abt,
            "VT (m³)": a.vt,
        }
        for a in inv.arboles
    ])
    if df.empty:
        return df
    res = (
        df.groupby("Nombre científico", as_index=False)
        .agg(**{
            "Nombre común": ("Nombre común", lambda s: ", ".join(sorted(set(s)))),
            "Familia": ("Familia", "first"),
            "N° árboles": ("VT (m³)", "size"),
            "Fustes": ("Fustes", "sum"),
            "AB (m²)": ("AB (m²)", "sum"),
            "VT (m³)": ("VT (m³)", "sum"),
        })
        .sort_values("VT (m³)", ascending=False, ignore_index=True)
    )
    return res.round({"AB (m²)": 4, "VT (m³)": 4})
