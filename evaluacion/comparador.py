"""Comparacion campo a campo entre lo predicho y el ground truth.

Distingue tres desenlaces, no dos. Un campo vacio y un campo con un valor
equivocado no cuestan lo mismo: el vacio salta a la vista en una revision, el
incorrecto se cuela hasta la planilla final. Contarlos juntos esconde justamente
lo que hay que vigilar.
"""

from __future__ import annotations

from dataclasses import dataclass
from difflib import SequenceMatcher

from esquema_contrato import CAMPOS_CONTRATO

#: Desenlaces posibles de la comparacion de un campo.
CORRECTO = "correcto"
INCORRECTO = "incorrecto"
OMITIDO = "omitido"

ESTADOS = (CORRECTO, INCORRECTO, OMITIDO)


@dataclass(frozen=True)
class ResultadoCampo:
    """Desenlace de comparar un campo de un documento."""

    id_documento: str
    campo: str
    esperado: str
    obtenido: str
    estado: str
    similitud: float

    @property
    def acerto(self) -> bool:
        return self.estado == CORRECTO


def _normalizar(valor) -> str:
    """Lleva cualquier valor a texto comparable: colapsa espacios y recorta bordes."""
    if valor is None:
        return ""
    return " ".join(str(valor).split())


def comparar_valor(esperado, obtenido) -> tuple[str, float]:
    """Compara un valor y devuelve su desenlace junto con la similitud de caracteres.

    La similitud solo es informativa cuando el desenlace es incorrecto: permite
    separar un error de una letra, tipico del OCR, de una lectura completamente
    equivocada como haber tomado los datos de la otra parte del contrato.
    """
    referencia = _normalizar(esperado)
    leido = _normalizar(obtenido)

    if leido == referencia:
        return CORRECTO, 1.0
    if not leido:
        return OMITIDO, 0.0
    return INCORRECTO, SequenceMatcher(None, referencia, leido).ratio()


def comparar_documento(id_documento: str, esperados: dict,
                       obtenidos: dict) -> list[ResultadoCampo]:
    """Compara los quince campos de un documento y devuelve un resultado por campo."""
    resultados: list[ResultadoCampo] = []
    for campo in CAMPOS_CONTRATO:
        esperado = esperados.get(campo, "")
        obtenido = (obtenidos or {}).get(campo, "")
        estado, similitud = comparar_valor(esperado, obtenido)
        resultados.append(ResultadoCampo(
            id_documento=id_documento,
            campo=campo,
            esperado=_normalizar(esperado),
            obtenido=_normalizar(obtenido),
            estado=estado,
            similitud=round(similitud, 4),
        ))
    return resultados


def comparar_lote(
    registros_esperados: list[dict], registros_obtenidos: list[dict],
) -> tuple[list[ResultadoCampo], list[str]]:
    """Compara un lote completo emparejando por identificador de documento.

    Devuelve los resultados de todos los campos y la lista de documentos que
    estaban en el ground truth pero no en las predicciones. Esos se evaluan igual,
    con todos sus campos como omitidos: un documento que el extractor ni siquiera
    proceso es un fallo, no una fila que se pueda descartar del promedio.
    """
    por_id = {registro["id_documento"]: registro.get("campos", {})
              for registro in registros_obtenidos}

    resultados: list[ResultadoCampo] = []
    sin_prediccion: list[str] = []

    for registro in registros_esperados:
        id_documento = registro["id_documento"]
        if id_documento not in por_id:
            sin_prediccion.append(id_documento)
        resultados.extend(
            comparar_documento(
                id_documento, registro.get("campos", {}), por_id.get(id_documento, {}),
            )
        )

    return resultados, sin_prediccion
