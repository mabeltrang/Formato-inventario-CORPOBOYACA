# -*- coding: utf-8 -*-
"""
config/generos_cites_excluidos.py

Géneros cuyo listado CITES a rango GENUS trae una anotación
(FullAnnotationEnglish) que restringe el Apéndice a poblaciones de una
región que NO incluye a Colombia. Para estos géneros, el fallback de
género (cites_genero en core/inventario.py y app.py) NO debe aplicarse
a especies colombianas/neotropicales indeterminadas ("Genero sp"),
porque el listado real de CITES no las cubre.

Revisado contra config/Listado_CITES.csv (185 filas rank=GENUS): de
todas las anotaciones con menciones geográficas, solo estas tres
existen en el archivo actual:

  - Cedrela   → "Populations of the Neotropics"        → SÍ cubre Colombia (no se excluye)
  - Dicksonia → "Only the populations of the Americas"  → SÍ cubre Colombia (no se excluye)
  - Diospyros → "Populations of Madagascar"             → NO cubre Colombia (se excluye aquí)

Si en una actualización futura del Listado_CITES.csv aparecen nuevos
géneros con anotación geográfica que no cubra Colombia (ej. "Populations
of Africa", "Only in Asia"), agregarlos aquí.

IMPORTANTE: esta lista es sobre el FALLBACK DE GÉNERO para nombres
indeterminados ("Genero sp"). Si algún día se carga una especie
puntual (ej. "Diospyros ebenum") con match exacto a nivel de especie
en Listado_CITES.csv, esa fila si trae su propia anotación específica
y se respeta tal cual — esta exclusión NO toca matches exactos de
especie, solo el fallback de género.
"""

GENEROS_CITES_EXCLUIDOS_COLOMBIA = {
    'diospyros',  # Apéndice II del género solo cubre "Populations of Madagascar"
}


def genero_cites_aplica_colombia(genero_norm: str) -> bool:
    """
    True si el fallback de género CITES debe aplicarse para este género
    en un proyecto colombiano. False si el género está en la lista de
    exclusión (anotación geográfica que no cubre Colombia).
    """
    return genero_norm.strip().lower() not in GENEROS_CITES_EXCLUIDOS_COLOMBIA
