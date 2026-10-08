"""Firma escaneada para los formatos (FGR-29 y "Firma del solicitante" del FGR-06).

La imagen se busca en este orden:
  1. st.secrets["firma_aislados_png_b64"]  (PNG en base64; recomendado si el repo es público)
  2. plantilla/firmas/firma_aislados.png
Si no hay ninguna, los formatos salen sin firma.
"""

from __future__ import annotations

import base64
import io
from pathlib import Path

from openpyxl.drawing.image import Image as XLImage
from PIL import Image

RUTA_FIRMA = Path(__file__).resolve().parent.parent / "plantilla" / "firmas" / "firma_aislados.png"


def cargar_firma(b64: str | None = None, ruta: Path | str = RUTA_FIRMA) -> bytes | None:
    if b64:
        return base64.b64decode(b64)
    ruta = Path(ruta)
    return ruta.read_bytes() if ruta.exists() else None


def _png_transparente(datos: bytes) -> bytes:
    """Fondo blanco → transparente, para que la firma no tape las líneas de la celda."""
    im = Image.open(io.BytesIO(datos)).convert("RGBA")
    pix = [(r, g, b, 0) if min(r, g, b) > 230 else (r, g, b, a) for r, g, b, a in im.getdata()]
    im.putdata(pix)
    salida = io.BytesIO()
    im.save(salida, format="PNG")
    return salida.getvalue()


def insertar_firma(ws, celda: str, datos: bytes, alto_px: int) -> None:
    img = XLImage(io.BytesIO(_png_transparente(datos)))
    escala = alto_px / img.height
    img.width, img.height = round(img.width * escala), alto_px
    ws.add_image(img, celda)
