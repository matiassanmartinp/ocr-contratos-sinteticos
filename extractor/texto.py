"""Obtencion del texto de un contrato en PDF.

Por ahora solo implementa la via de texto embebido, que es la que da el techo de
precision de la logica de extraccion sin que el ruido del OCR se mezcle con los
errores de parseo. La via OCR se agrega despues y expone la misma interfaz.
"""

from __future__ import annotations

from pathlib import Path

import fitz  # PyMuPDF

import configuracion as cfg


def normalizar_espacios(texto: str) -> str:
    """Colapsa saltos de linea y espacios repetidos en un solo espacio.

    El texto de un PDF viene cortado en lineas segun donde caiga el margen, no
    segun donde termine una frase. Aplanarlo permite escribir patrones sobre el
    contenido y no sobre la maquetacion.
    """
    return " ".join((texto or "").split())


def extraer_texto_nativo(ruta_pdf: Path) -> str:
    """Devuelve el texto embebido del PDF, con los espacios ya normalizados."""
    documento = fitz.open(str(ruta_pdf))
    try:
        paginas = [pagina.get_text() for pagina in documento]
    finally:
        documento.close()
    return normalizar_espacios(" ".join(paginas))


def tiene_texto_util(texto: str) -> bool:
    """Indica si el texto embebido alcanza para extraer sin recurrir al OCR.

    Un PDF que es solo una imagen escaneada devuelve texto vacio o unos pocos
    caracteres sueltos; por debajo del umbral configurado hay que rasterizar.
    """
    return len(texto or "") >= cfg.MINIMO_CARACTERES_TEXTO_NATIVO
