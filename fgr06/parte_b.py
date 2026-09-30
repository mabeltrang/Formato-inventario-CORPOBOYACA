"""FGR-06 – Parte B "Información técnica sobre el Aprovechamiento y Manejo de Árboles Aislados".

`calcular_parte_b` arma los valores por defecto a partir del inventario (y del predio si
se subió el KMZ); la app deja editar todo antes de escribir. `escribir_parte_b` los pone
en las celdas del formato. Las celdas de totales ya son fórmulas de la plantilla.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

import pandas as pd

from .amenazas import consultar_especie
from .calculos import decimal_a_gms
from .lector import Inventario
from .precios import buscar_precio

HOJA_PARTE_B = 1
MAX_ESPECIES = 5  # filas de la tabla de valor comercial (la sección 4 tiene 7)

SISTEMAS = {  # opción -> celda donde va la "x"
    "Árboles de sombrío": "H11",
    "Cultivos misceláneos": "P11",
    "Sist. agrosilvopastoril": "X11",
    "Rastrojo": "AC11",
    "Plantación forestal": "AK11",
    "Cercas vivas": "F13",
    "Linderos": "J13",
    "Carreteras": "O13",
    "Vías férreas": "T13",
    "Canales": "X13",
    "Tierras no cultivadas o abandonadas": "AK13",
}
TOPOGRAFIA = {"Plana": "T17", "Ondulada": "Z17", "Colina": "AE17"}
USOS_SUELO = {  # etiqueta -> celda (la etiqueta y el valor van juntos, como en el formato)
    "Cultivos": "A25",
    "Rastrojo": "E25",
    "Pastos": "I25",
    "Protección Ambiental": "M25",
    "Bosque plantado": "U25",
    "Industrial": "AB25",
}
DESEMBOSQUE = {  # sistema -> fila
    "Extracción manual": 64,
    "Con tracción animal": 65,
    "Con cable aéreo": 66,
    "Mecánico (Tractor)": 67,
    "Otro: Mecánico manual": 68,
}

OBS_DEFECTO = (
    "La madera resultante del aprovechamiento forestal no será extraida del predio, "
    "su propietario destinará su uso dentro del mismo sitio. "
)
# Plantas a sembrar por árbol talado (sin amenaza, amenazado) según el tipo de aprovechamiento
RELACION_SIEMBRA = {
    "unico": (10, 15),      # valores indicados por CORPOBOYACÁ
    "domestico": (5, 5),
}
# Valor por planta: siembra + 2 años de mantenimiento (COP), según el tipo de aprovechamiento
VALOR_POR_PLANTA = {
    "unico": 110_000,
    "domestico": 41_000,
}

ESPECIES_SIEMBRA_DEFECTO = (
    "Myrcia tomentosa, Juglans neotropica, Quercus humboldtii, Alnus acuminata, "
    "Tabebuia chrysantha, Furcraea spp., Weinmannia tomentosa, Ocotea spp., "
    "Pithecellobium dulce, Inga oerstediana y Cedrela montana"
)


@dataclass
class FilaEspecie:
    nombre_comun: str
    nombre_cientifico: str
    n_arboles: int
    volumen: float
    precio: float | None = None
    origen_precio: str = ""
    amenaza: str = ""
    amenazada: bool = False


@dataclass
class DatosParteB:
    # 1. Sistema
    sistema: str = "Tierras no cultivadas o abandonadas"
    # 2. Biofísico
    altitud: float | None = None
    topografia: str = "Plana"
    pendiente_pct: float | None = None
    cuerpo_agua: bool = False
    cuerpo_agua_clase: str = ""
    cuerpo_agua_nombre: str = ""
    fuente_lat: float | None = None
    fuente_lon: float | None = None
    # 3. Uso del suelo
    usos_suelo: dict[str, float] = field(default_factory=lambda: {"Pastos": 100.0})
    uso_otro: str = ""
    area_predio_ha: float | None = None
    uso_pot: str = "Rural"
    # 4. Especies y valores
    especies: list[FilaEspecie] = field(default_factory=list)
    observaciones_valor: str = OBS_DEFECTO
    jornales_auxiliar: int = 1
    valor_jornal_auxiliar: float = 120_000
    jornales_motosierrista: int = 1
    valor_jornal_motosierrista: float = 100_000
    desembosque_sistema: str = "Otro: Mecánico manual"
    desembosque_jornales: int = 1
    desembosque_valor_jornal: float = 120_000
    extraccion_manual: bool = True
    transformacion_motosierra: bool = True
    valor_maquinaria: float = 900_000
    acopio: tuple[float, float] | None = None       # (lon, lat)
    acopio_id: object = None
    observaciones_acopio: str = OBS_DEFECTO
    transporte_m3: float = 0
    transporte_valor_m3: float = 0
    # 5. Renovabilidad
    siembra: bool = True
    plantas_por_arbol: int = 10
    plantas_por_arbol_amenazado: int = 15
    n_no_amenazados: int = 0
    n_amenazados: int = 0
    especies_siembra: str = ESPECIES_SIEMBRA_DEFECTO
    valor_por_planta: float = VALOR_POR_PLANTA["unico"]
    tipo_aprovechamiento: str = "unico"

    @property
    def n_plantas(self) -> int:
        return self.plantas_por_arbol * self.n_no_amenazados + self.plantas_por_arbol_amenazado * self.n_amenazados

    def texto_compensacion(self) -> str:
        if self.plantas_por_arbol == self.plantas_por_arbol_amenazado:
            n = self.n_no_amenazados + self.n_amenazados
            return (
                "Con la finalidad de mitigar el impacto ambiental y recuperar parcialmente los beneficios "
                f"ecológicos de los árboles talados, se propone la siembra de {_numero_letras(self.plantas_por_arbol)} "
                f"({self.plantas_por_arbol}) nuevos individuos por cada árbol talado. "
                f"Para los {n} árboles a aprovechar se sembrarán {self.n_plantas} individuos."
            )
        return (
            "Con la finalidad de mitigar el impacto ambiental y recuperar parcialmente los beneficios "
            f"ecológicos de los árboles talados, se propone la siembra de {_numero_letras(self.plantas_por_arbol)} "
            f"({self.plantas_por_arbol}) nuevos individuos por cada árbol talado que no presente categoría de "
            f"amenaza, y {_numero_letras(self.plantas_por_arbol_amenazado)} ({self.plantas_por_arbol_amenazado}) "
            "por cada uno que sí se encuentre en alguna categoría de amenaza. "
            f"Para los {self.n_no_amenazados + self.n_amenazados} árboles a aprovechar "
            f"({self.n_no_amenazados} sin categoría de amenaza y {self.n_amenazados} amenazados) "
            f"se sembrarán {self.n_plantas} individuos."
        )


def _numero_letras(n: int) -> str:
    palabras = {1: "uno", 2: "dos", 3: "tres", 4: "cuatro", 5: "cinco", 6: "seis", 7: "siete", 8: "ocho",
                9: "nueve", 10: "diez", 11: "once", 12: "doce", 13: "trece", 14: "catorce", 15: "quince",
                16: "dieciséis", 17: "diecisiete", 18: "dieciocho", 19: "diecinueve", 20: "veinte"}
    return palabras.get(n, str(n))


# ----------------------------------------------------------------------------
# Cálculo
# ----------------------------------------------------------------------------

def arbol_central(inv: Inventario):
    """Árbol que minimiza la suma de distancias al resto (medoide). Devuelve el Arbol."""
    arboles = inv.arboles
    if not arboles:
        return None
    lat0 = sum(a.lat for a in arboles) / len(arboles)
    kx = math.cos(math.radians(lat0))
    pts = [(a.lon * kx, a.lat) for a in arboles]
    mejor, mejor_suma = None, float("inf")
    for i, (x1, y1) in enumerate(pts):
        suma = sum(math.hypot(x1 - x2, y1 - y2) for x2, y2 in pts)
        if suma < mejor_suma:
            mejor, mejor_suma = arboles[i], suma
    return mejor


def jornales(n_arboles: int, volumen: float, arboles_por_jornal: float, m3_por_jornal: float) -> int:
    return max(1, math.ceil(max(n_arboles / arboles_por_jornal, volumen / m3_por_jornal)))


def especies_inventario(inv: Inventario, precios: pd.DataFrame, contar_veda: bool = False) -> list[FilaEspecie]:
    grupos: dict[str, FilaEspecie] = {}
    for a in inv.arboles:
        clave = a.nombre_cientifico
        if clave not in grupos:
            estado = consultar_especie(a.nombre_cientifico)
            precio, origen = buscar_precio(precios, a.nombre_cientifico)
            grupos[clave] = FilaEspecie(
                nombre_comun=a.nombre_comun,
                nombre_cientifico=a.nombre_cientifico,
                n_arboles=0,
                volumen=0.0,
                precio=precio,
                origen_precio=origen,
                amenaza=estado.resumen(),
                amenazada=estado.es_amenazada(contar_veda),
            )
        grupos[clave].n_arboles += 1
        grupos[clave].volumen += a.vt
    return sorted(grupos.values(), key=lambda f: f.volumen, reverse=True)


def calcular_parte_b(
    inv: Inventario,
    precios: pd.DataFrame,
    arboles_por_jornal: float = 30,
    m3_por_jornal: float = 8,
    contar_veda: bool = False,
    area_predio_ha: float | None = None,
    relieve=None,
    tipo_aprovechamiento: str = "unico",
) -> DatosParteB:
    d = DatosParteB()
    if tipo_aprovechamiento not in RELACION_SIEMBRA:
        raise ValueError(f"Tipo de aprovechamiento no válido: {tipo_aprovechamiento}")
    d.tipo_aprovechamiento = tipo_aprovechamiento
    d.plantas_por_arbol, d.plantas_por_arbol_amenazado = RELACION_SIEMBRA[tipo_aprovechamiento]
    d.valor_por_planta = VALOR_POR_PLANTA[tipo_aprovechamiento]
    d.especies = especies_inventario(inv, precios, contar_veda)
    n = len(inv.arboles)
    vol = sum(a.vt for a in inv.arboles)
    j = jornales(n, vol, arboles_por_jornal, m3_por_jornal)
    d.jornales_auxiliar = d.jornales_motosierrista = d.desembosque_jornales = j

    central = arbol_central(inv)
    if central:
        d.acopio, d.acopio_id = (central.lon, central.lat), central.id

    d.n_amenazados = sum(f.n_arboles for f in d.especies if f.amenazada)
    d.n_no_amenazados = n - d.n_amenazados

    d.area_predio_ha = area_predio_ha
    if relieve is not None:
        d.altitud = relieve.altitud_msnm
        d.pendiente_pct = relieve.pendiente_pct
        d.topografia = relieve.topografia
    return d


def _filas_tabla(especies: list[FilaEspecie]) -> list[FilaEspecie]:
    """Máximo MAX_ESPECIES filas; si hay más, las menores se agrupan en 'Otras especies'."""
    if len(especies) <= MAX_ESPECIES:
        return especies
    principales, resto = especies[: MAX_ESPECIES - 1], especies[MAX_ESPECIES - 1:]
    vol = sum(f.volumen for f in resto)
    con_precio = [f for f in resto if f.precio is not None]
    precio = (sum(f.precio * f.volumen for f in con_precio) / sum(f.volumen for f in con_precio)) if con_precio else None
    otras = FilaEspecie(
        nombre_comun="Otras especies",
        nombre_cientifico="Otras especies (" + ", ".join(f.nombre_cientifico for f in resto) + ")",
        n_arboles=sum(f.n_arboles for f in resto),
        volumen=vol,
        precio=precio,
        origen_precio="promedio ponderado",
    )
    return principales + [otras]


# ----------------------------------------------------------------------------
# Escritura
# ----------------------------------------------------------------------------

def _x(ws, celda, marcar=True):
    ws[celda] = "x" if marcar else None


def _gms_celdas(ws, fila, cols, valor, decimales=2):
    g, m, s = decimal_a_gms(valor, decimales)
    for col, v, fmt in zip(cols, (g, m, s), ('0"°"', '0"´"', '0.00"´´"')):
        ws[f"{col}{fila}"] = v
        ws[f"{col}{fila}"].number_format = fmt


def escribir_parte_b(wb, d: DatosParteB) -> None:
    ws = wb.worksheets[HOJA_PARTE_B]

    # 1. Sistema asociado
    for celda in SISTEMAS.values():
        ws[celda] = None
    if d.sistema in SISTEMAS:
        _x(ws, SISTEMAS[d.sistema])

    # 2. Características biofísicas
    ws["G17"] = d.altitud
    for celda in TOPOGRAFIA.values():
        ws[celda] = None
    if d.topografia in TOPOGRAFIA:
        _x(ws, TOPOGRAFIA[d.topografia])
    ws["AJ17"] = None if d.pendiente_pct is None else d.pendiente_pct / 100
    ws["AJ17"].number_format = "0.00%"
    _x(ws, "H19", d.cuerpo_agua)
    _x(ws, "J19", not d.cuerpo_agua)
    ws["M19"] = d.cuerpo_agua_clase or None
    ws["Y19"] = d.cuerpo_agua_nombre or None
    if d.cuerpo_agua and d.fuente_lat is not None and d.fuente_lon is not None:
        _gms_celdas(ws, 21, ("M", "Q", "U"), d.fuente_lat)
        _gms_celdas(ws, 21, ("AB", "AF", "AJ"), d.fuente_lon)

    # 3. Uso del suelo
    for etiqueta, celda in USOS_SUELO.items():
        v = d.usos_suelo.get(etiqueta)
        ws[celda] = f"{etiqueta}: {v:g}" if v else f"{etiqueta}:"
    ws["C27"] = d.uso_otro or None
    ws["AC27"] = d.area_predio_ha
    ws["AC27"].number_format = "0.000"
    ws["Q29"] = d.uso_pot or None

    # 4. Aspectos técnicos (7 filas: 34–40)
    filas = _filas_tabla(d.especies)
    for i in range(7):
        r = 34 + i
        f = filas[i] if i < len(filas) else None
        ws[f"A{r}"] = f.n_arboles if f else None
        ws[f"E{r}"] = f.nombre_comun if f else None
        ws[f"Q{r}"] = f.nombre_cientifico if f else None
        ws[f"AH{r}"] = f.volumen if f else None
        ws[f"AH{r}"].number_format = "0.000"
    ws["N42"] = "=AC27"
    ws["N42"].number_format = "0.000"
    ws["AG42"] = "=AC27"
    ws["AG42"].number_format = "0.000"

    # Valor comercial (5 filas: 47–51)
    for i in range(MAX_ESPECIES):
        r = 47 + i
        f = filas[i] if i < len(filas) else None
        ws[f"A{r}"] = f"=IF(Q{34 + i}=\"\",\"\",Q{34 + i})"
        ws[f"O{r}"] = f"=IF(AH{34 + i}=\"\",\"\",AH{34 + i})"
        ws[f"O{r}"].number_format = "0.000"
        ws[f"R{r}"] = f.precio if f else None
        ws[f"AB{r}"] = f'=IF(OR(O{r}="",R{r}=""),0,O{r}*R{r})'
    ws["F53"] = d.observaciones_valor

    # Mano de obra
    ws["O58"], ws["S58"] = d.jornales_auxiliar, d.valor_jornal_auxiliar
    ws["O59"], ws["S59"] = d.jornales_motosierrista, d.valor_jornal_motosierrista

    # Desembosque
    for fila in DESEMBOSQUE.values():
        ws[f"I{fila}"] = ws[f"L{fila}"] = None
    if d.desembosque_sistema in DESEMBOSQUE:
        fila = DESEMBOSQUE[d.desembosque_sistema]
        ws[f"I{fila}"], ws[f"L{fila}"] = d.desembosque_jornales, d.desembosque_valor_jornal

    # Maquinaria e insumos
    _x(ws, "E77", d.extraccion_manual)
    _x(ws, "P81", d.transformacion_motosierra)
    ws["AD81"] = d.valor_maquinaria

    # Patio de acopio (árbol central)
    if d.acopio:
        ws["A86"] = 1
        _gms_celdas(ws, 86, ("E", "G", "I"), d.acopio[1])
        _gms_celdas(ws, 86, ("L", "N", "P"), d.acopio[0])
    ws["F90"] = d.observaciones_acopio

    # Transporte
    ws["E93"], ws["N93"] = d.transporte_m3, d.transporte_valor_m3

    # 5. Renovabilidad
    _x(ws, "AB97", not d.siembra)
    _x(ws, "AJ97", d.siembra)
    ws["E99"] = d.n_plantas if d.siembra else None
    ws["L99"] = d.especies_siembra if d.siembra else None
    ws["AF101"] = d.valor_por_planta
