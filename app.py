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
from fgr06.costos import (DatosFGR29, Tarifas, costo_aprovechamiento, costo_compensacion, generar_fgr29,
                          generar_tablas_informe, totales_fgr29)
from fgr06.parte_b import calcular_parte_b
from fgr06.precios import cargar_precios
from fgr06.predio import calcular_relieve, leer_kmz

DECIMALES_SEG = 2
LIMITE_DOMESTICO_M3 = 20   # hasta 20 m³: aislados de uso doméstico; más: árboles aislados


def pesos(v: float) -> str:
    """$ 4.164.800 (punto de miles, sin decimales)."""
    return "$ " + f"{v:,.0f}".replace(",", ".")


def num(v: float, dec: int = 3) -> str:
    """21,920 (coma decimal, punto de miles)."""
    return f"{v:,.{dec}f}".replace(",", "_").replace(".", ",").replace("_", ".")

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

vol = sum(a.vt for a in inv.arboles)
detectado = "domestico" if vol <= LIMITE_DOMESTICO_M3 else "unico"
tipo = st.radio(
    "Tipo de aprovechamiento",
    ["unico", "domestico"],
    index=["unico", "domestico"].index(detectado),
    format_func=lambda t: {"unico": "Árboles aislados · FGR-06 + costos (FGR-29)", "domestico": "Aislados de uso doméstico · solo FGR-06"}[t],
    horizontal=True,
    key=f"tipo_{detectado}",   # si cambia el inventario, vuelve a la detección automática
)
st.caption(f"Detectado por volumen: {num(vol)} m³ → **{'aislados de uso doméstico' if detectado == 'domestico' else 'árboles aislados'}** "
           f"(hasta {LIMITE_DOMESTICO_M3} m³ es uso doméstico). Puedes cambiarlo arriba."
           + ("" if tipo == detectado else " ⚠️ Cambiado a mano."))
UNICO = tipo == "unico"
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

m1, m2, m3, m4, m5 = st.columns(5)
m1.metric("Árboles", len(inv.arboles))
m2.metric("Volumen total (m³)", num(vol))
m3.metric("Especies", len(datos_b.especies))
m4.metric("Plantas a reponer", datos_b.n_plantas)
m5.metric("Área del predio (ha)", num(area) if area else "—")
datos_proyecto = [(k, v) for k, v in (("Proyecto", inv.proyecto), ("Propietario", inv.propietario),
                                       ("Ubicación", inv.ubicacion), ("Fecha", inv.fecha)) if v]
if datos_proyecto:
    st.caption(" · ".join(f"**{k}:** {v}" for k, v in datos_proyecto))

zona_descarga = st.container()

# --- Vista rápida ---------------------------------------------------------------
if UNICO:
    tab_a, tab_esp, tab_costos, tab_b = st.tabs(["Parte A", "Especies", "Costos (FGR-29)", "Parte B"])
else:
    tab_a, tab_esp, tab_b = st.tabs(["Parte A", "Especies", "Parte B"])

with tab_a:
    vista_a = tabla_arboles(inv, DECIMALES_SEG)
    for col in [c for c in vista_a.columns if c.startswith("DAP") and not c.startswith("DAP A")]:
        vista_a[col] = vista_a[col].mask(vista_a[col] == 0)   # fustes que no existen: en blanco
    st.dataframe(vista_a, hide_index=True, width="stretch")

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
    st.markdown(f"**Valor comercial total:** {pesos(valor_total)}"
                + (f" · faltan precios para: {', '.join(faltan)}" if faltan else ""))


def _tabla_items(items):
    return pd.DataFrame([{"Ítem": i.item, "Cantidad": f"{num(i.cantidad, 0 if float(i.cantidad).is_integer() else 2)} {i.unidad}",
                          "Valor unitario": pesos(i.valor_unidad), "Total": pesos(i.total)} for i in items])


datos_29 = comp = None
if UNICO:
    with tab_costos:
        st.caption("Los costos salen del volumen (aprovechamiento) y de las plantas a reponer (compensación). "
                   "Con los mismos valores se llenan el FGR-29, la renovabilidad de la Parte B y las tablas "
                   "del documento técnico.")
        st.markdown("**Predio y firma del FGR-29**")
        c1, c2, c3 = st.columns(3)
        valor_predio = c1.number_input("Valor del contrato de arriendo o servidumbre ($)", value=0, step=1_000_000, min_value=0,
                                       help="Va en 1.4 (valor del predio / servidumbre).")
        canon = c2.number_input("Canon de arrendamiento anual ($)", value=0, step=100_000, min_value=0,
                                help="Va en 2.3. Déjalo en 0 si es servidumbre sin canon.")
        fecha = c3.date_input("Fecha")
        t = Tarifas()
        with st.expander("Tarifas base", expanded=False):
            c1, c2, c3, c4 = st.columns(4)
            t.tala_m3 = c1.number_input("Tala ($/m³)", value=int(t.tala_m3), step=5_000)
            t.transporte_menor_m3 = c2.number_input("Transporte menor ($/m³)", value=int(t.transporte_menor_m3), step=5_000)
            t.jornal = c3.number_input("Jornal ($)", value=int(t.jornal), step=5_000)
            t.plantula = c4.number_input("Plántula ($)", value=int(t.plantula), step=1_000)
            st.caption("Rendimientos e insumos: `fgr06/costos.py` → `Tarifas`.")
        aprov = costo_aprovechamiento(vol, t)
        comp = costo_compensacion(datos_b.n_plantas, t)
        # La renovabilidad de la Parte B usa el mismo costo por planta
        datos_b.valor_por_planta = round(comp.valor_por_planta)

        datos_29 = DatosFGR29(vol, comp, t, valor_predio=valor_predio, canon_anual=canon, fecha=fecha)
        with st.expander("Firmante", expanded=False):
            c1, c2 = st.columns(2)
            datos_29.nombre = c1.text_input("Nombre", datos_29.nombre)
            datos_29.identificacion = c2.text_input("Identificación", datos_29.identificacion)
            datos_29.direccion = c1.text_input("Dirección", datos_29.direccion)
            datos_29.telefono = c2.text_input("Teléfono", datos_29.telefono)
            datos_29.cargo = c1.text_input("Cargo / rol", datos_29.cargo)

        total_aprov = sum(i.total for i in aprov)
        st.markdown("**Qué se escribe en el FGR-29**")
        filas_29 = [
            (f"Tala y transporte menor ({num(vol)} m³)", total_aprov),
            ("Contrato de arriendo / servidumbre", valor_predio),
            ("Canon de arrendamiento anual", canon),
            *comp.subtotales.items(),
            (f"Imprevistos ({comp.pct_imprevistos:.0%})", comp.imprevistos),
        ]
        st.dataframe(pd.DataFrame([(c, pesos(v)) for c, v in filas_29 if v], columns=["Concepto", "Valor"]),
                     hide_index=True, width="stretch")
        st.caption("El resto del FGR-29 (obras, maquinaria y operación de la minigranja) son los valores "
                   "estándar de la plantilla.")

        with st.expander(f"Detalle · costos de aprovechamiento ({pesos(total_aprov)})"):
            st.dataframe(_tabla_items(aprov), hide_index=True, width="stretch")
        with st.expander(f"Detalle · costos de reposición, {comp.n_plantas} plantas, 3 años ({pesos(comp.total)})"):
            for titulo, items in (("Mano de obra siembra inicial", comp.mano_obra), ("Insumos", comp.insumos),
                                  ("Herramientas", comp.herramientas),
                                  ("Reposición, mantenimiento y monitoreo (3 años)", comp.mantenimiento)):
                st.caption(f"{titulo} · {pesos(comp.subtotales[titulo])}")
                st.dataframe(_tabla_items(items), hide_index=True, width="stretch")
            st.markdown(f"Imprevistos ({comp.pct_imprevistos:.0%}): **{pesos(comp.imprevistos)}**")


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
        ("4. Mano de obra", f"Auxiliar {d.jornales_auxiliar} jornal(es) + motosierrista {d.jornales_motosierrista} → {pesos(costo_mo)}"),
        ("4. Desembosque", f"{d.desembosque_sistema}: {d.desembosque_jornales} jornal(es) → {pesos(costo_des)}"),
        ("4. Maquinaria e insumos", f"{pesos(d.valor_maquinaria)}"),
        ("4. Patio de acopio (árbol central)",
         f"ID {d.acopio_id} · N {_gms(d.acopio[1])} · W {_gms(d.acopio[0])}" if d.acopio else "—"),
        ("5. Plantas a sembrar", f"{d.n_plantas} ({d.n_no_amenazados} × {d.plantas_por_arbol} + {d.n_amenazados} × {d.plantas_por_arbol_amenazado})"),
        ("5. Renovabilidad", f"{d.n_plantas} × {pesos(d.valor_por_planta)} = {pesos(costo_ren)}"),
        ("6. Costo total aprovechamiento", f"{pesos(costo_mo + costo_des + d.valor_maquinaria + costo_ren)}"),
    ]
    filas = [(k, v) for k, v in filas if not str(v).startswith("—")]   # sin dato: no se muestra
    st.dataframe(pd.DataFrame(filas, columns=["Campo", "Valor"]), hide_index=True, width="stretch")
    st.markdown("**Texto de compensación para el informe:**")
    st.code(d.texto_compensacion(), language=None, wrap_lines=True)


# --- Resumen y descarga (se arma al final para incluir lo editado en las pestañas) ------------
if inv.arboles:
    with zona_descarga:
        nombre = re.sub(r"[^\w\-]+", "_", inv.proyecto or archivo.name.rsplit(".", 1)[0]).strip("_")
        XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        st.subheader("Antes de descargar")
        if UNICO and datos_29 is not None:
            tot29 = totales_fgr29(datos_29)
            total_aprov = sum(i.total for i in costo_aprovechamiento(vol, datos_29.tarifas))
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Aprovechamiento", f"{pesos(total_aprov)}", help=f"{vol:.3f} m³ × tala + transporte menor")
            c2.metric("Compensación (3 años)", f"{pesos(comp.total)}", help=f"{comp.n_plantas} plantas")
            c3.metric("Valor por planta", f"{pesos(comp.valor_por_planta)}", help="Va en la renovabilidad de la Parte B")
            c4.metric("Total FGR-29", f"{pesos(tot29['total'])}",
                      help=f"Inversión {pesos(tot29['inversion'])} + operación {pesos(tot29['operacion'])}")
            if not datos_29.valor_predio and not datos_29.canon_anual:
                st.warning("El valor del contrato de arriendo/servidumbre y el canon están en 0. "
                           "Escríbelos en la pestaña *Costos (FGR-29)* si aplican.")
            st.caption("FGR-06 Parte B, FGR-29 y tablas del informe usan estos mismos valores.")
            b1, b2, b3 = st.columns(3)
            b1.download_button("⬇️ FGR-06 inventario", data=generar_fgr06(inv, DECIMALES_SEG, parte_b=datos_b),
                               file_name=f"FGR-06_Inventario_{nombre}.xlsx", mime=XLSX, type="primary",
                               width="stretch")
            b2.download_button("⬇️ FGR-29 costos", data=generar_fgr29(datos_29),
                               file_name=f"FGR-29_Costos_{nombre}.xlsx", mime=XLSX, type="primary",
                               width="stretch")
            b3.download_button("⬇️ Tablas de costos del informe",
                               data=generar_tablas_informe(vol, comp, datos_29.tarifas),
                               file_name=f"Tablas_costos_informe_{nombre}.xlsx", mime=XLSX, width="stretch")
        else:
            st.caption(f"Aislados de uso doméstico: solo inventario. {len(inv.arboles)} árboles · {vol:.3f} m³ · "
                       f"{datos_b.n_plantas} plantas a reponer.")
            st.download_button("⬇️ FGR-06 inventario", data=generar_fgr06(inv, DECIMALES_SEG, parte_b=datos_b),
                               file_name=f"FGR-06_Inventario_{nombre}.xlsx", mime=XLSX, type="primary")
