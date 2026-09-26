"""Predio a partir de un KMZ/KML: área, árboles dentro del polígono, altitud y pendiente.

- Área: proyección local sobre el elipsoide WGS84 (radios de curvatura en el centro
  del predio). Para predios de pocos km² el error es despreciable (< 0,01 %).
- Altitud y pendiente: se muestrea el DEM en una grilla sobre el predio.
  Fuente principal: OpenTopoData SRTM 30 m (api.opentopodata.org, gratis, sin clave).
  Respaldo: Open-Meteo Elevation (Copernicus GLO-90, 90 m).
  Con predios pequeños (pocas hectáreas) la pendiente de un DEM de 30 m es solo
  indicativa: revísala contra el levantamiento topográfico si lo tienes.
"""

from __future__ import annotations

import io
import math
import time
import zipfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass

import requests

_A = 6_378_137.0              # semieje mayor WGS84 (m)
_E2 = 6.694379990141e-3       # excentricidad² WGS84


def _metros_por_grado(lat: float) -> tuple[float, float]:
    """(m por grado de longitud, m por grado de latitud) en la latitud dada."""
    s = math.sin(math.radians(lat))
    n = _A / math.sqrt(1 - _E2 * s * s)                 # radio del primer vertical
    m = _A * (1 - _E2) / (1 - _E2 * s * s) ** 1.5       # radio meridiano
    return math.radians(1) * n * math.cos(math.radians(lat)), math.radians(1) * m


def _area_anillo_m2(anillo, lat_ref: float, lon_ref: float) -> float:
    mx, my = _metros_por_grado(lat_ref)
    pts = [((lon - lon_ref) * mx, (lat - lat_ref) * my) for lon, lat in anillo]
    return abs(sum(x1 * y2 - x2 * y1 for (x1, y1), (x2, y2) in zip(pts, pts[1:] + pts[:1]))) / 2

# Clases de topografía del FGR-06 según pendiente media (%). Umbrales editables.
UMBRAL_PLANA = 3.0      # 0–3 %   → Plana
UMBRAL_ONDULADA = 12.0  # 3–12 %  → Ondulada; > 12 % → Colina


@dataclass
class Poligono:
    nombre: str
    anillo: list[tuple[float, float]]   # [(lon, lat), ...] anillo exterior
    huecos: list[list[tuple[float, float]]]

    @property
    def area_m2(self) -> float:
        lons, lats = zip(*self.anillo)
        lon_c, lat_c = sum(lons) / len(lons), sum(lats) / len(lats)
        return _area_anillo_m2(self.anillo, lat_c, lon_c) - sum(
            _area_anillo_m2(h, lat_c, lon_c) for h in self.huecos
        )

    def contiene(self, lon: float, lat: float) -> bool:
        return _punto_en_anillo(lon, lat, self.anillo) and not any(
            _punto_en_anillo(lon, lat, h) for h in self.huecos
        )


@dataclass
class Predio:
    poligonos: list[Poligono]

    @property
    def area_ha(self) -> float:
        return sum(p.area_m2 for p in self.poligonos) / 10_000

    def contiene(self, lon: float, lat: float) -> bool:
        return any(p.contiene(lon, lat) for p in self.poligonos)

    @property
    def bbox(self) -> tuple[float, float, float, float]:
        pts = [pt for p in self.poligonos for pt in p.anillo]
        lons, lats = zip(*pts)
        return min(lons), min(lats), max(lons), max(lats)


@dataclass
class Relieve:
    altitud_msnm: float
    pendiente_pct: float
    topografia: str        # Plana / Ondulada / Colina
    n_puntos: int
    fuente: str


# ----------------------------------------------------------------------------
# Lectura KMZ / KML
# ----------------------------------------------------------------------------

def _punto_en_anillo(x: float, y: float, anillo) -> bool:
    dentro = False
    n = len(anillo)
    for i in range(n):
        x1, y1 = anillo[i]
        x2, y2 = anillo[(i + 1) % n]
        if (y1 > y) != (y2 > y):
            xc = x1 + (y - y1) * (x2 - x1) / (y2 - y1)
            if x < xc:
                dentro = not dentro
    return dentro


def _coords(texto: str) -> list[tuple[float, float]]:
    pts = []
    for tupla in texto.split():
        partes = tupla.split(",")
        if len(partes) >= 2:
            pts.append((float(partes[0]), float(partes[1])))
    return pts


def leer_kmz(datos: bytes) -> Predio:
    """Lee un .kmz o .kml (bytes) y devuelve los polígonos que contiene."""
    if datos[:2] == b"PK":
        with zipfile.ZipFile(io.BytesIO(datos)) as z:
            nombre_kml = next((n for n in z.namelist() if n.lower().endswith(".kml")), None)
            if not nombre_kml:
                raise ValueError("El KMZ no contiene ningún archivo .kml.")
            datos = z.read(nombre_kml)

    raiz = ET.fromstring(datos)

    def local(tag):
        return tag.rsplit("}", 1)[-1]

    poligonos = []
    for pm in raiz.iter():
        if local(pm.tag) != "Placemark":
            continue
        nombre = next((e.text or "" for e in pm.iter() if local(e.tag) == "name"), "")
        for pol in (e for e in pm.iter() if local(e.tag) == "Polygon"):
            exterior, huecos = None, []
            for frontera in pol:
                tipo = local(frontera.tag)
                coords = next((e.text for e in frontera.iter() if local(e.tag) == "coordinates"), None)
                if not coords:
                    continue
                if tipo == "outerBoundaryIs":
                    exterior = _coords(coords)
                elif tipo == "innerBoundaryIs":
                    huecos.append(_coords(coords))
            if exterior and len(exterior) >= 3:
                poligonos.append(Poligono(nombre.strip(), exterior, huecos))

    if not poligonos:
        raise ValueError("No se encontró ningún polígono en el archivo (¿el predio está dibujado como línea?).")
    return Predio(poligonos)


# ----------------------------------------------------------------------------
# DEM
# ----------------------------------------------------------------------------

def _elev_opentopodata(puntos: list[tuple[float, float]]) -> list[float]:
    salida = []
    for i in range(0, len(puntos), 100):
        lote = puntos[i:i + 100]
        locs = "|".join(f"{lat:.6f},{lon:.6f}" for lon, lat in lote)
        r = requests.get("https://api.opentopodata.org/v1/srtm30m", params={"locations": locs}, timeout=30)
        r.raise_for_status()
        salida += [res["elevation"] for res in r.json()["results"]]
        if i + 100 < len(puntos):
            time.sleep(1.1)  # límite de 1 consulta por segundo
    return salida


def _elev_openmeteo(puntos: list[tuple[float, float]]) -> list[float]:
    salida = []
    for i in range(0, len(puntos), 100):
        lote = puntos[i:i + 100]
        r = requests.get(
            "https://api.open-meteo.com/v1/elevation",
            params={
                "latitude": ",".join(f"{lat:.6f}" for _, lat in lote),
                "longitude": ",".join(f"{lon:.6f}" for lon, _ in lote),
            },
            timeout=30,
        )
        r.raise_for_status()
        salida += r.json()["elevation"]
    return salida


FUENTES_DEM = [
    ("OpenTopoData SRTM 30 m", _elev_opentopodata),
    ("Open-Meteo Copernicus 90 m", _elev_openmeteo),
]


def clasificar_topografia(pendiente_pct: float) -> str:
    if pendiente_pct <= UMBRAL_PLANA:
        return "Plana"
    if pendiente_pct <= UMBRAL_ONDULADA:
        return "Ondulada"
    return "Colina"


def calcular_relieve(predio: Predio, paso_m: float = 30.0, max_puntos: int = 400, fuentes=None) -> Relieve:
    """Altitud media y pendiente media (%) del predio a partir del DEM.

    Arma una grilla regular (paso ≈ resolución del DEM) que cubre el predio con un
    margen de una celda, calcula la pendiente por diferencias centrales y promedia
    las celdas cuyo centro cae dentro del polígono.
    """
    fuentes = fuentes or FUENTES_DEM
    lon0, lat0, lon1, lat1 = predio.bbox
    m_por_grado_lon, m_por_grado_lat = _metros_por_grado((lat0 + lat1) / 2)

    ancho_m = (lon1 - lon0) * m_por_grado_lon
    alto_m = (lat1 - lat0) * m_por_grado_lat
    paso = paso_m
    while ((ancho_m / paso) + 3) * ((alto_m / paso) + 3) > max_puntos:
        paso *= 1.25
    nx = int(math.ceil(ancho_m / paso)) + 3
    ny = int(math.ceil(alto_m / paso)) + 3
    dlon, dlat = paso / m_por_grado_lon, paso / m_por_grado_lat

    grilla = [
        (lon0 - dlon + i * dlon, lat0 - dlat + j * dlat)
        for j in range(ny)
        for i in range(nx)
    ]

    ultimo_error = None
    for nombre, fn in fuentes:
        try:
            z = fn(grilla)
            if len(z) != len(grilla) or any(v is None for v in z):
                raise ValueError("respuesta incompleta")
            break
        except Exception as e:  # noqa: BLE001
            ultimo_error = e
    else:
        raise RuntimeError(f"No se pudo consultar ningún DEM: {ultimo_error}")

    def Z(i, j):
        return z[j * nx + i]

    pendientes, alturas = [], []
    for j in range(1, ny - 1):
        for i in range(1, nx - 1):
            lon, lat = grilla[j * nx + i]
            if not predio.contiene(lon, lat):
                continue
            dzdx = (Z(i + 1, j) - Z(i - 1, j)) / (2 * paso)
            dzdy = (Z(i, j + 1) - Z(i, j - 1)) / (2 * paso)
            pendientes.append(math.hypot(dzdx, dzdy) * 100)
            alturas.append(Z(i, j))

    if not pendientes:
        # Predio más pequeño que una celda: se usa la celda central de la grilla
        i, j = nx // 2, ny // 2
        dzdx = (Z(i + 1, j) - Z(i - 1, j)) / (2 * paso)
        dzdy = (Z(i, j + 1) - Z(i, j - 1)) / (2 * paso)
        pendientes, alturas = [math.hypot(dzdx, dzdy) * 100], [Z(i, j)]

    pend = sum(pendientes) / len(pendientes)
    return Relieve(
        altitud_msnm=round(sum(alturas) / len(alturas)),
        pendiente_pct=round(pend, 2),
        topografia=clasificar_topografia(pend),
        n_puntos=len(pendientes),
        fuente=nombre,
    )
