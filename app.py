"""Conversor de inventario forestal → FGR-06 CORPOBOYACÁ (Parte A y Parte B).

Sube el inventario (y opcionalmente el KMZ del predio) y descarga el Excel.
Todos los valores se calculan con los supuestos por defecto de fgr06/parte_b.py.
El precio por m³ se puede escribir en la pestaña Especies (las especies sin precio
de referencia quedan vacías) y pasa directo al Excel; lo demás se ajusta en el Excel.

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import re

import streamlit as st

import pandas as pd

from fgr06 import ErrorFormato, filas_fgr, generar_fgr06, leer_inventario, tabla_arboles
from fgr06.calculos import decimal_a_gms
from fgr06.parte_b import calcular_parte_b
from fgr06.precios import cargar_precios
from fgr06.predio import calcular_relieve, leer_kmz

DECIMALES_SEG = 2

st.set_page_config(page_title="Conversor FGR-06 · CORPOBOYACÁ", page_icon="🌳", layout="wide")


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

tipo = st.radio(
    "Tipo de aprovechamiento",
    ["unico", "domestico"],
    format_func=lambda t: {"unico": "Único · 10 plantas por árbol (15 si está amenazado) · $110.000 c/u",
                           "domestico": "Doméstico · 5 plantas por árbol · $22.000 c/u"}[t],
    horizontal=True,
)
datos_b = calcular_parte_b(inv, cargar_precios(), area_predio_ha=area, relieve=relieve, tipo_aprovechamiento=tipo)

# --- Avisos --------------------------------------------------------------------
_, avisos_coord = filas_fgr(inv, DECIMALES_SEG)
sin_precio = [f.nombre_cientifico for f in datos_b.especies if f.precio is None]
avisos = inv.avisos + avisos_coord + avisos_predio
if sin_precio:
    avisos.append("Sin precio por m³ de referencia: " + ", ".join(sin_precio)
                  + ". Escríbelo en la pestaña *Especies* antes de descargar.")
if kmz is None:
    avisos.append("Sin KMZ: área del predio, altitud y pendiente quedan vacías en el Excel.")

for e in inv.errores:
    st.error(e)
for a in avisos:
    st.warning(a)

vol = sum(a.vt for a in inv.arboles)
m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Árboles", len(inv.arboles))
m2.metric("Volumen total (m³)", f"{vol:.3f}")
m3.metric("Especies", len(datos_b.especies))
m4.metric("Plantas a reponer", datos_b.n_plantas)
m5.metric("Área del predio (ha)", f"{area:.3f}" if area else "—")
st.caption(
    f"**Proyecto:** {inv.proyecto or '—'} · **Propietario:** {inv.propietario or '—'} · "
    f"**Ubicación:** {inv.ubicacion or '—'} · **Fecha:** {inv.fecha or '—'}"
)

zona_descarga = st.container()

# --- Vista rápida ---------------------------------------------------------------
tab_a, tab_esp, tab_b = st.tabs(["Parte A", "Especies", "Parte B"])

with tab_a:
    st.dataframe(tabla_arboles(inv, DECIMALES_SEG), hide_index=True, width="stretch")

with tab_esp:
    st.caption("El precio ($/m³ en pie) es editable: las celdas vacías son especies sin precio de referencia. "
               "Lo que escribas aquí es lo que sale en el Excel.")
    tabla_esp = pd.DataFrame([
        {
            "Nombre científico": f.nombre_cientifico,
            "Nombre común": f.nombre_comun,
            "N° árboles": f.n_arboles,
            "Volumen (m³)": round(f.volumen, 3),
            "Amenaza / veda": f.amenaza,
            "Plantas por árbol": datos_b.plantas_por_arbol_amenazado if f.amenazada else datos_b.plantas_por_arbol,
            "Precio ($/m³)": f.precio,
            "Origen del precio": f.origen_precio if f.precio is not None else "—",
        }
        for f in datos_b.especies
    ])
    editada = st.data_editor(
        tabla_esp,
        hide_index=True, width="stretch",
        disabled=[c for c in tabla_esp.columns if c != "Precio ($/m³)"],
        column_config={
            "Precio ($/m³)": st.column_config.NumberColumn(format="$ %d", min_value=0, step=1000),
        },
        key="precios_especies",
    )
    for f, precio in zip(datos_b.especies, editada["Precio ($/m³)"]):
        if pd.notna(precio) and precio != f.precio:
            f.precio, f.origen_precio = float(precio), "manual"
        elif pd.isna(precio):
            f.precio = None
    valor_total = sum(f.volumen * f.precio for f in datos_b.especies if f.precio)
    faltan = [f.nombre_cientifico for f in datos_b.especies if f.precio is None]
    st.markdown(f"**Valor comercial total:** $ {valor_total:,.0f}"
                + (f" · faltan precios para: {', '.join(faltan)}" if faltan else ""))


def _gms(v):
    g, m, s_ = decimal_a_gms(v, DECIMALES_SEG)
    return f"{g}° {m}' {s_:.2f}\""


with tab_b:
    d = datos_b
    costo_mo = d.jornales_auxiliar * d.valor_jornal_auxiliar + d.jornales_motosierrista * d.valor_jornal_motosierrista
    costo_des = d.desembosque_jornales * d.desembosque_valor_jornal
    costo_ren = d.n_plantas * d.valor_por_planta
    filas = [
        ("1. Sistema asociado", d.sistema),
        ("2. Altitud", f"{d.altitud:.0f} m s. n. m." if d.altitud else "— (sin KMZ)"),
        ("2. Pendiente / topografía", f"{d.pendiente_pct:.2f} % · {d.topografia}" if d.pendiente_pct is not None else "— (sin KMZ)"),
        ("2. Cuerpos de agua", "Sí" if d.cuerpo_agua else "No"),
        ("3. Uso del suelo", ", ".join(f"{k} {v:g} %" for k, v in d.usos_suelo.items() if v)),
        ("3. Área total del predio", f"{d.area_predio_ha:.3f} ha" if d.area_predio_ha else "— (sin KMZ)"),
        ("3. Uso según POT", d.uso_pot),
        ("4. Mano de obra", f"Auxiliar {d.jornales_auxiliar} jornal(es) + motosierrista {d.jornales_motosierrista} → $ {costo_mo:,.0f}"),
        ("4. Desembosque", f"{d.desembosque_sistema}: {d.desembosque_jornales} jornal(es) → $ {costo_des:,.0f}"),
        ("4. Maquinaria e insumos", f"$ {d.valor_maquinaria:,.0f}"),
        ("4. Patio de acopio (árbol central)",
         f"ID {d.acopio_id} · N {_gms(d.acopio[1])} · W {_gms(d.acopio[0])}" if d.acopio else "—"),
        ("5. Plantas a sembrar", f"{d.n_plantas} ({d.n_no_amenazados} × {d.plantas_por_arbol} + {d.n_amenazados} × {d.plantas_por_arbol_amenazado})"),
        ("5. Renovabilidad", f"{d.n_plantas} × $ {d.valor_por_planta:,.0f} = $ {costo_ren:,.0f}"),
        ("6. Costo total aprovechamiento", f"$ {costo_mo + costo_des + d.valor_maquinaria + costo_ren:,.0f}"),
    ]
    st.dataframe(pd.DataFrame(filas, columns=["Campo", "Valor"]), hide_index=True, width="stretch")
    st.markdown("**Texto de compensación para el informe:**")
    st.code(d.texto_compensacion(), language=None, wrap_lines=True)


# --- Descarga (se arma al final para incluir los precios editados) --------------
if inv.arboles:
    with zona_descarga:
        nombre = re.sub(r"[^\w\-]+", "_", inv.proyecto or archivo.name.rsplit(".", 1)[0]).strip("_")
        st.download_button(
            "⬇️ Descargar FGR-06 (Excel)",
            data=generar_fgr06(inv, DECIMALES_SEG, parte_b=datos_b),
            file_name=f"FGR-06_Inventario_{nombre}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            type="primary",
        )
