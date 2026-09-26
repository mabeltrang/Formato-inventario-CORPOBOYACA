"""Conversor de inventario forestal → FGR-06 CORPOBOYACÁ (Parte A).

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import re

import streamlit as st

from fgr06 import ErrorFormato, filas_fgr, generar_fgr06, leer_inventario, resumen_especies, tabla_arboles
from fgr06.calculos import FACTOR_FORMA_DEFECTO

DECIMALES_SEG = 2

st.set_page_config(page_title="Conversor FGR-06 · CORPOBOYACÁ", page_icon="🌳", layout="wide")

st.title("Conversor de inventario al FGR-06")
st.caption(
    "Sube el inventario en tu formato (hoja *Inventario*) y descarga la **Parte A – Inventario "
    "Forestal al 100 %** del FGR-06 v7 de CORPOBOYACÁ. La Parte B queda en blanco para llenarla a mano."
)

with st.sidebar:
    st.header("Parámetros")
    factor = st.number_input(
        "Factor de forma", min_value=0.1, max_value=1.0, value=FACTOR_FORMA_DEFECTO, step=0.05,
        help="VT = HT × Σ AB de los fustes × factor de forma",
    )
    st.markdown(
        "**Cálculos**  \n"
        "DAP = CAP / π  \n"
        "AB = π · (DAP/2)²  \n"
        "VT = HT · Σ AB · ff  \n"
        f"Segundos de coordenada con {DECIMALES_SEG} decimales."
    )

archivo = st.file_uploader("Inventario forestal (.xlsx)", type=["xlsx"])
if archivo is None:
    st.info("Esperando el archivo…")
    st.stop()

try:
    inv = leer_inventario(archivo, factor_forma=factor)
except ErrorFormato as e:
    st.error(f"El archivo no tiene el formato esperado: {e}")
    st.stop()
except Exception as e:  # noqa: BLE001
    st.error(f"No se pudo leer el archivo: {e}")
    st.stop()

# --- Encabezado del proyecto ------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Árboles", len(inv.arboles))
c2.metric("Volumen total (m³)", f"{sum(a.vt for a in inv.arboles):.3f}")
c3.metric("Especies", len({a.nombre_cientifico for a in inv.arboles}))
c4.metric("Máx. fustes por árbol", inv.max_fustes)
st.write(
    f"**Proyecto:** {inv.proyecto or '—'} · **Propietario:** {inv.propietario or '—'} · "
    f"**Ubicación:** {inv.ubicacion or '—'} · **Fecha:** {inv.fecha or '—'}"
)

# --- Validaciones -------------------------------------------------------------
_, avisos_coord = filas_fgr(inv, DECIMALES_SEG)
avisos = inv.avisos + avisos_coord
if inv.errores:
    with st.expander(f"❌ {len(inv.errores)} error(es): estos árboles NO se incluyen", expanded=True):
        for e in inv.errores:
            st.write(f"- {e}")
if avisos:
    with st.expander(f"⚠️ {len(avisos)} aviso(s) para revisar", expanded=False):
        for a in avisos:
            st.write(f"- {a}")
if not inv.errores and not avisos:
    st.success("Inventario sin errores ni avisos. El VT recalculado coincide con el del Excel.")
if inv.max_fustes > 3:
    st.info(f"Hay árboles con {inv.max_fustes} fustes: se agregan columnas DAP D en adelante al formato.")

tab_arboles, tab_especies = st.tabs(["Vista previa FGR-06", "Búsqueda por especie"])

with tab_arboles:
    st.dataframe(tabla_arboles(inv, DECIMALES_SEG), hide_index=True, width="stretch")

with tab_especies:
    res = resumen_especies(inv)
    busqueda = st.text_input("Buscar especie (nombre común o científico)", placeholder="p. ej. eucalipto")
    if busqueda:
        patron = re.escape(busqueda.strip())
        mascara = res["Nombre científico"].str.contains(patron, case=False) | res["Nombre común"].str.contains(
            patron, case=False
        )
        filtrado = res[mascara]
        if filtrado.empty:
            st.warning("Ninguna especie coincide.")
        else:
            m1, m2, m3 = st.columns(3)
            m1.metric("Árboles", int(filtrado["N° árboles"].sum()))
            m2.metric("Fustes", int(filtrado["Fustes"].sum()))
            m3.metric("Volumen (m³)", f"{filtrado['VT (m³)'].sum():.4f}")
        st.dataframe(filtrado, hide_index=True, width="stretch")
    else:
        st.dataframe(res, hide_index=True, width="stretch")

# --- Descarga -----------------------------------------------------------------
if inv.arboles:
    nombre = re.sub(r"[^\w\-]+", "_", inv.proyecto or archivo.name.rsplit(".", 1)[0]).strip("_")
    st.download_button(
        "⬇️ Descargar FGR-06 (Parte A)",
        data=generar_fgr06(inv, DECIMALES_SEG),
        file_name=f"FGR-06_Inventario_{nombre}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption("La columna ID queda agrupada y oculta al final de la Parte A; se expande con el botón «+».")
