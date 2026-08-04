"""Generador de contratos de arriendo vehicular sinteticos.

Produce PDFs con tres layouts distintos, su version "escaneada" degradada y el
ground truth en JSON de cada documento, para poder medir despues la precision de
un extractor OCR sin usar ningun contrato real.

Uso tipico desde la linea de comandos::

    python -m generador --cantidad 50 --semilla 42 --perfil mixto

Este paquete se mantiene sin importaciones en el ``__init__`` a proposito: las
plantillas importan ``generador.formatos``, y dejar el paquete vacio evita
cualquier ciclo de importacion.
"""
