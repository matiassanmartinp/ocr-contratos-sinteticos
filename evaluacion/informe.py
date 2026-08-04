"""Presentacion de las metricas como texto legible en la terminal."""

from __future__ import annotations

import configuracion as cfg
from evaluacion import metricas
from evaluacion.comparador import ResultadoCampo

_ANCHO = 78
_RECORTE_EJEMPLO = 46


def _titulo(texto: str) -> str:
    return f"\n{texto}\n{'=' * _ANCHO}"


def _porcentaje(valor: float) -> str:
    return f"{valor * 100:6.1f}%"


def _recortar(texto: str, ancho: int = _RECORTE_EJEMPLO) -> str:
    texto = texto or "(vacio)"
    return texto if len(texto) <= ancho else texto[: ancho - 1] + "…"


def _tabla(filas: dict[str, dict], encabezado_primera: str) -> list[str]:
    """Arma una tabla de exactitud, error y omision para un conjunto de filas."""
    lineas = [
        f"{encabezado_primera:<24} {'exact.':>7} {'error':>7} {'omis.':>7} {'n':>6}",
        "-" * _ANCHO,
    ]
    for clave, m in filas.items():
        lineas.append(
            f"{clave:<24} {_porcentaje(m['exactitud'])} {_porcentaje(m['tasa_error'])} "
            f"{_porcentaje(m['tasa_omision'])} {m['total']:>6}"
        )
    return lineas


def redactar(resultados: list[ResultadoCampo], registros_esperados: list[dict],
             sin_prediccion: list[str], etiqueta: str = "") -> str:
    """Redacta el informe completo de una evaluacion."""
    partes: list[str] = []

    global_ = metricas.resumen_global(resultados)
    por_documento = metricas.exactitud_por_documento(resultados)

    encabezado = "INFORME DE EXTRACCION"
    if etiqueta:
        encabezado += f" — {etiqueta}"
    partes.append(_titulo(encabezado))
    partes.append(
        f"Documentos evaluados : {por_documento['documentos']}\n"
        f"Campos comparados    : {global_['total']}\n"
        f"Exactitud por campo  : {_porcentaje(global_['exactitud'])}  "
        f"({global_['correctos']} correctos, {global_['incorrectos']} incorrectos, "
        f"{global_['omitidos']} omitidos)\n"
        f"Documentos perfectos : {_porcentaje(por_documento['exactitud'])}  "
        f"({por_documento['completos']} de {por_documento['documentos']} con los "
        f"quince campos correctos)"
    )

    if sin_prediccion:
        partes.append(
            f"\nAVISO: {len(sin_prediccion)} documento(s) sin prediccion, contados "
            f"como omitidos: {', '.join(sin_prediccion[:5])}"
            + (" …" if len(sin_prediccion) > 5 else "")
        )

    partes.append(_titulo("EXACTITUD POR CAMPO"))
    partes.extend(_tabla(metricas.exactitud_por_campo(resultados), "campo"))

    for dimension in cfg.DIMENSIONES_DESGLOSE:
        desglose = metricas.desglosar(resultados, registros_esperados, dimension)
        if len(desglose) > 1:
            partes.append(_titulo(f"DESGLOSE POR {dimension.upper()}"))
            partes.extend(_tabla(desglose, dimension))

    confusiones = metricas.confusion_con_la_contraparte(resultados)
    partes.append(_titulo("CONFUSION CON LA PROPIA ARRENDADORA"))
    if confusiones:
        total = sum(confusiones.values())
        partes.append(
            f"{total} campo(s) tomaron los datos de la arrendadora en vez de los del "
            f"arrendatario:"
        )
        for campo, cantidad in sorted(confusiones.items(), key=lambda p: -p[1]):
            partes.append(f"  {campo:<24} {cantidad}")
    else:
        partes.append("Ninguna. El extractor distinguio bien las dos partes del contrato.")

    problematicos = metricas.campos_problematicos(resultados)
    if problematicos:
        partes.append(_titulo("PEORES CAMPOS, CON EJEMPLOS"))
        for entrada in problematicos:
            campo = entrada["campo"]
            partes.append(
                f"\n{campo}  —  exactitud {_porcentaje(entrada['exactitud'])}, "
                f"similitud media {entrada['similitud_media']:.2f}"
            )
            for fallo in metricas.ejemplos_de_fallo(resultados, campo):
                partes.append(f"   {fallo.id_documento} [{fallo.estado}]")
                partes.append(f"     esperado: {_recortar(fallo.esperado)}")
                partes.append(f"     obtenido: {_recortar(fallo.obtenido)}")
    else:
        partes.append(_titulo("PEORES CAMPOS"))
        partes.append("Ninguno: los quince campos se extrajeron sin error.")

    return "\n".join(partes) + "\n"
