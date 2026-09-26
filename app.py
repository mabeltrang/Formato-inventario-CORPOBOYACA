"""Conversor de inventario forestal → FGR-06 CORPOBOYACÁ (Parte A y Parte B).

Ejecutar:  streamlit run app.py
"""

from __future__ import annotations

import re

import pandas as pd
import streamlit as st

from fgr06 import ErrorFormato, filas_fgr, generar_fgr06, leer_inventario, resumen_especies, tabla_arboles
from fgr06.amenazas import consultar_especie
from fgr06.calculos import FACTOR_FORMA_DEFECTO
from fgr06.parte_b import DESEMBOSQUE, SISTEMAS, TOPOGRAFIA, USOS_SUELO, calcular_parte_b, jornales
from fgr06.precios import COLUMNAS, cargar_precios
from fgr06.predio import calcular_relieve, leer_kmz

DECIMALES_SEG = 2

st.set_page_config(page_title="Conversor FGR-06 · CORPOBOYACÁ", page_icon="🌳", layout="wide")


@st.cache_data(show_spinner=False)
def _leer_kmz(datos: bytes):
    return leer_kmz(datos)


@st.cache_data(show_spinner="Consultando el modelo de elevación…", ttl=24 * 3600)
def _relieve(datos: bytes):
    return calcular_relieve(leer_kmz(datos))


st.title("Conversor de inventario al FGR-06")
st.caption(
    "Sube el inventario en tu formato (hoja *Inventario*) y descarga el FGR-06 v7 de CORPOBOYACÁ "
    "en Excel editable: **Parte A** (inventario al 100 %) y, si quieres, **Parte B** (información técnica)."
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

vol_total = sum(a.vt for a in inv.arboles)

# --- Encabezado del proyecto ------------------------------------------------
c1, c2, c3, c4 = st.columns(4)
c1.metric("Árboles", len(inv.arboles))
c2.metric("Volumen total (m³)", f"{vol_total:.3f}")
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

tab_a, tab_esp, tab_b = st.tabs(["Parte A · vista previa", "Especies y amenaza", "Parte B"])

# =============================================================================
# Parte A
# =============================================================================
with tab_a:
    st.dataframe(tabla_arboles(inv, DECIMALES_SEG), hide_index=True, width="stretch")

# =============================================================================
# Especies
# =============================================================================
with tab_esp:
    res = resumen_especies(inv)
    estados = {s: consultar_especie(s) for s in res["Nombre científico"]}
    res["Amenaza / veda"] = res["Nombre científico"].map(lambda s: estados[s].resumen())
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
    st.caption(
        "Amenaza según MADS Res. 0126/2024, UICN y CITES (mismas listas de la app de compensación). "
        "Se considera amenazada si es CR, EN o VU (MADS o UICN) o CITES Apéndice I o II."
    )

# =============================================================================
# Parte B
# =============================================================================
with tab_b:
    incluir_b = st.toggle("Llenar la Parte B en el Excel", value=True)

    # --- Predio (KMZ) ---------------------------------------------------------
    st.subheader("Predio")
    kmz = st.file_uploader("Polígono del predio (.kmz o .kml)", type=["kmz", "kml"])
    area_kmz, relieve = None, None
    if kmz is not None:
        datos_kmz = kmz.getvalue()
        try:
            predio = _leer_kmz(datos_kmz)
            area_kmz = round(predio.area_ha, 4)
            fuera = [a.id for a in inv.arboles if not predio.contiene(a.lon, a.lat)]
            st.write(f"Área del polígono: **{area_kmz:.4f} ha** ({len(predio.poligonos)} polígono(s)).")
            if fuera:
                st.warning(f"{len(fuera)} árbol(es) quedan fuera del predio: ID {', '.join(map(str, fuera))}.")
            else:
                st.success("Todos los árboles están dentro del predio.")
            try:
                relieve = _relieve(datos_kmz)
                st.write(
                    f"Altitud media **{relieve.altitud_msnm:.0f} m s. n. m.**, pendiente media "
                    f"**{relieve.pendiente_pct:.2f} %** → {relieve.topografia} "
                    f"({relieve.n_puntos} puntos, {relieve.fuente})."
                )
                st.caption("Con predios de pocas hectáreas la pendiente del DEM es indicativa; ajústala si tienes topografía.")
            except Exception as e:  # noqa: BLE001
                st.warning(f"No se pudo calcular altitud y pendiente automáticamente ({e}). Ingrésalas a mano.")
        except Exception as e:  # noqa: BLE001
            st.error(f"No se pudo leer el KMZ: {e}")

    # --- Parámetros de cálculo ---------------------------------------------------
    st.subheader("Rendimientos y amenaza")
    r1, r2, r3 = st.columns(3)
    arb_jornal = r1.number_input("Árboles por jornal", min_value=1.0, value=30.0, step=5.0,
                                 help="Supuesto editable, no es un valor normativo.")
    m3_jornal = r2.number_input("m³ por jornal", min_value=0.5, value=8.0, step=0.5,
                                help="Supuesto editable, no es un valor normativo.")
    contar_veda = r3.checkbox("Contar especies en veda como amenazadas (15:1)", value=False)
    n_jorn = jornales(len(inv.arboles), vol_total, arb_jornal, m3_jornal)
    st.caption(f"Jornales calculados por actividad: **{n_jorn}** = máx(árboles ÷ {arb_jornal:g}, m³ ÷ {m3_jornal:g}), mínimo 1.")

    # --- Precios -----------------------------------------------------------------
    st.subheader("Precios de la madera en pie ($/m³)")
    precios = cargar_precios()
    base = calcular_parte_b(inv, precios, arb_jornal, m3_jornal, contar_veda, area_kmz, relieve)
    tabla_precios = pd.DataFrame(
        [{"Nombre científico": f.nombre_cientifico, "Nombre común": f.nombre_comun,
          "Volumen (m³)": round(f.volumen, 3), "Precio ($/m³)": f.precio, "Origen": f.origen_precio}
         for f in base.especies]
    )
    editada = st.data_editor(
        tabla_precios, hide_index=True, width="stretch",
        disabled=["Nombre científico", "Nombre común", "Volumen (m³)", "Origen"],
        column_config={"Precio ($/m³)": st.column_config.NumberColumn(format="$ %d", min_value=0)},
    )
    precio_editado = dict(zip(editada["Nombre científico"], editada["Precio ($/m³)"]))
    sin_precio = [s for s, p in precio_editado.items() if pd.isna(p)]
    if sin_precio:
        st.warning("Sin precio: " + ", ".join(sin_precio) + ". Escríbelo en la tabla.")
    # CSV actualizado para subir al repo
    actualizado = precios.copy()
    for f in base.especies:
        p = precio_editado.get(f.nombre_cientifico)
        if pd.isna(p) or (f.precio is not None and float(p) == f.precio and f.origen_precio == "especie"):
            continue
        mask = actualizado["nombre_cientifico"].str.lower() == f.nombre_cientifico.lower()
        if mask.any():
            actualizado.loc[mask, "precio_cop_m3_en_pie"] = float(p)
            actualizado.loc[mask, "fuente"] = "Editado en la app"
        else:
            actualizado.loc[len(actualizado)] = [f.nombre_cientifico, f.nombre_comun, float(p), "Editado en la app", ""]
    st.download_button(
        "Descargar precios_madera.csv actualizado", actualizado[COLUMNAS].to_csv(index=False).encode("utf-8"),
        file_name="precios_madera.csv", mime="text/csv",
        help="Reemplaza plantilla/precios_madera.csv en el repo para que queden guardados.",
    )

    # --- Formulario ----------------------------------------------------------------
    st.subheader("Datos del formato")
    with st.expander("1–3. Sistema, características biofísicas y uso del suelo", expanded=True):
        f1, f2, f3 = st.columns(3)
        sistemas = list(SISTEMAS)
        sistema = f1.selectbox("Sistema asociado", sistemas, index=sistemas.index(base.sistema))
        altitud = f2.number_input("Altitud (m s. n. m.)", min_value=0.0, value=float(base.altitud or 0), step=1.0)
        pendiente = f3.number_input("Pendiente (%)", min_value=0.0, value=float(base.pendiente_pct or 0), step=0.1)
        topos = list(TOPOGRAFIA)
        topografia = f1.selectbox("Topografía", topos, index=topos.index(base.topografia))
        area_predio = f2.number_input("Área total del predio (ha)", min_value=0.0,
                                      value=float(base.area_predio_ha or 0), step=0.001, format="%.3f")
        uso_pot = f3.text_input("Uso principal del suelo (POT/EOT)", value=base.uso_pot)

        agua = st.checkbox("Hay cuerpos de agua", value=False)
        if agua:
            a1, a2, a3, a4 = st.columns(4)
            clase = a1.text_input("Clase", placeholder="Quebrada, nacimiento…")
            nombre_agua = a2.text_input("Nombre")
            f_lat = a3.number_input("Latitud fuente (decimal)", value=0.0, format="%.6f")
            f_lon = a4.number_input("Longitud fuente (decimal)", value=0.0, format="%.6f")
        else:
            clase = nombre_agua = ""
            f_lat = f_lon = None

        st.markdown("**Uso actual del suelo (%)**")
        cols_uso = st.columns(len(USOS_SUELO) + 1)
        usos = {}
        for col, etiqueta in zip(cols_uso, USOS_SUELO):
            usos[etiqueta] = col.number_input(etiqueta, min_value=0.0, max_value=100.0,
                                              value=float(base.usos_suelo.get(etiqueta, 0)), step=5.0)
        uso_otro = cols_uso[-1].text_input("Otro")
        if abs(sum(usos.values()) - 100) > 0.01:
            st.warning(f"El uso del suelo suma {sum(usos.values()):g} %, no 100 %.")

    with st.expander("4. Mano de obra, desembosque, maquinaria y acopio"):
        g1, g2, g3, g4 = st.columns(4)
        j_aux = g1.number_input("Jornales auxiliar motosierra", min_value=0, value=int(base.jornales_auxiliar))
        v_aux = g2.number_input("Valor jornal auxiliar ($)", min_value=0.0, value=float(base.valor_jornal_auxiliar), step=5000.0)
        j_mot = g3.number_input("Jornales motosierrista", min_value=0, value=int(base.jornales_motosierrista))
        v_mot = g4.number_input("Valor jornal motosierrista ($)", min_value=0.0, value=float(base.valor_jornal_motosierrista), step=5000.0)
        opciones_des = list(DESEMBOSQUE)
        des_sis = g1.selectbox("Sistema de desembosque", opciones_des, index=opciones_des.index(base.desembosque_sistema))
        des_j = g2.number_input("Jornales desembosque", min_value=0, value=int(base.desembosque_jornales))
        des_v = g3.number_input("Valor jornal desembosque ($)", min_value=0.0, value=float(base.desembosque_valor_jornal), step=5000.0)
        maq = g4.number_input("Valor maquinaria e insumos ($)", min_value=0.0, value=float(base.valor_maquinaria), step=50000.0)
        obs = st.text_area("Observaciones (valor comercial y acopio)", value=base.observaciones_valor)
        t1, t2 = st.columns(2)
        trans_m3 = t1.number_input("Transporte: cantidad (m³)", min_value=0.0, value=0.0)
        trans_v = t2.number_input("Transporte: valor por m³ ($)", min_value=0.0, value=0.0, step=5000.0)
        if base.acopio:
            st.caption(f"Patio de acopio = árbol central, ID {base.acopio_id} "
                       f"(X {base.acopio[0]:.6f}, Y {base.acopio[1]:.6f}).")

    with st.expander("5. Renovabilidad del recurso forestal", expanded=True):
        h1, h2, h3 = st.columns(3)
        ppa = h1.number_input("Plantas por árbol sin amenaza", min_value=0, value=int(base.plantas_por_arbol))
        ppa_am = h2.number_input("Plantas por árbol amenazado", min_value=0, value=int(base.plantas_por_arbol_amenazado))
        v_planta = h3.number_input("Valor por planta ($, incluye 2 años de mantenimiento)", min_value=0.0,
                                   value=float(base.valor_por_planta), step=1000.0)
        esp_siembra = st.text_area("Especies a sembrar", value=base.especies_siembra)

    # --- Armar datos finales ----------------------------------------------------------
    datos_b = base
    datos_b.sistema, datos_b.altitud, datos_b.pendiente_pct, datos_b.topografia = sistema, altitud or None, pendiente or None, topografia
    datos_b.area_predio_ha, datos_b.uso_pot = area_predio or None, uso_pot
    datos_b.cuerpo_agua, datos_b.cuerpo_agua_clase, datos_b.cuerpo_agua_nombre = agua, clase, nombre_agua
    datos_b.fuente_lat, datos_b.fuente_lon = f_lat, f_lon
    datos_b.usos_suelo, datos_b.uso_otro = usos, uso_otro
    for f in datos_b.especies:
        p = precio_editado.get(f.nombre_cientifico)
        f.precio = None if pd.isna(p) else float(p)
    datos_b.jornales_auxiliar, datos_b.valor_jornal_auxiliar = j_aux, v_aux
    datos_b.jornales_motosierrista, datos_b.valor_jornal_motosierrista = j_mot, v_mot
    datos_b.desembosque_sistema, datos_b.desembosque_jornales, datos_b.desembosque_valor_jornal = des_sis, des_j, des_v
    datos_b.valor_maquinaria = maq
    datos_b.observaciones_valor = datos_b.observaciones_acopio = obs
    datos_b.transporte_m3, datos_b.transporte_valor_m3 = trans_m3, trans_v
    datos_b.plantas_por_arbol, datos_b.plantas_por_arbol_amenazado = ppa, ppa_am
    datos_b.valor_por_planta, datos_b.especies_siembra = v_planta, esp_siembra

    st.subheader("Compensación")
    k1, k2, k3 = st.columns(3)
    k1.metric("Árboles sin amenaza", datos_b.n_no_amenazados)
    k2.metric("Árboles amenazados", datos_b.n_amenazados)
    k3.metric("Plantas a sembrar", datos_b.n_plantas)
    amenazadas = [f for f in datos_b.especies if f.amenazada]
    if amenazadas:
        st.write("Especies amenazadas: " + "; ".join(f"{f.nombre_cientifico} ({f.amenaza})" for f in amenazadas))
    st.markdown("Texto para el informe:")
    st.code(datos_b.texto_compensacion(), language=None, wrap_lines=True)

# --- Descarga -----------------------------------------------------------------
st.divider()
if inv.arboles:
    nombre = re.sub(r"[^\w\-]+", "_", inv.proyecto or archivo.name.rsplit(".", 1)[0]).strip("_")
    st.download_button(
        "⬇️ Descargar FGR-06 (Excel)",
        data=generar_fgr06(inv, DECIMALES_SEG, parte_b=datos_b if incluir_b else None),
        file_name=f"FGR-06_Inventario_{nombre}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        type="primary",
    )
    st.caption(
        "Parte A " + ("y Parte B llenas" if incluir_b else "llena; Parte B en blanco")
        + ". La columna ID queda agrupada y oculta al final de la Parte A (botón «+»)."
    )
