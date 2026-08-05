"""Conversion de un PDF en imagenes, compartida por el generador y el extractor.

El generador la usa para fabricar escaneos degradados; el extractor, para poder
pasar por OCR un PDF que no trae texto embebido. Vive en la raiz para que ninguno
de los dos paquetes dependa del otro.
"""

from __future__ import annotations

import io
from pathlib import Path

import fitz  # PyMuPDF
from PIL import Image


def rasterizar_pdf(ruta_pdf: Path, dpi: int) -> list[Image.Image]:
    """Convierte cada pagina del PDF en una imagen PIL en escala de grises."""
    paginas: list[Image.Image] = []
    with fitz.open(str(ruta_pdf)) as documento:
        for pagina in documento:
            mapa_pixeles = pagina.get_pixmap(dpi=dpi, alpha=False)
            imagen = Image.open(io.BytesIO(mapa_pixeles.tobytes("png")))
            paginas.append(imagen.convert("L"))
    return paginas


def contar_paginas(ruta_pdf: Path) -> int:
    """Devuelve cuantas paginas tiene el PDF sin rasterizar ninguna."""
    with fitz.open(str(ruta_pdf)) as documento:
        return documento.page_count
