"""Agregacion de los resultados de comparacion en metricas interpretables."""

from __future__ import annotations

from collections import defaultdict

import configuracion as cfg
from esquema_contrato import CAMPOS_CONTRATO
from evaluacion.comparador import CORRECTO, INCORRECTO, OMITIDO, ResultadoCampo


def _fila_vacia() -> dict:
    return {"total": 0, CORRECTO: 0, INCORRECTO: 0, OMITIDO: 0, "suma_similitud": 0.0}


def _cerrar(fila: dict) -> dict:
    """Convierte los conteos acumulados en tasas."""
    total = fila["total"] or 1
    return {
        "total": fila["total"],
        "correctos": fila[CORRECTO],
        "incorrectos": fila[INCORRECTO],
        "omitidos": fila[OMITIDO],
        "exactitud": fila[CORRECTO] / total,
        "tasa_error": fila[INCORRECTO] / total,
        "tasa_omision": fila[OMITIDO] / total,
        "similitud_media": fila["suma_similitud"] / total,
    }


def _acumular(fila: dict, resultado: ResultadoCampo) -> None:
    fila["total"] += 1
    fila[resultado.estado] += 1
    fila["suma_similitud"] += resultado.similitud


def exactitud_por_campo(resultados: list[ResultadoCampo]) -> dict[str, dict]:
    """Metricas de cada uno de los quince campos.

    Es la vista principal: los campos no tienen la misma dificultad y un promedio
    global esconde que, por ejemplo, todo funcione salvo la fecha de termino.
    """
    acumulado = {campo: _fila_vacia() for campo in CAMPOS_CONTRATO}
    for resultado in resultados:
        _acumular(acumulado[resultado.campo], resultado)
    return {campo: _cerrar(fila) for campo, fila in acumulado.items()}


def exactitud_por_documento(resultados: list[ResultadoCampo]) -> dict:
    """Proporcion de documentos con los quince campos correctos.

    Es la metrica que importa si la salida se usa sin revision humana: un solo
    campo malo invalida la fila completa.
    """
    por_documento: dict[str, list[ResultadoCampo]] = defaultdict(list)
    for resultado in resultados:
        por_documento[resultado.id_documento].append(resultado)

    completos = sum(
        1 for campos in por_documento.values() if all(r.acerto for r in campos)
    )
    total = len(por_documento) or 1
    return {
        "documentos": len(por_documento),
        "completos": completos,
        "exactitud": completos / total,
    }


def resumen_global(resultados: list[ResultadoCampo]) -> dict:
    """Metricas agregadas sobre todos los campos de todos los documentos."""
    fila = _fila_vacia()
    for resultado in resultados:
        _acumular(fila, resultado)
    return _cerrar(fila)


def desglosar(resultados: list[ResultadoCampo], registros_esperados: list[dict],
              dimension: str) -> dict[str, dict]:
    """Corta los resultados por una dimension del ground truth.

    Las dimensiones utiles son ``plantilla`` y ``perfil_escaneo``: si un campo
    solo falla en un layout, el problema es el patron de ese layout y no el motor
    de lectura.
    """
    valor_por_documento = {
        registro["id_documento"]: str(registro.get(dimension, "desconocido"))
        for registro in registros_esperados
    }

    acumulado: dict[str, dict] = defaultdict(_fila_vacia)
    for resultado in resultados:
        clave = valor_por_documento.get(resultado.id_documento, "desconocido")
        _acumular(acumulado[clave], resultado)

    return {clave: _cerrar(fila) for clave, fila in sorted(acumulado.items())}


def campos_problematicos(resultados: list[ResultadoCampo], limite: int = 5) -> list[dict]:
    """Devuelve los campos con peor exactitud, para saber por donde empezar."""
    por_campo = exactitud_por_campo(resultados)
    ordenados = sorted(por_campo.items(), key=lambda par: par[1]["exactitud"])
    return [
        {"campo": campo, **metricas}
        for campo, metricas in ordenados[:limite]
        if metricas["exactitud"] < 1.0
    ]


def ejemplos_de_fallo(resultados: list[ResultadoCampo], campo: str,
                      limite: int = 3) -> list[ResultadoCampo]:
    """Primeros casos concretos en que un campo fallo, para poder inspeccionarlos."""
    fallos = [r for r in resultados if r.campo == campo and not r.acerto]
    return fallos[:limite]


def confusion_con_la_contraparte(resultados: list[ResultadoCampo]) -> dict[str, int]:
    """Cuenta cuantas veces se extrajeron los datos de la propia arrendadora.

    Es un error de naturaleza distinta a "leyo cualquier cosa": significa que el
    extractor identifico bien el campo pero se equivoco de parte del contrato.
    Merece contarse aparte porque su causa y su arreglo son otros.
    """
    conteo: dict[str, int] = {}
    for resultado in resultados:
        propio = cfg.VALORES_PROPIOS.get(resultado.campo)
        if propio and resultado.obtenido and resultado.obtenido == propio:
            conteo[resultado.campo] = conteo.get(resultado.campo, 0) + 1
    return conteo
