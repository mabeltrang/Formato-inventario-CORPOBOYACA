# -*- coding: utf-8 -*-
"""
config/nombres.py

Normalización ÚNICA de nombres científicos, usada tanto por
core/inventario.py (procesamiento de inventario) como por app.py
(pestaña de Consulta de especies amenazadas), para que ambos
matcheen exactamente igual contra los CSV de referencia
(especies_amenazadas_co.csv, Listado_CITES.csv, Listado_UICN.csv).

Antes de este módulo existían DOS implementaciones separadas
(core/inventario.py::_norm y app.py::key = nombre.strip().lower()),
que podían divergir. La de app.py no:
  - quitaba tildes
  - colapsaba espacios internos dobles/múltiples
  - limpiaba espacios "invisibles" (\xa0 non-breaking space, tabs)
    típicos al copiar/pegar nombres desde Excel/Word.

Eso hacía que especies con datos correctos en los CSV (ej. Bowdichia
virgilioides → Least Concern en Listado_UICN.csv) aparecieran como
"No aplica (NA)" en la pestaña de consulta si el nombre venía con
algún espacio "sucio", aunque el mismo nombre procesado por
core/inventario.py sí matcheara bien.
"""

import re
import unicodedata

# Cualquier espacio unicode (incluye \xa0, tabs, etc.) → colapsar a uno solo
_WS_RE = re.compile(r'\s+')


def norm_especie(nombre) -> str:
    """
    Normaliza un nombre científico para matching contra los CSV de
    referencia (MADS, CITES, UICN):
      1. Quita tildes/diacríticos (NFD + filtra marcas de combinación)
      2. Pasa a minúsculas
      3. Colapsa cualquier secuencia de espacios (incluidos \xa0, tabs)
         a un solo espacio
      4. Quita espacios al inicio/final

    Uso: la MISMA función debe usarse para normalizar tanto las claves
    cargadas desde los CSV como el nombre consultado, en ambos módulos
    (core/inventario.py y app.py), para evitar que un lado normalice
    distinto que el otro.
    """
    s = str(nombre)
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.lower()
    s = _WS_RE.sub(' ', s)
    return s.strip()


def es_indeterminado(nombre_norm: str) -> bool:
    """
    True si el nombre normalizado tiene forma 'Genero sp/spp' (indeterminado).
    Recibe el nombre YA normalizado con norm_especie().
    """
    _SP_SUFIJOS = {'sp', 'sp.', 'spp', 'spp.', 'sp1', 'sp2', 'sp3'}
    partes = nombre_norm.strip().split()
    return len(partes) == 2 and partes[1] in _SP_SUFIJOS
