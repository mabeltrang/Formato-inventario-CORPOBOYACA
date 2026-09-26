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
- La **Parte B** se entrega en blanco (plantilla limpia) para llenarla a mano.

### Validaciones

- **Errores** (el árbol se excluye): sin CAP A, HT vacía o ≤ 0, coordenadas vacías o fuera de Colombia.
- **Avisos**:
  - VT distinto al recalculado.
  - IDs repetidos.
  - X y Y invertidas (se corrigen solas).
  - Dos árboles que quedan con la misma coordenada en grados, minutos y segundos.

## Estructura

```
app.py                     Interfaz Streamlit
fgr06/
  lector.py                Lectura y validación del inventario propio
  calculos.py              DAP, AB, VT y conversión a grados, minutos y segundos
  escritor.py              Escritura del FGR-06 Parte A sobre la plantilla
  excel_utils.py           Insertar columnas conservando combinaciones y anchos
  resumen.py               Tablas de vista previa y resumen por especie
plantilla/
  FGR-06_v7_plantilla.xlsx          Formato CORPOBOYACÁ limpio (Parte A sin filas, Parte B en blanco)
  Plantilla_Inventario_Forestal.xlsx Inventario de campo en blanco (formato propio, con fórmulas)
  crear_plantilla_inventario.py      Regenera la plantilla de inventario
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

No requiere variables de entorno ni secretos.

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
