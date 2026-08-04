"""Renderizado de un contrato sintetico a PDF con reportlab.

El PDF que se produce aqui es nativo: lleva el texto embebido. Sirve como caso
"documento digital" y como entrada del modulo de escaneo, que lo convierte en una
imagen degradada para simular un documento papel digitalizado.
"""

from __future__ import annotations

from pathlib import Path
from random import Random

from reportlab.platypus import SimpleDocTemplate

from esquema_contrato import ContratoSintetico
from generador.plantillas import obtener_plantilla


def renderizar_contrato(
    contrato: ContratoSintetico,
    ruta_pdf: Path,
    nombre_plantilla: str,
    aleatorio: Random,
) -> Path:
    """Escribe el contrato en ``ruta_pdf`` usando la plantilla indicada.

    La plantilla decide el tamano de pagina, los margenes, la tipografia y el
    formato con que se imprime cada valor; este modulo solo la ejecuta.
    """
    plantilla = obtener_plantilla(nombre_plantilla)
    ruta_pdf.parent.mkdir(parents=True, exist_ok=True)

    documento = SimpleDocTemplate(
        str(ruta_pdf),
        title="Contrato de arrendamiento de vehiculo (documento sintetico)",
        author="Generador sintetico - repositorio de portafolio",
        subject="Documento generado automaticamente. No corresponde a un contrato real.",
        **plantilla.CONFIGURACION_PAGINA,
    )

    elementos = plantilla.construir(contrato, aleatorio)
    dibujar_fondo = getattr(plantilla, "dibujar_fondo", None)

    if dibujar_fondo is None:
        documento.build(elementos)
    else:
        documento.build(elementos, onFirstPage=dibujar_fondo, onLaterPages=dibujar_fondo)

    return ruta_pdf
