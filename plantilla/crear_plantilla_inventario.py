"""Genera plantilla/Plantilla_Inventario_Forestal.xlsx: el inventario en blanco en el
formato propio (el que lee la app), con las fórmulas de DAP, AB, VT, VC y área de copa.

Para árboles con más de 3 fustes: inserta 3 columnas después de "AB C (m2)" con los
encabezados "CAP D (m)", "DAP D (m)", "AB D (m2)" y suma AB D en "AB T (m2)".
La app detecta sola cualquier columna "CAP X (m)".
"""

from pathlib import Path

import openpyxl
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter as L
from openpyxl.worksheet.datavalidation import DataValidation

SALIDA = Path(__file__).with_name("Plantilla_Inventario_Forestal.xlsx")
FILAS = 300          # filas con fórmulas listas
F0 = 6               # primera fila de datos

ENCABEZADOS = [
    "ID", "Cobertura", "Nombre común", "Nombre científico", "Familia",
    "CAP A (m)", "DAP A (m)", "AB A (m2)",
    "CAP B (m)", "DAP B (m)", "AB B (m2)",
    "CAP C (m)", "DAP C (m)", "AB C (m2)",
    "HT (m)", "HC (m)", "AB T (m2)", "VT (m3)", "VC (m3)",
    "diámetro de copa (N-S)", "Diámetro de copa ( E-O)", "Área de copa (m2)",
    "Coordenada X ", "Coordenada Y", "Municipio", "Departamento",
    "Estado fitosanitario", "Medida de manejo",
]
ENTRADAS = {"ID", "Cobertura", "Nombre común", "Nombre científico", "Familia", "CAP A (m)", "CAP B (m)",
            "CAP C (m)", "HT (m)", "diámetro de copa (N-S)", "Diámetro de copa ( E-O)", "Coordenada X ",
            "Coordenada Y", "Municipio", "Departamento", "Estado fitosanitario", "Medida de manejo"}

fino = Side(style="thin")
BORDE = Border(left=fino, right=fino, top=fino, bottom=fino)
FUENTE = Font(name="Arial", size=9)
NEGRITA = Font(name="Arial", size=9, bold=True)
ENTRADA = Font(name="Arial", size=9, color="0000FF")
GRIS = PatternFill("solid", fgColor="D9E1D2")
AMARILLO = PatternFill("solid", fgColor="FFFF00")
CENTRO = Alignment(horizontal="center", vertical="center", wrap_text=True)

wb = openpyxl.Workbook()
ws = wb.active
ws.title = "Inventario"

# --- Datos del proyecto --------------------------------------------------------
ws.merge_cells("A1:C4")
for i, etiqueta in enumerate(["PROYECTO", "PROPIETARIO", "UBICACIÓN", "FECHA"], start=1):
    ws.cell(i, 4, etiqueta).font = NEGRITA
    ws.merge_cells(start_row=i, start_column=5, end_row=i, end_column=10)
    ws.cell(i, 5).fill = AMARILLO
    for c in range(4, 11):
        ws.cell(i, c).border = BORDE
ws["L1"], ws["M1"] = "Factor de forma", 0.7
ws["L1"].font, ws["M1"].font, ws["M1"].fill = NEGRITA, ENTRADA, AMARILLO
ws["L2"] = "Texto azul = dato de campo. Negro = fórmula (no editar)."
ws["L2"].font = Font(name="Arial", size=8, italic=True)

# --- Encabezados -----------------------------------------------------------------
col = {}
for c, t in enumerate(ENCABEZADOS, start=1):
    celda = ws.cell(5, c, t)
    celda.font, celda.fill, celda.alignment, celda.border = NEGRITA, GRIS, CENTRO, BORDE
    col[t.strip()] = L(c)
ws.row_dimensions[5].height = 30

# --- Fórmulas --------------------------------------------------------------------
ff = "$M$1"
for r in range(F0, F0 + FILAS):
    formulas = {}
    for f in "ABC":
        cap, dap = col[f"CAP {f} (m)"], col[f"DAP {f} (m)"]
        formulas[f"DAP {f} (m)"] = f'=IF(N({cap}{r})>0,{cap}{r}/PI(),"")'
        formulas[f"AB {f} (m2)"] = f'=IF(N({cap}{r})>0,PI()*({dap}{r}/2)^2,"")'
    ht, abt = col["HT (m)"], col["AB T (m2)"]
    formulas["HC (m)"] = f'=IF(N({ht}{r})>0,{ht}{r}*2/3,"")'
    formulas["AB T (m2)"] = f'=IF(N({col["CAP A (m)"]}{r})>0,SUM({col["AB A (m2)"]}{r},{col["AB B (m2)"]}{r},{col["AB C (m2)"]}{r}),"")'
    formulas["VT (m3)"] = f'=IF(AND(N({ht}{r})>0,N({abt}{r})>0),{ht}{r}*{abt}{r}*{ff},"")'
    formulas["VC (m3)"] = f'=IF(AND(N({ht}{r})>0,N({abt}{r})>0),{col["HC (m)"]}{r}*{abt}{r}*{ff},"")'
    ns, eo = col["diámetro de copa (N-S)"], col["Diámetro de copa ( E-O)"]
    formulas["Área de copa (m2)"] = f'=IF(AND(N({ns}{r})>0,N({eo}{r})>0),{ns}{r}*{eo}{r},"")'

    for c, t in enumerate(ENCABEZADOS, start=1):
        celda = ws.cell(r, c)
        celda.border = BORDE
        celda.alignment = Alignment(horizontal="center", vertical="center")
        clave = t.strip()
        if clave in formulas:
            celda.value = formulas[clave]
            celda.font = FUENTE
        else:
            celda.font = ENTRADA
        if clave.startswith(("DAP", "AB", "VT", "VC")):
            celda.number_format = "0.0000"
        elif clave.startswith("Coordenada"):
            celda.number_format = "0.000000"
        elif clave.startswith(("CAP", "HT", "HC", "Área", "diám", "Diám")):
            celda.number_format = "0.00"

# --- Totales ---------------------------------------------------------------------
rt = F0 + FILAS
ws.cell(rt, 1, "TOTAL").font = NEGRITA
ws.cell(rt, 2, f'=COUNT({col["CAP A (m)"]}{F0}:{col["CAP A (m)"]}{rt - 1})').font = NEGRITA
for campo in ("VT (m3)", "VC (m3)", "Área de copa (m2)"):
    c = col[campo]
    ws[f"{c}{rt}"] = f"=SUM({c}{F0}:{c}{rt - 1})"
    ws[f"{c}{rt}"].font, ws[f"{c}{rt}"].number_format = NEGRITA, "0.0000"

# --- Listas desplegables ---------------------------------------------------------
for campo, opciones in (("Estado fitosanitario", "Bueno,Regular,Malo,Muerto"),
                        ("Medida de manejo", "Tala,Poda,Permanece,Traslado")):
    dv = DataValidation(type="list", formula1=f'"{opciones}"', allow_blank=True)
    ws.add_data_validation(dv)
    dv.add(f"{col[campo]}{F0}:{col[campo]}{rt - 1}")

# --- Anchos y paneles --------------------------------------------------------------
anchos = {"ID": 6, "Cobertura": 16, "Nombre común": 16, "Nombre científico": 26, "Familia": 14,
          "Coordenada X": 13, "Coordenada Y": 13, "Municipio": 14, "Departamento": 14,
          "Estado fitosanitario": 13, "Medida de manejo": 13}
for c, t in enumerate(ENCABEZADOS, start=1):
    ws.column_dimensions[L(c)].width = anchos.get(t.strip(), 10)
ws.freeze_panes = "F6"

wb.save(SALIDA)
print(f"Creado {SALIDA}")
