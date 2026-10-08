# Conversor FGR-06 · CORPOBOYACÁ

App de Streamlit que convierte un inventario forestal de árboles aislados (formato propio,
hoja **Inventario**) en la **Parte A – Inventario Forestal al 100 %** del formato
**FGR-06 v7** de CORPOBOYACÁ, con las celdas combinadas del formato oficial.

## Qué hace

- Lee el inventario: una fila por árbol, con `CAP A (m)`, `CAP B (m)`, `CAP C (m)`… (tantos fustes como haya),
  `HT (m)`, `Coordenada X` (longitud) y `Coordenada Y` (latitud) en grados decimales WGS84.
- Recalcula todo en Python:
  - DAP = CAP / π
  - AB = π · (DAP/2)²
  - VT = HT · Σ AB de todos los fustes · factor de forma (0,7 por defecto, editable). La misma HT se usa para todos los fustes.
- Compara el VT recalculado con el VT del Excel y avisa si no coinciden.
- Escribe el FGR-06 árbol por árbol:
  - N° de árboles = 1.
  - DAP en cm.
  - Latitud y longitud en grados, minutos y segundos, con los segundos a 2 decimales.
  - Fila TOTAL con fórmulas.
- Si algún árbol tiene más de 3 fustes, agrega columnas `DAP D (cm)`, `DAP E (cm)`… después de DAP C.
- Deja el **ID** del inventario en una columna agrupada y oculta al final (botón «+» para verla), fuera del área de impresión.
- Configura la impresión: papel 8,5 × 13 (Folio), ajuste a una página de ancho y encabezados de tabla repetidos en cada hoja.
- Pestaña de **búsqueda por especie**: número de árboles, fustes, AB y volumen por especie.
- **Parte B** (opcional, se activa en la pestaña Parte B). Cada sección se llena así:
  - **Sección 1, sistema asociado.** Se elige en un formulario.
  - **Sección 2, características biofísicas.**
    - Altitud y pendiente salen del **KMZ del predio** usando un DEM (OpenTopoData SRTM 30 m, con Open-Meteo 90 m como respaldo).
    - La topografía se clasifica por la pendiente: Plana ≤ 3 %, Ondulada ≤ 12 % y Colina > 12 %.
    - Los cuerpos de agua se ingresan en el formulario.
  - **Sección 3, uso del suelo.** Formulario.
    - El área del predio sale del KMZ.
    - La app avisa si hay árboles fuera del polígono.
  - **Sección 4, aspectos técnicos.**
    - Árboles y volumen por especie salen del inventario.
    - El precio por m³ sale de `plantilla/precios_madera.csv` y se puede editar en la app.
    - Jornales = máx(árboles ÷ árboles por jornal, m³ ÷ m³ por jornal), con mínimo 1. Ambos rendimientos son supuestos editables.
    - El patio de acopio es el **árbol central** del inventario (el medoide).
  - **Sección 5, renovabilidad.**
    - Se siembran 10 plantas por árbol sin amenaza y 15 por árbol amenazado.
    - La app genera el texto de compensación para el informe.

### Validaciones

- **Errores** (el árbol se excluye): sin CAP A, HT vacía o ≤ 0, coordenadas vacías o fuera de Colombia.
- **Avisos**:
  - VT distinto al recalculado.
  - IDs repetidos.
  - X y Y invertidas (se corrigen solas).
  - Dos árboles que quedan con la misma coordenada en grados, minutos y segundos.

## Costos y FGR-29 (solo árboles aislados)

La app detecta el **tipo de aprovechamiento** por el volumen total (hasta 20 m³ es aislados de uso doméstico; más, árboles aislados).
Se puede cambiar a mano:

- **Aislados de uso doméstico**: entrega solo el FGR-06 (inventario, Parte A y B). 5 plantas por árbol.
- **Árboles aislados**: entrega además el **FGR-29** (autodeclaración de costos) y las **tablas de costos del
  documento técnico**. 10 plantas por árbol (15 si está amenazado).

Los costos salen de `fgr06/costos.py` (`Tarifas`) y de dos datos del inventario:

- **Aprovechamiento** = volumen total × (tala $100.000/m³ + transporte menor $90.000/m³).
- **Compensación (3 años)** = f(N plantas): mano de obra de siembra por rendimientos (plantas/jornal),
  plántulas e insumos por dosis, herramientas (un kit cada 150 plantas), resiembra del 10 %,
  7 visitas de mantenimiento con jornales que escalan con N, e imprevistos del 5 % sobre el subtotal.

Antes de descargar, la app muestra un resumen (aprovechamiento, compensación, valor por planta y total del
FGR-29) y avisa si faltan el contrato o el canon. El detalle de cada tabla queda en la pestaña *Costos (FGR-29)*.

Con los mismos números se llenan:

| Dónde | Qué |
|---|---|
| FGR-29 · 1.1 fila 10 | Volumen × tarifa de aprovechamiento |
| FGR-29 · 1.4 | Valor del contrato de arriendo o servidumbre (se escribe en la app). La compensación de 1.4 queda en 0 |
| FGR-29 · 2.3 | Canon de arrendamiento anual (se escribe en la app) |
| FGR-29 · 2.6 | Mano de obra, insumos, herramientas, mantenimiento e imprevistos |
| FGR-06 Parte B · renovabilidad | Valor por planta = total compensación ÷ N |
| Tablas del informe | Costos de aprovechamiento y costos de reposición a 3 años, con fórmulas |

El resto del FGR-29 (obras, maquinaria, operación de la minigranja) es la plantilla estándar de Unergy en
`plantilla/FGR-29_v3_plantilla.xlsx`. Actualiza las tarifas una vez al año en `Tarifas`.

## Amenaza de especies

`fgr06/amenazas/` es una copia de la consulta de amenaza del repo
[analisis-compensacion-forestal](https://github.com/mabeltrang/analisis-compensacion-forestal)
(commit c0c980d). Incluye las listas MADS Res. 0126/2024, CITES y UICN, y las vedas nacionales y regionales.

Para el 15:1 se considera **amenazada** una especie que cumpla cualquiera de estas condiciones:

- CR, EN o VU en MADS.
- CR, EN o VU en UICN.
- CITES Apéndice I o II.
- Opcionalmente, estar en veda.

Si actualizas las listas en el otro repo, copia de nuevo los CSV a `fgr06/amenazas/datos/`.

## Precios de la madera en pie

`plantilla/precios_madera.csv` tiene las columnas `nombre_cientifico`, `nombre_comun`, `precio_cop_m3_en_pie`, `fuente` y `fecha`.

- Búsqueda: nombre exacto → sinónimo (`plantilla/sinonimos_especies.csv`, p. ej. *Hesperocyparis lusitanica* → *Cupressus lusitanica*) → `Genero sp`.
- Si la especie no tiene precio, se usa el de `Genero sp` y la app lo avisa.
- Los precios editados en la app se descargan como CSV actualizado. Súbelo al repo para que queden guardados.
- Documenta la fuente de cada precio, por ejemplo la cotización de un aserrío local con su fecha.

## Estructura

```
app.py                     Interfaz Streamlit
fgr06/
  lector.py                Lectura y validación del inventario propio
  calculos.py              DAP, AB, VT y conversión a grados, minutos y segundos
  escritor.py              Escritura del FGR-06 Parte A sobre la plantilla
  excel_utils.py           Insertar columnas conservando combinaciones y anchos
  resumen.py               Tablas de vista previa y resumen por especie
  parte_b.py               Cálculo y escritura de la Parte B
  costos.py                Tarifas, costos de aprovechamiento y compensación, FGR-29 y tablas del informe
  predio.py                KMZ: área, árboles dentro del predio, altitud y pendiente (DEM)
  precios.py               Tabla de precios por especie
  amenazas/                MADS / CITES / UICN / vedas (copiado de analisis-compensacion-forestal)
plantilla/
  FGR-06_v7_plantilla.xlsx          Formato CORPOBOYACÁ limpio (Parte A sin filas, Parte B en blanco)
  FGR-29_v3_plantilla.xlsx          Autodeclaración de costos con los valores estándar de minigranja
  Plantilla_Inventario_Forestal.xlsx Inventario de campo en blanco (formato propio, con fórmulas)
  crear_plantilla_inventario.py      Regenera la plantilla de inventario
  precios_madera.csv                 Precios de referencia $/m³ en pie
ejemplos/
  crear_ejemplo.py         Genera un inventario ficticio (incluye un árbol de 5 fustes)
  inventario_ejemplo.xlsx
tests/                     Pruebas con pytest
```

## Uso local

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
streamlit run app.py
```

Pruebas:

```bash
pip install pytest
pytest -q
```

## Despliegue en Streamlit Community Cloud

1. Sube el repo a GitHub.
2. En share.streamlit.io, crea una app nueva que apunte a `app.py`.

No requiere variables de entorno ni secretos. Para altitud y pendiente, la app necesita salida a internet hacia api.opentopodata.org o api.open-meteo.com; Streamlit Cloud la tiene.

## Salida

La app entrega un **.xlsx editable** (no PDF). Las celdas combinadas solo llevan borde en el
contorno, para que no aparezcan líneas atravesando los números al abrirlo en Google Sheets o LibreOffice.

## Formato de entrada esperado

Usa `plantilla/Plantilla_Inventario_Forestal.xlsx`:

- Texto azul: datos de campo.
- Negro: fórmulas.
- El factor de forma va en M1.
- Si un árbol tiene más de 3 fustes, inserta después de `AB C (m2)` las columnas `CAP D (m)`, `DAP D (m)` y `AB D (m2)`, y súmalas en `AB T (m2)`.

| Campo | Encabezado |
|---|---|
| ID | `ID` |
| Nombre común | `Nombre común` |
| Nombre científico | `Nombre científico` |
| Familia (opcional) | `Familia` |
| Fustes | `CAP A (m)`, `CAP B (m)`, `CAP C (m)`, `CAP D (m)`… |
| Altura total | `HT (m)` |
| Volumen de control (opcional) | `VT (m3)` |
| Longitud | `Coordenada X` |
| Latitud | `Coordenada Y` |

- Los datos del proyecto (`PROYECTO`, `PROPIETARIO`, `UBICACIÓN`, `FECHA`) se leen de las celdas a la derecha de cada etiqueta.
- Las filas sin nombre común y sin CAP A, como la fila de totales, se ignoran.

## Actualizar la plantilla

Si CORPOBOYACÁ publica una versión nueva del FGR-06, reemplaza `plantilla/FGR-06_v7_plantilla.xlsx`
respetando lo siguiente:

- La Parte A es la primera hoja.
- Los encabezados de la tabla van en las filas 8 a 10.
- Los árboles empiezan en la fila 11.

Si cambian las columnas, ajusta `_grupos()` en `fgr06/escritor.py`.

> ⚠️ No subas inventarios reales al repo: tienen datos de propietarios y coordenadas. El `.gitignore` bloquea los `.xlsx` salvo la plantilla y el ejemplo.
