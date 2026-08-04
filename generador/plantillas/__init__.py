"""Registro de las plantillas de layout disponibles.

Cada plantilla es un modulo que expone:

``NOMBRE``
    Identificador corto, el mismo que se guarda en el ground truth.
``VARIANTES_FORMATO``
    Como imprime esta plantilla la fecha, el monto, la patente y la etiqueta del
    RUT de la persona natural.
``CONFIGURACION_PAGINA``
    Argumentos de pagina y margenes para ``SimpleDocTemplate``.
``construir(contrato, aleatorio)``
    Devuelve la lista de elementos de reportlab del documento.
``dibujar_fondo(canvas, doc)``
    Opcional. Se dibuja detras del contenido en cada pagina.

Para agregar un cuarto layout basta crear el modulo, importarlo aqui y sumarlo a
``REGISTRO_PLANTILLAS`` y a ``DISTRIBUCION_PLANTILLAS`` en ``configuracion.py``.
"""

from generador.plantillas import (
    plantilla_compacta,
    plantilla_formal,
    plantilla_tabular,
)

REGISTRO_PLANTILLAS = {
    plantilla_formal.NOMBRE: plantilla_formal,
    plantilla_tabular.NOMBRE: plantilla_tabular,
    plantilla_compacta.NOMBRE: plantilla_compacta,
}

NOMBRES_PLANTILLAS = tuple(REGISTRO_PLANTILLAS)


def obtener_plantilla(nombre: str):
    """Devuelve el modulo de la plantilla pedida o falla con un mensaje claro."""
    try:
        return REGISTRO_PLANTILLAS[nombre]
    except KeyError:
        disponibles = ", ".join(NOMBRES_PLANTILLAS)
        raise ValueError(
            f"Plantilla desconocida: {nombre!r}. Disponibles: {disponibles}."
        ) from None
