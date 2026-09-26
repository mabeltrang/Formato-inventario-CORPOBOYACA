"""Conversor de inventario forestal → FGR-06 CORPOBOYACÁ (Parte A y Parte B).

Sube el inventario (y opcionalmente el KMZ del predio) y descarga el Excel.
Todos los valores se calculan con los supuestos por defecto de fgr06/parte_b.py;
lo que haga falta se ajusta directamente en el Excel.

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import re

import streamlit as st

from fgr06 import ErrorFormato, filas_fgr, generar_fgr06, leer_inventario
from fgr06.parte_b import calcular_parte_b
from fgr06.precios import cargar_precios
from fgr06.predio import calcular_relieve, leer_kmz

DECIMALES_SEG = 2

st.set_page_config(page_title="Conversor FGR-06 · CORPOBOYACÁ", page_icon="🌳", layout="centered")


@st.cache_data(show_spinner="Consultando el modelo de elevación…", ttl=24 * 3600)
def _relieve(datos: bytes):
    return calcular_relieve(leer_kmz(datos))


st.title("Conversor de inventario al FGR-06")
st.caption("Sube el inventario (hoja *Inventario*) y el KMZ del predio, y descarga el FGR-06 v7 de CORPOBOYACÁ.")

archivo = st.file_uploader("Inventario forestal (.xlsx)", type=["xlsx"])
kmz = st.file_uploader("Polígono del predio (.kmz o .kml) · opcional", type=["kmz", "kml"])
if archivo is None:
    st.stop()

try:
    inv = leer_inventario(archivo)
except ErrorFormato as e:
    st.error(f"El archivo no tiene el formato esperado: {e}")
    st.stop()
except Exception as e:  # noqa: BLE001
    st.error(f"No se pudo leer el archivo: {e}")
    st.stop()

# --- Predio -------------------------------------------------------------------
area, relieve, avisos_predio = None, None, []
if kmz is not None:
    datos_kmz = kmz.getvalue()
    try:
        predio = leer_kmz(datos_kmz)
        area = round(predio.area_ha, 4)
        fuera = [str(a.id) for a in inv.arboles if not predio.contiene(a.lon, a.lat)]
        if fuera:
            avisos_predio.append(f"Árboles fuera del polígono del predio: ID {', '.join(fuera)}.")
        try:
            relieve = _relieve(datos_kmz)
        except Exception as e:  # noqa: BLE001
            avisos_predio.append(f"No se pudo calcular altitud y pendiente ({e}); quedan vacías en el Excel.")
    except Exception as e:  # noqa: BLE001
        avisos_predio.append(f"No se pudo leer el KMZ ({e}); el área del predio queda vacía en el Excel.")

datos_b = calcular_parte_b(inv, cargar_precios(), area_predio_ha=area, relieve=relieve)

# --- Avisos --------------------------------------------------------------------
_, avisos_coord = filas_fgr(inv, DECIMALES_SEG)
sin_precio = [f.nombre_cientifico for f in datos_b.especies if f.precio is None]
avisos = inv.avisos + avisos_coord + avisos_predio
if sin_precio:
    avisos.append("Sin precio por m³ (llenar en el Excel): " + ", ".join(sin_precio) + ".")
if kmz is None:
    avisos.append("Sin KMZ: área del predio, altitud y pendiente quedan vacías en el Excel.")

for e in inv.errores:
    st.error(e)
for a in avisos:
    st.warning(a)

vol = sum(a.vt for a in inv.arboles)
resumen = f"**{len(inv.arboles)} árboles · {vol:.3f} m³ · {datos_b.n_plantas} plantas a reponer**"
if area:
    resumen += f" · predio {area:.3f} ha"
if relieve:
    resumen += f" · {relieve.altitud_msnm:.0f} m s. n. m. · pendiente {relieve.pendiente_pct:.1f} %"
st.markdown(resumen)

if inv.arboles:
    nombre = re.sub(r"[^\w\-]+", "_", inv.proyecto or archivo.name.rsplit(".", 1)[0]).strip("_")
    st.download_button(
        "⬇️ Descargar FGR-06 (Excel)",
        data=generar_fgr06(inv, DECIMALES_SEG, parte_b=datos_b),
        file_name=f"FGR-06_Inventario_{nombre}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
