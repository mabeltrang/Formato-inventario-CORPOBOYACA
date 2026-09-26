# -*- coding: utf-8 -*-
"""
generos_alta_amenaza.py — Géneros de alta amenaza generalizada (Colombia)

Contexto (Manual 2026 / Criterio B):
  Cuando un individuo del inventario queda identificado solo a género
  (ej. "Quercus sp"), la práctica histórica de Unergy —y del sector— ha
  sido reportar "No aplica (NA)" para ese registro, porque el nombre no
  coincide de forma exacta con ninguna fila del catálogo de amenaza
  (especies_amenazadas_co.csv / CITES / IUCN).

  Sin embargo, para un puñado de géneros la práctica anterior subestima
  el riesgo real: son géneros donde, en Colombia, prácticamente TODAS las
  especies nativas están catalogadas en algún grado de amenaza (a
  diferencia de géneros grandes y diversos como Ficus, Cestrum o
  Erythroxylum, donde la mayoría de especies son LC o no evaluadas y un
  "sp." no debería heredar el peor caso del género).

  Este módulo es la ÚNICA fuente que habilita el fallback de género en
  core/inventario.py (_lookup) y en app.py (_consultar_amenaza_sp): si el
  género de un nombre indeterminado ("Genero sp"/"Genero spp") NO está en
  este diccionario, el sistema mantiene el comportamiento histórico
  ("No aplica (NA)" / LC), consistente con los planes de compensación ya
  radicados y aceptados por las CARs.

  Lista inicial propuesta — Miguel debe validarla/ampliarla contra
  literatura y normativa específica antes de darla por definitiva. Cada
  entrada debe quedar sustentada (no es un cálculo automático), para que
  sea defendible ante una CAR si se cuestiona el criterio.
"""

# Género normalizado (sin tildes, minúsculas) → justificación técnica
GENEROS_ALTA_AMENAZA = {
    "quercus": {
        "justificacion": (
            "Colombia tiene una sola especie nativa del género, Quercus "
            "humboldtii (roble andino), categorizada como amenazada. Un "
            "registro 'Quercus sp' en un inventario colombiano "
            "prácticamente solo puede corresponder a esa especie."
        ),
        "fuente": "Res. 1912/2017 MADS; Lista Roja UICN",
    },
    "magnolia": {
        "justificacion": (
            "La mayoría de especies neotropicales de Magnoliaceae "
            "presentes en Colombia (incluye los antiguos géneros "
            "Dugandiodendron y Talauma) están categorizadas en CR o EN "
            "por su rango restringido y la pérdida de hábitat."
        ),
        "fuente": "Res. 1912/2017 MADS; Lista Roja UICN",
    },
    "podocarpus": {
        "justificacion": (
            "Las especies colombianas de Podocarpaceae (incluye géneros "
            "afines como Prumnopitys, Retrophyllum) están, en su "
            "mayoría, catalogadas como amenazadas por sobreexplotación "
            "maderera histórica y crecimiento lento."
        ),
        "fuente": "Res. 1912/2017 MADS; Lista Roja UICN",
    },
    "aniba": {
        "justificacion": (
            "Género del laurel/comino; varias especies colombianas están "
            "amenazadas por sobreexplotación selectiva de madera fina."
        ),
        "fuente": "Res. 1912/2017 MADS; Lista Roja UICN",
    },
    "cedrela": {
        "justificacion": (
            "El género del cedro presenta presión histórica fuerte por "
            "aprovechamiento maderero; aunque no todas las especies "
            "tienen igual grado, la mayoría de registros en inventarios "
            "colombianos corresponden a especies con alguna categoría de "
            "amenaza. Revisar caso a caso si se identifica la especie."
        ),
        "fuente": "Res. 1912/2017 MADS; Lista Roja UICN",
    },
}


def es_genero_alta_amenaza(genero_norm: str) -> bool:
    """True si el género (ya normalizado: sin tildes, minúsculas) está en
    la lista curada de géneros de alta amenaza generalizada."""
    return genero_norm in GENEROS_ALTA_AMENAZA


def info_genero_alta_amenaza(genero_norm: str):
    """Retorna el dict de justificación/fuente para un género curado, o
    None si el género no está en la lista."""
    return GENEROS_ALTA_AMENAZA.get(genero_norm)
