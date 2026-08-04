"""Interfaz de linea de comandos de la evaluacion.

    python -m evaluacion
    python -m evaluacion --predicciones salidas/predicciones.jsonl --json informe.json
"""

from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict
from pathlib import Path

import configuracion as cfg
from evaluacion import informe as redactor
from evaluacion import metricas
from evaluacion.comparador import comparar_lote
from generador.ground_truth import leer_manifiesto

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def construir_analizador() -> argparse.ArgumentParser:
    """Define los argumentos aceptados por la linea de comandos."""
    directorio_gt = cfg.DIRECTORIO_SALIDAS / cfg.SUBDIRECTORIO_GROUND_TRUTH

    analizador = argparse.ArgumentParser(
        prog="python -m evaluacion",
        description="Compara las predicciones del extractor contra el ground truth.",
    )
    analizador.add_argument(
        "--predicciones", type=Path,
        default=cfg.DIRECTORIO_SALIDAS / cfg.NOMBRE_ARCHIVO_PREDICCIONES,
        help="Archivo JSONL de predicciones (por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--ground-truth", type=Path,
        default=directorio_gt / cfg.NOMBRE_MANIFIESTO,
        help="Manifiesto del ground truth (por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--json", type=Path, default=None,
        help="Guarda ademas las metricas en un archivo JSON, para graficarlas o "
             "compararlas entre corridas.",
    )
    analizador.add_argument(
        "--etiqueta", default="",
        help="Nombre de la corrida, para distinguirla en el encabezado del informe.",
    )
    return analizador


def construir_metricas(resultados, registros_esperados, sin_prediccion) -> dict:
    """Arma el diccionario de metricas completo, apto para serializar."""
    return {
        "global": metricas.resumen_global(resultados),
        "por_documento": metricas.exactitud_por_documento(resultados),
        "por_campo": metricas.exactitud_por_campo(resultados),
        "desgloses": {
            dimension: metricas.desglosar(resultados, registros_esperados, dimension)
            for dimension in cfg.DIMENSIONES_DESGLOSE
        },
        "confusion_con_la_contraparte": metricas.confusion_con_la_contraparte(resultados),
        "documentos_sin_prediccion": sin_prediccion,
    }


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de la linea de comandos."""
    opciones = construir_analizador().parse_args(argumentos)

    for ruta in (opciones.predicciones, opciones.ground_truth):
        if not ruta.is_file():
            print(f"No existe el archivo: {ruta}")
            return 1

    registros_esperados = leer_manifiesto(opciones.ground_truth)
    with opciones.predicciones.open(encoding="utf-8") as archivo:
        registros_obtenidos = [json.loads(linea) for linea in archivo if linea.strip()]

    resultados, sin_prediccion = comparar_lote(registros_esperados, registros_obtenidos)
    print(redactor.redactar(resultados, registros_esperados, sin_prediccion, opciones.etiqueta))

    if opciones.json is not None:
        contenido = construir_metricas(resultados, registros_esperados, sin_prediccion)
        contenido["resultados"] = [asdict(resultado) for resultado in resultados]
        opciones.json.parent.mkdir(parents=True, exist_ok=True)
        opciones.json.write_text(
            json.dumps(contenido, ensure_ascii=False, indent=2), encoding="utf-8",
        )
        print(f"Metricas guardadas en {opciones.json}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
