"""Genera plantilla/precios_madera.csv con precios de madera EN PIE ($/m³).

Criterio: precio en pie = madera puesta en sitio de proceso menos costos directos
de aprovechamiento y fletes (definición del dictamen fuente).

FUENTE BASE
  López Cadena, B. (2020). Inventario forestal y valoración de madera en pie y
  extraída, Finca San Alfonso (Bolívar, Valle). Dictamen pericial, Juzgado Civil
  del Circuito de Roldanillo, rad. 76-622-31-03-001-2019-00025-00. Lonja de
  Propiedad Raíz de Caldas, RNA 1557. Cuadros 3 y 4 (octubre 2020).
  https://www.ramajudicial.gov.co/documents/36464024/67164864/2019-00025-00+DICTAMEN+2.pdf/cba336b0-6840-46c0-b3ff-af1ef2f1064c
    - Precio en pie aserrío:  $185.000/m³ (pino y eucalipto)
    - Precio en pie pulpa:    $40.000/m³  (pino y eucalipto)
    - Uso: pino 78 % aserrío / 22 % pulpa; eucalipto 52 % aserrío / 48 % pulpa

ACTUALIZACIÓN: IPC total nacional DANE, variación anual 2021–2025.
  Para actualizar a otro año, agregue la variación en IPC_ANUAL y vuelva a correr:
      python plantilla/generar_precios_madera.py

Los valores "homologado" NO vienen de la fuente: se asignan por similitud de
mercado y uso, como estimación del profesional responsable. Revíselos.
"""

from pathlib import Path
import csv

PRECIO_ASERRIO_2020 = 185_000
PRECIO_PULPA_2020 = 40_000
USO_ASERRIO = {"pino": 0.78, "eucalipto": 0.52}   # Cuadro 3 del dictamen

IPC_ANUAL = {2021: 5.62, 2022: 13.12, 2023: 9.28, 2024: 5.20, 2025: 5.10}  # DANE, %
FECHA = "2026-01 (IPC dic-2025)"

factor = 1.0
for v in IPC_ANUAL.values():
    factor *= 1 + v / 100

aserrio = PRECIO_ASERRIO_2020 * factor
pulpa = PRECIO_PULPA_2020 * factor


def ponderado(grupo):
    p = USO_ASERRIO[grupo]
    return round((p * aserrio + (1 - p) * pulpa) / 1000) * 1000


PINO = ponderado("pino")
EUCA = ponderado("eucalipto")
LENA = round(pulpa / 1000) * 1000

F_PINO = "Dictamen López Cadena 2020 (pino: 78 % aserrío $185.000 + 22 % pulpa $40.000 en pie), IPC a dic-2025"
F_EUCA = "Dictamen López Cadena 2020 (eucalipto: 52 % aserrío $185.000 + 48 % pulpa $40.000 en pie), IPC a dic-2025"
F_LENA = "Dictamen López Cadena 2020 (pulpa/leña $40.000 en pie), IPC a dic-2025"
H_PINO = "Homologado a pino (conífera de plantación, mismo mercado) - estimación del profesional"
H_EUCA = "Homologado a eucalipto (latifoliada de plantación con aserrío parcial) - estimación del profesional"
H_LENA = "Homologado a pulpa/leña (sin mercado de aserrío en pie) - estimación del profesional"

# (nombre_cientifico, nombre_comun, precio, fuente)
FILAS = [
    # Pinos
    ("Pinus sp", "Pino", PINO, F_PINO),
    ("Pinus patula", "Pino pátula", PINO, F_PINO),
    ("Pinus radiata", "Pino radiata", PINO, F_PINO),
    ("Pinus oocarpa", "Pino oocarpa", PINO, F_PINO),
    ("Pinus maximinoi", "Pino maximinoi", PINO, F_PINO),
    ("Pinus tecunumanii", "Pino tecunumanii", PINO, F_PINO),
    ("Pinus caribaea", "Pino caribe", PINO, F_PINO),
    ("Pinus kesiya", "Pino kesiya", PINO, F_PINO),
    # Ciprés
    ("Cupressus sp", "Ciprés", PINO, H_PINO),
    ("Cupressus lusitanica", "Ciprés", PINO, H_PINO),
    # Eucaliptos
    ("Eucalyptus sp", "Eucalipto", EUCA, F_EUCA),
    ("Eucalyptus globulus", "Eucalipto blanco", EUCA, F_EUCA),
    ("Eucalyptus camaldulensis", "Eucalipto rojo", EUCA, F_EUCA),
    ("Eucalyptus grandis", "Eucalipto grandis", EUCA, F_EUCA),
    ("Eucalyptus saligna", "Eucalipto saligna", EUCA, F_EUCA),
    ("Eucalyptus viminalis", "Eucalipto", EUCA, F_EUCA),
    ("Eucalyptus tereticornis", "Eucalipto", EUCA, F_EUCA),
    ("Eucalyptus urophylla", "Eucalipto", EUCA, F_EUCA),
    ("Eucalyptus nitens", "Eucalipto", EUCA, F_EUCA),
    ("Corymbia citriodora", "Eucalipto limón", EUCA, H_EUCA),
    # Acacias de tierras altas
    ("Acacia melanoxylon", "Acacia negra / japonesa", EUCA, H_EUCA),
    ("Acacia decurrens", "Acacia gris", LENA, H_LENA),
    ("Acacia mearnsii", "Acacia negra (mearnsii)", LENA, H_LENA),
    ("Acacia baileyana", "Acacia morada", LENA, H_LENA),
    ("Acacia sp", "Acacia", LENA, H_LENA),
    # Otras de plantación / introducidas comunes en Boyacá
    ("Alnus acuminata", "Aliso", EUCA, H_EUCA),
    ("Grevillea robusta", "Gravilea", EUCA, H_EUCA),
    ("Fraxinus uhdei", "Urapán", LENA, H_LENA),
    ("Fraxinus sp", "Fresno / Urapán", LENA, H_LENA),
    ("Fraxinus angustifolia", "Fresno", LENA, H_LENA),
    ("Salix humboldtiana", "Sauce", LENA, H_LENA),
    ("Salix babylonica", "Sauce llorón", LENA, H_LENA),
    ("Salix purpurea", "Sauce púrpura", LENA, H_LENA),
    ("Salix sp", "Sauce", LENA, H_LENA),
    ("Sambucus nigra", "Sauco", LENA, H_LENA),
    ("Schinus molle", "Falso pimiento", LENA, H_LENA),
    ("Ligustrum lucidum", "Jazmín de la China", LENA, H_LENA),
    ("Pittosporum undulatum", "Jazmín de monte", LENA, H_LENA),
    ("Tecoma stans", "Chicalá", LENA, H_LENA),
    ("Croton magdalenensis", "Drago", LENA, H_LENA),
    # Sin precio a propósito: especies en veda o sin referencia defendible
    ("Quercus humboldtii", "Roble andino (veda nacional)", None, "Veda nacional: no se asigna valor comercial"),
    ("Juglans neotropica", "Nogal (veda nacional)", None, "Veda nacional: no se asigna valor comercial"),
    ("Cedrela montana", "Cedro de montaña", None, "Sin referencia en pie"),
]

ruta = Path(__file__).resolve().parent / "precios_madera.csv"
with open(ruta, "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["nombre_cientifico", "nombre_comun", "precio_cop_m3_en_pie", "fuente", "fecha"])
    for nc, com, precio, fuente in FILAS:
        w.writerow([nc, com, precio if precio is not None else "", fuente, FECHA if precio else ""])

print(f"Factor IPC 2021-2025: {factor:.4f}")
print(f"Aserrío en pie: ${aserrio:,.0f}  |  Pulpa/leña en pie: ${pulpa:,.0f}")
print(f"Pino ponderado: ${PINO:,}  |  Eucalipto ponderado: ${EUCA:,}  |  Leña: ${LENA:,}")
print(f"{len(FILAS)} especies escritas en {ruta}")
