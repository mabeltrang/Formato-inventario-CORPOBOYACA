# -*- coding: utf-8 -*-
"""
Base de datos de vedas de flora arbórea en Colombia.
Fuentes:
  - Nacional: Res. 0316/1974 INDERENA, Ley 61/1985, Res. 1602/1995 + 020/1996 MADS
  - CORPOCESAR: Res. 0035 del 28 de enero de 2026 (veda temporal)
  - CDMB, CORANTIOQUIA, CORPOURABA, CORTOLIMA, CARDER, CVC, CORPOCALDAS, CRA:
    inventario MADS/Dirección General Ecosistemas
  - CAR (Cundinamarca): Acuerdo CAR N° 021 de 17 de julio de 2018, Art. 7
  - CORNARE: Acuerdo 404 de 29 de mayo de 2020 (30 especies forestales
    carismáticas de la jurisdicción; lista regional completa pendiente de
    verificar en el texto del acuerdo — se incluyen las especies confirmadas
    en actos administrativos públicos de Cornare que citan expresamente el
    Acuerdo 404/2020)
  - CORPOBOYACÁ, CARSUCRE, CORPORINOQUIA, CORPOGUAJIRA, CORPAMAG, CORPONOR,
    CVS, CARDIQUE, CSB, CORPOCHIVOR, CORPOGUAVIO, CORMACARENA, CDA,
    CORPOAMAZONIA, CODECHOCO, CORPONARIÑO, CORALINA, AMVA: sin veda forestal
    regional propia identificada con lista de especies verificable en fuente
    pública (búsqueda jul/2026 en normatividad publicada de cada corporación);
    aplican únicamente las vedas nacionales (ver VEDAS_NACIONALES). Si se
    conoce el acto administrativo específico de alguna de estas CAR, actualizar
    el campo "spp" y quitar "solo_nacional". CORPORINOQUIA tiene además la
    Res. 200.15.07-0193/2007, que suspende temporalmente el trámite de
    aprovechamientos forestales comerciales en bosque natural (no es una veda
    de especies puntuales, por lo que no se modela aquí como tal).
"""

import unicodedata


def _normalizar(s: str) -> str:
    if not s:
        return ""
    s = str(s)
    s = "".join(
        c for c in unicodedata.normalize("NFD", s)
        if unicodedata.category(c) != "Mn"
    )
    return s.lower().strip()


# ─────────────────────────────────────────────────────────────────────────────
# VEDAS NACIONALES — aplican en toda la jurisdicción colombiana
# Clave: fragmentos del nombre científico en minúsculas sin tildes
# ─────────────────────────────────────────────────────────────────────────────
VEDAS_NACIONALES = [
    {
        "nombre_comun": "Pino colombiano",
        "sci_fragmentos": ["podocarpus rospigliosii", "podocarpus montanus",
                           "podocarpus oleifolius", "retrophyllum rospigliosii",
                           "decussocarpus"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Nogal / Cedro negro",
        "sci_fragmentos": ["juglans"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Hojarasco",
        "sci_fragmentos": ["talauma caricifragans", "talauma caracifragans"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Molinillo",
        "sci_fragmentos": ["talauma hernandezi"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Caparrapí",
        "sci_fragmentos": ["ocotea caparrapi"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida todo el territorio nacional"
    },
    {
        "nombre_comun": "Roble andino",
        "sci_fragmentos": ["quercus humboldtii"],
        "norma": "Res. 0316/1974 INDERENA",
        "nota": "Veda indefinida. Exceptuado en Cauca, Nariño y Antioquia "
                "(sin carbón/leña/pulpa)"
    },
    {
        "nombre_comun": "Palma de cera",
        "sci_fragmentos": ["ceroxylon quindiuense", "ceroxylon alpinum",
                           "ceroxylon vogelianum"],
        "norma": "Ley 61/1985",
        "nota": "Árbol nacional — veda total e indefinida en todo el país"
    },
    {
        "nombre_comun": "Mangles",
        "sci_fragmentos": ["rhizophora", "laguncularia", "avicennia",
                           "pelliciera", "mora megistosperma", "mora oleifera",
                           "conocarpus"],
        "norma": "Res. 1602/1995 + Res. 020/1996 MADS",
        "nota": "Prohíbe aprovechamiento forestal único e impactos directos/indirectos"
    },
]

# ─────────────────────────────────────────────────────────────────────────────
# VEDAS REGIONALES — indexadas por código de CAR
#
# Campo "solo_nacional" (opcional, bool): cuando es True, indica que la CAR
# NO tiene una resolución de veda forestal regional propia identificada.
# En ese caso, consultar_veda() no busca coincidencias en "spp" (vacío) sino
# que, si la especie ya está en veda nacional, refleja esa veda nacional
# también como obligación aplicable en la jurisdicción de esta CAR (para que
# el resultado no aparezca como "sin veda" al seleccionar esta CAR).
# ─────────────────────────────────────────────────────────────────────────────
VEDAS_REGIONALES = {
    "CORPOCESAR": {
        "norma": "Res. 0035 del 28 de enero de 2026 CORPOCESAR",
        "tipo": "temporal",
        "nota": ("Veda temporal. La intervención requiere concepto técnico "
                 "favorable del GIT Forestal de CORPOCESAR + justificación "
                 "de interés público o riesgo (Art. 4° Res. 0035/2026)"),
        "spp": [
            {
                "nombre_comun": "Algarrobillo / Campano",
                "sci_fragmentos": ["samanea saman", "albizia saman",
                                   "pithecellobium saman"],
            },
            {
                "nombre_comun": "Caracolí",
                "sci_fragmentos": ["anacardium excelsum"],
            },
            {
                "nombre_comun": "Roble caribeño",
                "sci_fragmentos": ["tabebuia rosea", "handroanthus roseus"],
            },
            {
                "nombre_comun": "Orejero",
                "sci_fragmentos": ["enterolobium cyclocarpum"],
            },
        ]
    },
    "CDMB": {
        "norma": "Res. 1986/1984 CDMB",
        "tipo": "indefinida",
        "nota": "Prohíbe aprovechamiento de flora silvestre y maderables en su jurisdicción",
        "spp": [
            {"nombre_comun": "Canelo de páramo", "sci_fragmentos": ["drimys granatensis"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Laurel comino / Jigua", "sci_fragmentos": ["nectandra"]},
            {"nombre_comun": "Laurel comino", "sci_fragmentos": ["aniba"]},
            {"nombre_comun": "Yaya / Cargadero", "sci_fragmentos": ["guatteria"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Cedro", "sci_fragmentos": ["cedrela"]},
            {"nombre_comun": "Guayacán", "sci_fragmentos": ["tabebuia", "handroanthus"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Canime", "sci_fragmentos": ["copaifera canime"]},
            {"nombre_comun": "Palma de cera", "sci_fragmentos": ["ceroxylon"]},
        ]
    },
    "CORANTIOQUIA": {
        "norma": "Res. 3183/2000 CORANTIOQUIA",
        "tipo": "indefinida",
        "nota": "Veda y restricción al aprovechamiento en toda la jurisdicción",
        "spp": [
            {"nombre_comun": "Comino crespo", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Cedro de altura", "sci_fragmentos": ["cedrela montana"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Algarrobo", "sci_fragmentos": ["hymenaea courbaril"]},
            {"nombre_comun": "Guayacán amarillo", "sci_fragmentos": ["tabebuia chrysanta", "handroanthus chrysanthus"]},
            {"nombre_comun": "Chaquiro", "sci_fragmentos": ["podocarpus oleifolius"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Cativo", "sci_fragmentos": ["prioria copaifera"]},
            {"nombre_comun": "Diomato", "sci_fragmentos": ["astronium graveolens"]},
        ]
    },
    "CORPOURABA": {
        "norma": "Res. 076395/1995 + Res. 126198/1998 CORPOURABA",
        "tipo": "indefinida",
        "nota": "Prohíbe aprovechamiento bajo cualquier modalidad",
        "spp": [
            {"nombre_comun": "Comino crespo", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Nogal / Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Cativo", "sci_fragmentos": ["prioria copaifera"]},
            {"nombre_comun": "Choibá", "sci_fragmentos": ["dipterix panamensis"]},
            {"nombre_comun": "Ebano", "sci_fragmentos": ["caesalpinia ebano"]},
            {"nombre_comun": "Guayacán hobo", "sci_fragmentos": ["centrolobium paraense"]},
            {"nombre_comun": "Güino", "sci_fragmentos": ["carapa guianensis"]},
        ]
    },
    "CORTOLIMA": {
        "norma": "Acuerdo 10/1983 + Acuerdo 003/1994 CORTOLIMA",
        "tipo": "indefinida",
        "nota": "Veda permanente y total en su jurisdicción",
        "spp": [
            {"nombre_comun": "Cedro", "sci_fragmentos": ["cedrela"]},
            {"nombre_comun": "Pino romerón / hayuelo", "sci_fragmentos": ["podocarpus rospigliosii"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
        ]
    },
    "CARDER": {
        "norma": "Res. 177/1997 CARDER",
        "tipo": "indefinida",
        "nota": "No pueden ser aprovechadas salvo investigación o plantaciones registradas",
        "spp": [
            {"nombre_comun": "Cedro negro", "sci_fragmentos": ["juglans neotropica"]},
            {"nombre_comun": "Comino", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Chanul", "sci_fragmentos": ["humiriastrum procerum"]},
            {"nombre_comun": "Dinde", "sci_fragmentos": ["chlorophora tinctoria", "maclura tinctoria"]},
            {"nombre_comun": "Caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Algarrobo", "sci_fragmentos": ["hymenaea courbaril"]},
            {"nombre_comun": "Cerezo", "sci_fragmentos": ["prunus serotina"]},
        ]
    },
    "CVC": {
        "norma": "Acuerdo 17/1973 CVC",
        "tipo": "indefinida",
        "nota": "Veda al aprovechamiento forestal en todo el Valle del Cauca",
        "spp": [
            {"nombre_comun": "Caracolí", "sci_fragmentos": ["anacardium excelsum"]},
            {"nombre_comun": "Ceiba", "sci_fragmentos": ["ceiba pentandra"]},
            {"nombre_comun": "Samán", "sci_fragmentos": ["samanea saman", "albizia saman"]},
        ]
    },
    "CRC": {
        "norma": "Acuerdo 17/1973 CRC",
        "tipo": "indefinida",
        "nota": "Veda al aprovechamiento de las especies en Cauca",
        "spp": [
            {"nombre_comun": "Samán", "sci_fragmentos": ["albizia saman", "samanea saman"]},
            {"nombre_comun": "Caracolí", "sci_fragmentos": ["anacardium excelsum"]},
            {"nombre_comun": "Ceiba", "sci_fragmentos": ["ceiba pentandra"]},
            {"nombre_comun": "Palma de Cuezco", "sci_fragmentos": ["scheelea butyraceae", "attalea butyracea"]},
        ]
    },
    "CORPOCALDAS": {
        "norma": "Res. 810/1996 CORPOCALDAS",
        "tipo": "indefinida",
        "nota": "Veda indefinida en todo el territorio de Caldas",
        "spp": [
            {"nombre_comun": "Nogal / Cedro negro", "sci_fragmentos": ["juglans"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Caparrapí", "sci_fragmentos": ["ocotea caparrapi"]},
        ]
    },
    "CAS": {
        "norma": "Acuerdo CAS No. 386-19 del 19 de diciembre de 2019",
        "tipo": "indefinida",
        "nota": (
            "Veda permanente al aprovechamiento en la jurisdicción de la CAS. "
            "Incluye especies maderables, coníferas nativas, magnolias, robles y palmas."
        ),
        "spp": [
            {"nombre_comun": "Cedro caoba", "sci_fragmentos": ["swietenia macrophylla"]},
            {"nombre_comun": "Yumbe / Pateguara / Panela quemada",
             "sci_fragmentos": ["caryodaphnopsis cogolloi"]},
            {"nombre_comun": "Comino crespo", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Abarco", "sci_fragmentos": ["cariniana pyriformis"]},
            {"nombre_comun": "Chagüi", "sci_fragmentos": ["caryocar amygdaliferum"]},
            {"nombre_comun": "Sapán", "sci_fragmentos": ["clathrotropis brunnea"]},
            {"nombre_comun": "Marfil", "sci_fragmentos": ["isidodendron tripterocarpum"]},
            {"nombre_comun": "Pino silvestre / Chaquiro",
             "sci_fragmentos": ["podocarpus oleifolius"]},
            {"nombre_comun": "Pino colombiano",
             "sci_fragmentos": ["retrophyllum rospigliosii"]},
            {"nombre_comun": "Pino montañero",
             "sci_fragmentos": ["prumnopitys montana"]},
            {"nombre_comun": "Magnolia", "sci_fragmentos": ["magnolia"]},
            {"nombre_comun": "Roble blanco", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Roble negro", "sci_fragmentos": ["colombobalanus excelsa"]},
            {"nombre_comun": "Palma de cera",
             "sci_fragmentos": ["ceroxylon quindiuense", "ceroxylon quindíuense"]},
            {"nombre_comun": "Palma de Jender", "sci_fragmentos": ["wettinia hirsuta"]},
            {"nombre_comun": "Palma de ramo", "sci_fragmentos": ["ceroxylon vogelianum"]},
            {"nombre_comun": "Palma boba", "sci_fragmentos": ["cyathea hirsuta"]},
        ]
    },
    "CRA": {
        "norma": "Res. 0025/1996 CRA",
        "tipo": "indefinida",
        "nota": "Prohíbe comercialización de productos de mangles en Atlántico",
        "spp": [
            {"nombre_comun": "Mangle amarillo", "sci_fragmentos": ["laguncularia racemosa"]},
            {"nombre_comun": "Mangle colorado", "sci_fragmentos": ["rhizophora mangle"]},
            {"nombre_comun": "Mangle salado", "sci_fragmentos": ["avicennia nitida"]},
        ]
    },
    "CORPOBOYACA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPOBOYACÁ "
                 "que establezca veda forestal regional. En su jurisdicción aplican "
                 "las vedas nacionales vigentes (Res. 0316/1974 INDERENA, Ley 61/1985, "
                 "Res. 1602/1995 + 020/1996 MADS). Si se conoce una resolución "
                 "específica de CORPOBOYACÁ, actualizar este registro."),
        "spp": [],
        "solo_nacional": True,
    },
    "CARSUCRE": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CARSUCRE "
                 "que establezca veda forestal regional. En su jurisdicción "
                 "(incluye manglares del Golfo de Morrosquillo) aplican las vedas "
                 "nacionales vigentes, en particular la veda nacional de mangles "
                 "(Res. 1602/1995 + 020/1996 MADS) y demás vedas nacionales de "
                 "flora arbórea. Si se conoce una resolución específica de "
                 "CARSUCRE, actualizar este registro."),
        "spp": [],
        "solo_nacional": True,
    },
    "CAR": {
        "norma": "Acuerdo CAR N° 021 del 17 de julio de 2018 (Art. 7)",
        "tipo": "indefinida",
        "nota": ("Régimen de uso, aprovechamiento y protección de la flora silvestre y "
                 "los bosques naturales en la jurisdicción de la Corporación Autónoma "
                 "Regional de Cundinamarca. El Art. 7 declara especies vedadas en el "
                 "territorio CAR (coincidentes con vedas nacionales vigentes)."),
        "spp": [
            {"nombre_comun": "Pino colombiano / Pino romerón",
             "sci_fragmentos": ["podocarpus rospigliosii", "podocarpus montanus",
                                 "podocarpus oleifolius"]},
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Palma de cera", "sci_fragmentos": ["ceroxylon quindiuense"]},
        ],
    },
    "CORNARE": {
        "norma": "Acuerdo 404 del 29 de mayo de 2020 CORNARE",
        "tipo": "indefinida",
        "nota": ("Declara veda para especies forestales carismáticas de la jurisdicción "
                 "(Oriente antioqueño) — recopila además vedas nacionales vigentes "
                 "(Res. 0316/1974 INDERENA, Res. 0213/1977 INDERENA para epífitas). "
                 "El acuerdo cubre 30 especies en total; solo se listan aquí las "
                 "confirmadas expresamente en actos administrativos públicos de Cornare "
                 "que citan el Acuerdo 404/2020 — verificar el texto completo del acuerdo "
                 "para el listado íntegro antes de radicar."),
        "spp": [
            {"nombre_comun": "Roble andino", "sci_fragmentos": ["quercus humboldtii"]},
            {"nombre_comun": "Comino crespo", "sci_fragmentos": ["aniba perutilis"]},
            {"nombre_comun": "Chaquiro / Pino romerón", "sci_fragmentos": ["podocarpus oleifolius"]},
            {"nombre_comun": "Caunce", "sci_fragmentos": ["godoya antioquensis", "godoya antioquiensis"]},
        ],
    },
    "CORPORINOQUIA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPORINOQUIA que "
                 "establezca veda forestal regional por especie. En su jurisdicción "
                 "(Meta, Arauca, Casanare, Vichada) aplican las vedas nacionales vigentes. "
                 "Nota aparte: la Res. 200.15.07-0193/2007 suspende temporalmente el "
                 "trámite de aprovechamientos forestales comerciales en bosque natural, "
                 "pero no es una veda de especies puntuales."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOGUAJIRA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPOGUAJIRA que "
                 "establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes, en particular la veda nacional de mangles en zonas costeras."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPAMAG": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPAMAG que "
                 "establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes, en particular la veda nacional de mangles en la Ciénaga "
                 "Grande de Santa Marta."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPONOR": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPONOR (Norte de "
                 "Santander) que establezca veda forestal regional. Aplican las vedas "
                 "nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CVS": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CVS (Valles del "
                 "Sinú y San Jorge, Córdoba) que establezca veda forestal regional. "
                 "Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CARDIQUE": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CARDIQUE (Bolívar) "
                 "que establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes, en particular la veda nacional de mangles."),
        "spp": [],
        "solo_nacional": True,
    },
    "CSB": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CSB (Sur de Bolívar) "
                 "que establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOCHIVOR": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPOCHIVOR (Boyacá) "
                 "que establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOGUAVIO": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPOGUAVIO "
                 "(Cundinamarca — Guavio) que establezca veda forestal regional. "
                 "Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORMACARENA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORMACARENA (área "
                 "de manejo especial La Macarena, Meta) que establezca veda forestal "
                 "regional por especie. Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CDA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CDA (Guainía, "
                 "Guaviare, Vaupés) que establezca veda forestal regional. Aplican las "
                 "vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPOAMAZONIA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPOAMAZONIA "
                 "(Amazonas, Putumayo, Caquetá) que establezca veda forestal regional. "
                 "Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CODECHOCO": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CODECHOCÓ (Chocó) "
                 "que establezca veda forestal regional por especie, más allá de la "
                 "veda nacional histórica de toda la Costa Pacífica declarada por "
                 "INDERENA. Aplican las vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORPONARINO": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORPONARIÑO que "
                 "establezca veda forestal regional. Aplican las vedas nacionales "
                 "vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
    "CORALINA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("No se identificó un acto administrativo propio de CORALINA (San "
                 "Andrés, Providencia y Santa Catalina) que establezca veda forestal "
                 "regional por especie. Aplican las vedas nacionales vigentes, en "
                 "particular la veda nacional de mangles."),
        "spp": [],
        "solo_nacional": True,
    },
    "AMVA": {
        "norma": "N/A — sin resolución de veda forestal regional propia identificada",
        "tipo": "sin veda regional propia (aplica veda nacional)",
        "nota": ("Área Metropolitana del Valle de Aburrá — autoridad ambiental urbana "
                 "para el suelo urbano de los municipios del Valle de Aburrá. No se "
                 "identificó veda forestal regional propia por especie; aplican las "
                 "vedas nacionales vigentes."),
        "spp": [],
        "solo_nacional": True,
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# FUNCIÓN DE CONSULTA PRINCIPAL
# ─────────────────────────────────────────────────────────────────────────────
def consultar_veda(nombre_cientifico: str, nombre_comun: str = "",
                   car: str = "") -> dict:
    """
    Determina si una especie está en veda nacional, regional, o ninguna.

    Args:
        nombre_cientifico: nombre científico de la especie
        nombre_comun: nombre común (opcional, se usa como apoyo de búsqueda)
        car: código de la CAR competente (ej: 'CORPOCESAR', 'CDMB')

    Returns:
        dict con:
            en_veda_nacional (bool)
            en_veda_regional (bool)
            veda_nacional_info (dict | None): norma, nota
            veda_regional_info (dict | None): norma, nota, tipo
            nivel (str): 'nacional', 'regional', 'nacional+regional', 'sin_veda'
            alerta (str): texto para mostrar al usuario
    """
    sci_norm = _normalizar(nombre_cientifico)
    com_norm = _normalizar(nombre_comun)
    texto = sci_norm + " " + com_norm

    # ── Veda nacional ────────────────────────────────────────────────────────
    en_nac = False
    info_nac = None
    for v in VEDAS_NACIONALES:
        match = False
        for frag in v["sci_fragmentos"]:
            frag_n = _normalizar(frag)
            if frag_n in texto:
                match = True
                break
        if match:
            en_nac = True
            info_nac = {"norma": v["norma"], "nota": v["nota"],
                         "nombre_comun": v["nombre_comun"]}
            break

    # ── Veda regional ────────────────────────────────────────────────────────
    en_reg = False
    info_reg = None
    car_norm = car.upper().strip() if car else ""
    if car_norm and car_norm in VEDAS_REGIONALES:
        reg = VEDAS_REGIONALES[car_norm]

        if reg.get("solo_nacional"):
            # Esta CAR no tiene veda regional propia: si la especie ya está
            # en veda nacional, se refleja también aquí para que el resultado
            # de "consultar por esta CAR" no aparezca como sin veda.
            if en_nac:
                en_reg = True
                info_reg = {
                    "norma": info_nac["norma"],
                    "nota": reg["nota"],
                    "tipo": reg["tipo"],
                    "nombre_comun": info_nac["nombre_comun"],
                }
        else:
            for sp in reg["spp"]:
                match = False
                for frag in sp["sci_fragmentos"]:
                    frag_n = _normalizar(frag)
                    if frag_n in texto:
                        match = True
                        break
                if match:
                    en_reg = True
                    info_reg = {
                        "norma": reg["norma"],
                        "nota": reg["nota"],
                        "tipo": reg["tipo"],
                        "nombre_comun": sp["nombre_comun"]
                    }
                    break

    # ── Nivel y alerta ───────────────────────────────────────────────────────
    # Cuando la CAR es "solo_nacional", en_nac y en_reg siempre coinciden
    # (ambos True o ambos False), así que el nivel efectivo es "nacional".
    car_solo_nacional = (
        car_norm in VEDAS_REGIONALES
        and VEDAS_REGIONALES[car_norm].get("solo_nacional", False)
    )

    if en_nac and en_reg and not car_solo_nacional:
        nivel = "nacional+regional"
        alerta = (
            f"⚠️ VEDA NACIONAL ({info_nac['norma']}) + "
            f"VEDA REGIONAL ({info_reg['norma']}). "
            f"{info_reg['nota']}"
        )
    elif en_nac:
        nivel = "nacional"
        if car_solo_nacional:
            alerta = (
                f"⚠️ VEDA NACIONAL ({info_nac['norma']}). {info_nac['nota']}. "
                f"Nota: {car_norm} no tiene veda regional propia identificada; "
                f"aplica esta veda nacional en su jurisdicción."
            )
        else:
            alerta = (
                f"⚠️ VEDA NACIONAL ({info_nac['norma']}). "
                f"{info_nac['nota']}"
            )
    elif en_reg:
        nivel = "regional"
        alerta = (
            f"⚠️ VEDA REGIONAL ({info_reg['norma']}). "
            f"{info_reg['nota']}"
        )
    else:
        nivel = "sin_veda"
        alerta = ""

    return {
        "en_veda_nacional": en_nac,
        "en_veda_regional": en_reg,
        "veda_nacional_info": info_nac,
        "veda_regional_info": info_reg,
        "nivel": nivel,
        "alerta": alerta,
    }


def resumen_vedas_inventario(df_especies, car: str = "") -> dict:
    """
    Dado un DataFrame con columnas 'nombre_cientifico' y 'nombre_comun',
    devuelve un resumen de cuántas especies/individuos están en veda.

    Args:
        df_especies: DataFrame con al menos ['nombre_cientifico', 'n_individuos']
                     y opcionalmente ['nombre_comun']
        car: código CAR del proyecto

    Returns:
        dict con listas de especies en cada categoría y conteos
    """
    resultado = {
        "sin_veda": [],
        "veda_nacional": [],
        "veda_regional": [],
        "veda_nacional_y_regional": [],
        "n_ind_sin_veda": 0,
        "n_ind_veda_nacional": 0,
        "n_ind_veda_regional": 0,
        "n_ind_veda_ambas": 0,
        "hay_alerta": False,
    }

    for _, row in df_especies.iterrows():
        sci = str(row.get("nombre_cientifico", ""))
        nom = str(row.get("nombre_comun", ""))
        n = int(row.get("n_individuos", 1))
        info = consultar_veda(sci, nom, car)
        entrada = {
            "nombre_cientifico": sci,
            "nombre_comun": nom,
            "n_individuos": n,
            "nivel": info["nivel"],
            "alerta": info["alerta"],
        }
        if info["nivel"] == "nacional+regional":
            resultado["veda_nacional_y_regional"].append(entrada)
            resultado["n_ind_veda_ambas"] += n
            resultado["hay_alerta"] = True
        elif info["nivel"] == "nacional":
            resultado["veda_nacional"].append(entrada)
            resultado["n_ind_veda_nacional"] += n
            resultado["hay_alerta"] = True
        elif info["nivel"] == "regional":
            resultado["veda_regional"].append(entrada)
            resultado["n_ind_veda_regional"] += n
            resultado["hay_alerta"] = True
        else:
            resultado["sin_veda"].append(entrada)
            resultado["n_ind_sin_veda"] += n

    return resultado
