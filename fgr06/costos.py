"""Costos de aprovechamiento y compensación (solo árboles aislados, no uso doméstico).

Los costos salen de dos datos del inventario:

- Aprovechamiento = volumen total (m³) × (tarifa de tala + tarifa de transporte menor).
- Compensación = f(N plantas), con N = plantas a sembrar de la Parte B.

Con esos mismos números se llenan:

- la sección 1.1 y la 2.6 del FGR-29 (autodeclaración de costos), y
- las tablas de costos del documento técnico (aprovechamiento y reposición a 3 años),

así el FGR-06, el FGR-29 y el informe no se desfasan. Las tarifas por defecto están en
`Tarifas`; actualízalas ahí una vez al año (en la app no se editan).
"""

from __future__ import annotations

import io
import math
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side

PLANTILLA_FGR29 = Path(__file__).resolve().parent.parent / "plantilla" / "FGR-29_v3_plantilla.xlsx"

MESES = ("Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto",
         "Septiembre", "Octubre", "Noviembre", "Diciembre")


@dataclass
class Tarifas:
    """Formato estándar de costos de compensación (Unergy). Solo dependen de N plantas:
    plántulas (N), tutores (1,5 × N) y reposición (10 % de N). Todo lo demás es fijo."""

    # Aprovechamiento ($/m³ de volumen total)
    tala_m3: float = 100_000
    transporte_menor_m3: float = 90_000
    # Mano de obra siembra inicial: (ítem, unidad, cantidad, valor unidad) — fija
    mano_obra: tuple = (
        ("Rocería", "Jornal", 5, 100_000),
        ("Trazado", "Jornal", 3, 100_000),
        ("Hoyado", "Jornal", 5, 100_000),
        ("Plateo", "Jornal", 5, 100_000),
        ("Transporte y distribución", "Jornal", 3, 100_000),
        ("Siembra", "Jornal", 5, 100_000),
        ("Aplicación de fertilizantes", "Jornal", 3, 100_000),
        ("Marcación y georreferenciación", "Jornal", 3, 205_000),
    )
    # Insumos
    plantula: float = 25_000
    tutores_por_planta: float = 1.5
    tutor: float = 4_000
    insumos_fijos: tuple = (
        ("Fertilizante (100 g/árbol)", "Bulto 25 kg", 5, 70_000),
        ("Micorrizas (50 g/árbol)", "1 kg", 50, 4_000),
        ("Hidroretenedor (5 g hidratado)", "1 kg", 10, 40_000),
        ("Cabuya", "1 rollo", 10, 45_900),
        ("Transporte a sitio de siembra", "Jornal", 10, 200_000),
        ("Placas", "Und", 5, 160_000),
    )
    herramientas: tuple = (
        ("Azadón", "Und", 1, 45_000), ("Pala", "Und", 1, 80_000), ("Pala coca", "Und", 1, 94_000),
        ("Barra", "Und", 1, 150_000), ("Carretilla", "Und", 1, 200_000), ("EPP's", "Und", 1, 150_000),
        ("Limas", "Und", 1, 23_000),
    )
    # Reposición, mantenimiento y monitoreo (3 años)
    pct_reposicion: float = 0.10
    valor_reposicion: float = 520_505             # por individuo repuesto
    mantenimiento_fijo: tuple = (
        ("Control fitosanitario", "", 1, 20_000), ("Micorrizas", "", 1, 4_000), ("Fertilizantes", "", 1, 7_000),
        ("Hidroretenedor", "", 1, 4_000), ("Tutor", "", 1, 4_000), ("Cabuya", "", 1, 25_000),
        ("Transporte a sitio de siembra", "", 1, 200_000), ("Monitoreo de variables", "", 1, 200_000),
        ("Herramientas", "", 1, 59_500),
    )
    # Imprevistos: % sobre el subtotal de reposición, mantenimiento y monitoreo
    pct_imprevistos: float = 0.05

    @property
    def aprovechamiento_m3(self) -> float:
        return self.tala_m3 + self.transporte_menor_m3


@dataclass
class Item:
    item: str
    unidad: str
    cantidad: float
    valor_unidad: float

    @property
    def total(self) -> float:
        return self.cantidad * self.valor_unidad


@dataclass
class Compensacion:
    n_plantas: int
    mano_obra: list[Item]
    insumos: list[Item]
    herramientas: list[Item]
    mantenimiento: list[Item]
    pct_imprevistos: float

    @staticmethod
    def _suma(items: list[Item]) -> float:
        return sum(i.total for i in items)

    @property
    def subtotales(self) -> dict[str, float]:
        return {
            "Mano de obra siembra inicial": self._suma(self.mano_obra),
            "Insumos": self._suma(self.insumos),
            "Herramientas": self._suma(self.herramientas),
            "Reposición, mantenimiento y monitoreo (3 años)": self._suma(self.mantenimiento),
        }

    @property
    def imprevistos(self) -> float:
        # Igual que el formato estándar: 5 % del subtotal de reposición, mantenimiento y monitoreo
        return self._suma(self.mantenimiento) * self.pct_imprevistos

    @property
    def total(self) -> float:
        return sum(self.subtotales.values()) + self.imprevistos

    @property
    def valor_por_planta(self) -> float:
        return self.total / self.n_plantas if self.n_plantas else 0


def costo_aprovechamiento(volumen_m3: float, t: Tarifas) -> list[Item]:
    v = round(volumen_m3, 3)
    return [Item("Tala", "m³", v, t.tala_m3), Item("Transporte menor", "m³", v, t.transporte_menor_m3)]


def costo_compensacion(n: int, t: Tarifas) -> Compensacion:
    """Formato estándar: solo cambian plántulas, tutores, reposición (10 %) e imprevistos."""
    a_items = lambda filas: [Item(*f) for f in filas]  # noqa: E731
    mano_obra = a_items(t.mano_obra)
    insumos = [Item("Plántulas", "Und", n, t.plantula)] + a_items(t.insumos_fijos[:3])
    insumos.append(Item(f"Tutor ({t.tutores_por_planta:g}/árbol)", "Und", math.ceil(n * t.tutores_por_planta), t.tutor))
    insumos += a_items(t.insumos_fijos[3:])
    herramientas = a_items(t.herramientas)
    mantenimiento = [Item(f"Reposición ({t.pct_reposicion:.0%})", "Und", math.ceil(round(n * t.pct_reposicion, 6)),
                          t.valor_reposicion)]
    mantenimiento += a_items(t.mantenimiento_fijo)
    return Compensacion(n, mano_obra, insumos, herramientas, mantenimiento, t.pct_imprevistos)


# ----------------------------------------------------------------------------
# FGR-29
# ----------------------------------------------------------------------------

# Firma del FGR-29 en árboles aislados. En Streamlit Cloud se puede reemplazar con
# st.secrets["firmante_aislados"] (nombre, identificacion, direccion, telefono, cargo).
FIRMANTE_AISLADOS = {
    "nombre": "Eduardo Andrés Ospina Serrano",
    "identificacion": "1.152.200.773",
    "direccion": "Cl 46 # 70 A 65 Laureles - Estadio, Medellín",
    "telefono": "",
    "cargo": "",
}


@dataclass
class DatosFGR29:
    volumen_m3: float
    compensacion: Compensacion
    tarifas: Tarifas
    valor_predio: float | None = None       # valor del contrato de arriendo o de la servidumbre
    canon_anual: float | None = None        # arrendamiento anual del predio
    nombre: str = FIRMANTE_AISLADOS["nombre"]
    identificacion: str = FIRMANTE_AISLADOS["identificacion"]
    direccion: str = FIRMANTE_AISLADOS["direccion"]
    telefono: str = FIRMANTE_AISLADOS["telefono"]
    cargo: str = FIRMANTE_AISLADOS["cargo"]
    fecha: date = field(default_factory=date.today)
    firma_png: bytes | None = None          # firma escaneada (fgr06/firma.py)


# Filas con ítems (cantidad en D, valor unitario en E) de cada parte
FILAS_INVERSION = [*range(10, 18), *range(20, 30), *range(32, 37), *range(39, 48)]
FILAS_OPERACION = [*range(9, 20), *range(22, 26), *range(28, 34), *range(36, 41), *range(43, 49), *range(51, 56)]


def _llenar_fgr29(d: DatosFGR29, plantilla: Path | str = PLANTILLA_FGR29):
    wb = openpyxl.load_workbook(plantilla)
    a, b = wb.worksheets
    anio = d.fecha.year
    a["A6"] = f"PARTE A - COSTOS DE INVERSION             PRECIOS AÑO:         {anio}"
    b["A6"] = f"PARTE B - COSTO ANUAL DE OPERACIÓN                         AÑO:               {anio}"

    # 1.1 Aprovechamiento: volumen × (tala + transporte menor)
    a["D10"] = round(d.volumen_m3, 3)
    a["E10"] = d.tarifas.aprovechamiento_m3
    # 1.4 Predio / servidumbre y compensación (la compensación va solo en 2.6)
    a["E39"] = d.valor_predio or 0
    a["E42"] = 0
    # 2.3 Arrendamiento
    b["E28"] = d.canon_anual or 0
    # 2.6 Compensación
    for celda, valor in zip(("E51", "E52", "E53", "E54"), d.compensacion.subtotales.values()):
        b[celda] = round(valor)
    b["E55"] = d.compensacion.imprevistos
    b["A55"] = f"Imprevistos ({d.compensacion.pct_imprevistos:.0%})"
    b["A54"] = "Reposición, mantenimiento y monitoreo (3 años)"
    # Firma
    b["C62"], b["C63"], b["C64"], b["C65"] = (v or None for v in (d.nombre, d.identificacion, d.direccion,
                                                                  d.telefono))
    b["C67"] = f"{MESES[d.fecha.month - 1]}, {anio}"
    b["C68"] = d.cargo or None
    if d.firma_png:
        from .firma import insertar_firma

        insertar_firma(b, "C66", d.firma_png, alto_px=54)
    return wb


def totales_fgr29(d: DatosFGR29, plantilla: Path | str = PLANTILLA_FGR29) -> dict[str, float]:
    """Totales del FGR-29 (lo mismo que calculan sus fórmulas), para mostrarlos antes de descargar."""
    a, b = _llenar_fgr29(d, plantilla).worksheets

    def _suma(ws, filas):
        tot = 0.0
        for r in filas:
            q, v = ws[f"D{r}"].value, ws[f"E{r}"].value
            if isinstance(q, (int, float)) and isinstance(v, (int, float)):
                tot += q * v
        return tot

    inv, ope = _suma(a, FILAS_INVERSION), _suma(b, FILAS_OPERACION)
    return {"inversion": inv, "operacion": ope, "total": inv + ope}


def generar_fgr29(d: DatosFGR29, plantilla: Path | str = PLANTILLA_FGR29) -> bytes:
    wb = _llenar_fgr29(d, plantilla)
    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()


# ----------------------------------------------------------------------------
# Tablas para el documento técnico
# ----------------------------------------------------------------------------

_fino = Side(style="thin")
_BORDE = Border(left=_fino, right=_fino, top=_fino, bottom=_fino)
_GRIS = PatternFill("solid", fgColor="D9D9D9")
_F = Font(name="Arial", size=10)
_FB = Font(name="Arial", size=10, bold=True)
_PESOS = '"$" #,##0'


def _fila(ws, r, valores, negrita=False, gris=False, formatos=None):
    for col, v in enumerate(valores, 1):
        c = ws.cell(r, col, v)
        c.font, c.border = (_FB if negrita else _F), _BORDE
        c.alignment = Alignment(vertical="center", wrap_text=True)
        if gris:
            c.fill = _GRIS
        if formatos and formatos.get(col):
            c.number_format = formatos[col]


def generar_tablas_informe(volumen_m3: float, comp: Compensacion, t: Tarifas) -> bytes:
    """Tablas de costos del documento técnico, con fórmulas, listas para pegar en Word."""
    wb = openpyxl.Workbook()
    fmt = {3: "#,##0.###", 4: _PESOS, 5: _PESOS}
    encabezado = ["Ítem", "Unidad", "Cantidad", "Valor unitario", "Valor total"]

    # Costos de aprovechamiento
    ws = wb.active
    ws.title = "Costos aprovechamiento"
    _fila(ws, 1, encabezado, negrita=True, gris=True)
    r = 2
    for it in costo_aprovechamiento(volumen_m3, t):
        _fila(ws, r, [it.item, it.unidad, it.cantidad, it.valor_unidad, f"=C{r}*D{r}"], formatos=fmt)
        r += 1
    _fila(ws, r, ["Total", None, None, None, f"=SUM(E2:E{r - 1})"], negrita=True, gris=True, formatos=fmt)

    # Costos de reposición (3 años)
    ws = wb.create_sheet("Costos reposición")
    _fila(ws, 1, encabezado, negrita=True, gris=True)
    r, subtotales = 2, []
    secciones = [
        ("Mano de obra siembra inicial", comp.mano_obra),
        ("Insumos", comp.insumos),
        ("Herramientas", comp.herramientas),
        ("Reposición, mantenimiento y monitoreo (3 años)", comp.mantenimiento),
    ]
    for titulo, items in secciones:
        _fila(ws, r, [titulo, None, None, None, None], negrita=True)
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
        r += 1
        ini = r
        for it in items:
            _fila(ws, r, [it.item, it.unidad, it.cantidad, it.valor_unidad, f"=C{r}*D{r}"], formatos=fmt)
            r += 1
        _fila(ws, r, ["Total", None, None, None, f"=SUM(E{ini}:E{r - 1})"], negrita=True, gris=True, formatos=fmt)
        subtotales.append((titulo, r))
        r += 1
    fila_mant = subtotales[-1][1]          # imprevistos sobre reposición, mantenimiento y monitoreo
    _fila(ws, r, [f"Imprevistos ({comp.pct_imprevistos:.0%})", None, None, comp.pct_imprevistos,
                  f"=E{fila_mant}*D{r}"], negrita=True, formatos={4: "0%", 5: _PESOS})
    r_imp = r
    r += 2
    _fila(ws, r, ["Valor total compensación (3 años)", None, None, None, None], negrita=True, gris=True)
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=5)
    r += 1
    ini = r
    for titulo, fila in subtotales + [(f"Imprevistos ({comp.pct_imprevistos:.0%})", r_imp)]:
        _fila(ws, r, [titulo, None, None, None, f"=E{fila}"], formatos={5: _PESOS})
        ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)
        r += 1
    _fila(ws, r, ["Total", None, None, None, f"=SUM(E{ini}:E{r - 1})"], negrita=True, gris=True, formatos={5: _PESOS})
    ws.merge_cells(start_row=r, start_column=1, end_row=r, end_column=4)

    for hoja in wb.worksheets:
        for col, ancho in zip("ABCDE", (44, 14, 11, 16, 17)):
            hoja.column_dimensions[col].width = ancho

    salida = io.BytesIO()
    wb.save(salida)
    return salida.getvalue()
