"""Consulta de categoría de amenaza y veda por especie.

Copiado de `mabeltrang/analisis-compensacion-forestal` (commit c0c980d, 2026-09-08):
    config/nombres.py, config/generos_alta_amenaza.py, config/generos_cites_excluidos.py,
    config/vedas.py y los CSV de config/ (MADS Res. 0126/2024, CITES, UICN).
La lógica de `_indices` y `consultar_especie` es la de core/inventario.py de ese repo.
Si se actualizan las listas allá, copiar de nuevo los archivos de `datos/`.

Regla usada para el plan de renovabilidad (Parte B del FGR-06):
    especie AMENAZADA si cumple cualquiera de:
      - MADS (Res. 0126/2024): CR, EN o VU
      - UICN: CR, EN o VU
      - CITES: Apéndice I o II
      - (opcional) veda nacional o regional de la CAR
"""

from __future__ import annotations

import csv
import os
from collections import defaultdict
from dataclasses import dataclass
from functools import lru_cache

import pandas as pd

from .generos_alta_amenaza import es_genero_alta_amenaza
from .generos_cites_excluidos import genero_cites_aplica_colombia
from .nombres import es_indeterminado, norm_especie
from .vedas import consultar_veda

DATOS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "datos")

_UICN_MAP = {
    "critically endangered": "CR",
    "endangered": "EN",
    "vulnerable": "VU",
    "near threatened": "NT",
    "lower risk/near threatened": "NT",
    "lower risk/conservation dependent": "LC",
    "lower risk/least concern": "LC",
    "least concern": "LC",
    "data deficient": "DD",
    "extinct in the wild": "EW",
    "extinct": "EX",
}
_CAT_ORDER = {"CR": 6, "EN": 5, "VU": 4, "NT": 3, "LC": 2, "DD": 1, "EW": 7, "EX": 8}
_CITES_ORD = {"I": 0, "II": 1, "III": 2}

CATEGORIAS_AMENAZA = {"CR", "EN", "VU"}
APENDICES_CITES_AMENAZA = {"I", "II"}


@lru_cache(maxsize=1)
def _indices():
    # ── MADS ──
    amenaza_exact: dict[str, str] = {}
    amenaza_genero: dict[str, str] = defaultdict(lambda: "LC")
    ea = pd.read_csv(os.path.join(DATOS, "especies_amenazadas_co.csv"))
    ea.columns = [norm_especie(c) for c in ea.columns]
    col_nombre = next(c for c in ea.columns if "nombre" in c and "cientifico" in c.replace(" ", ""))
    col_cat = next(c for c in ea.columns if "categoria" in c and "amenaza" in c.replace(" ", ""))
    for _, r in ea.iterrows():
        nombre, cat = norm_especie(str(r[col_nombre])), str(r[col_cat]).strip()
        if nombre and cat:
            amenaza_exact[nombre] = cat
            gen = nombre.split()[0]
            if _CAT_ORDER.get(cat, 0) > _CAT_ORDER.get(amenaza_genero[gen], 0):
                amenaza_genero[gen] = cat

    # ── CITES ──
    cites_exact: dict[str, str] = {}
    cites_genero: dict[str, str] = {}
    with open(os.path.join(DATOS, "Listado_CITES.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rank = (row.get("RankName") or "").strip().upper()
            genus = norm_especie(row.get("Genus") or "")
            species = norm_especie(row.get("Species") or "")
            listing = (row.get("CurrentListing") or "").strip()
            partes = [p.strip() for p in listing.replace("NC", "").split("/") if p.strip() in _CITES_ORD]
            if not partes:
                continue
            ap = sorted(partes, key=lambda x: _CITES_ORD[x])[0]
            if rank in ("SPECIES", "SUBSPECIES") and genus and species:
                nombre = f"{genus} {species}"
                if nombre not in cites_exact or _CITES_ORD[ap] < _CITES_ORD[cites_exact[nombre]]:
                    cites_exact[nombre] = ap
            elif rank == "GENUS" and genus and genero_cites_aplica_colombia(genus):
                if genus not in cites_genero or _CITES_ORD[ap] < _CITES_ORD[cites_genero[genus]]:
                    cites_genero[genus] = ap

    # ── UICN ──
    uicn_exact: dict[str, str] = {}
    with open(os.path.join(DATOS, "Listado_UICN.csv"), newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            nombre_raw = (row.get("scientificName") or "").strip()
            cat = _UICN_MAP.get(norm_especie(row.get("redlistCategory") or ""))
            if nombre_raw and cat:
                uicn_exact[" ".join(norm_especie(nombre_raw).split()[:2])] = cat

    return amenaza_exact, dict(amenaza_genero), cites_exact, cites_genero, uicn_exact


@dataclass
class EstadoEspecie:
    nombre_cientifico: str
    mads: str                  # CR/EN/VU/NT/LC...
    mads_por_genero: bool      # la categoría MADS se heredó del género (Genero sp)
    cites: str | None          # I / II / III / None
    uicn: str | None           # CR/EN/VU/NT/LC/DD... / None
    veda: str                  # 'sin_veda', 'nacional', 'regional', 'nacional+regional'
    veda_alerta: str

    def es_amenazada(self, contar_veda: bool = False) -> bool:
        if self.mads in CATEGORIAS_AMENAZA or self.uicn in CATEGORIAS_AMENAZA:
            return True
        if self.cites in APENDICES_CITES_AMENAZA:
            return True
        return contar_veda and self.veda != "sin_veda"

    def resumen(self) -> str:
        partes = []
        if self.mads in CATEGORIAS_AMENAZA:
            partes.append(f"MADS {self.mads}" + (" (por género)" if self.mads_por_genero else ""))
        if self.uicn in CATEGORIAS_AMENAZA:
            partes.append(f"UICN {self.uicn}")
        if self.cites in APENDICES_CITES_AMENAZA:
            partes.append(f"CITES Ap. {self.cites}")
        if self.veda != "sin_veda":
            partes.append(f"Veda {self.veda}")
        return ", ".join(partes) or "Sin categoría de amenaza"


@lru_cache(maxsize=2048)
def consultar_especie(nombre_cientifico: str, car: str = "CORPOBOYACA") -> EstadoEspecie:
    amenaza_exact, amenaza_genero, cites_exact, cites_genero, uicn_exact = _indices()
    n = norm_especie(nombre_cientifico)
    gen = n.split()[0] if n.split() else ""
    indet = es_indeterminado(n)

    por_genero = False
    if n in amenaza_exact:
        cat_mads = amenaza_exact[n]
    elif indet and es_genero_alta_amenaza(gen):
        cat_mads = amenaza_genero.get(gen, "LC")
        por_genero = cat_mads != "LC"
    else:
        cat_mads = "LC"

    cites_ap = cites_exact.get(n, cites_genero.get(gen))
    cat_uicn = uicn_exact.get(" ".join(n.split()[:2]))
    veda = consultar_veda(nombre_cientifico, car=car)

    return EstadoEspecie(
        nombre_cientifico=nombre_cientifico,
        mads=cat_mads,
        mads_por_genero=por_genero,
        cites=cites_ap,
        uicn=cat_uicn,
        veda=veda["nivel"],
        veda_alerta=veda["alerta"],
    )


__all__ = ["EstadoEspecie", "consultar_especie", "consultar_veda", "norm_especie"]
