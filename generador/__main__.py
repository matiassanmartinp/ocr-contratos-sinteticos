"""Interfaz de linea de comandos del generador.

    python -m generador --cantidad 50 --semilla 42 --perfil mixto
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import configuracion as cfg
from generador.lote import generar_lote, limpiar_salidas
from generador.plantillas import NOMBRES_PLANTILLAS

# Los contratos llevan acentos y enie; en la consola de Windows la salida por
# defecto no siempre es UTF-8.
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def construir_analizador() -> argparse.ArgumentParser:
    """Define los argumentos aceptados por la linea de comandos."""
    analizador = argparse.ArgumentParser(
        prog="python -m generador",
        description=(
            "Genera contratos de arriendo vehicular sinteticos en PDF, su version "
            "escaneada degradada y el ground truth en JSON de cada documento."
        ),
    )
    analizador.add_argument(
        "--cantidad", type=int, default=cfg.CANTIDAD_POR_DEFECTO,
        help="Cantidad de contratos a generar (por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--semilla", type=int, default=cfg.SEMILLA_POR_DEFECTO,
        help="Semilla aleatoria; fija el lote completo (por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--perfil", default=cfg.PERFIL_ESCANEO_POR_DEFECTO,
        choices=(*cfg.PERFILES_ESCANEO, cfg.PERFIL_MIXTO),
        help="Perfil de degradacion del escaneo (por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--plantilla", default=None, choices=NOMBRES_PLANTILLAS,
        help="Fuerza un unico layout. Sin este argumento se reparten segun "
             "DISTRIBUCION_PLANTILLAS.",
    )
    analizador.add_argument(
        "--salida", type=Path, default=cfg.DIRECTORIO_SALIDAS,
        help="Directorio de salidas (por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--solo-pdf", action="store_true",
        help="Genera solo los PDF nativos, sin rasterizar ni degradar.",
    )
    analizador.add_argument(
        "--limpiar", action="store_true",
        help="Borra los archivos generados previamente en el directorio de salidas "
             "antes de generar el lote nuevo.",
    )
    return analizador


def _resumir(registros: list[dict]) -> str:
    """Arma el resumen por plantilla y por perfil de escaneo del lote generado."""
    por_plantilla = Counter(registro["plantilla"] for registro in registros)
    por_perfil = Counter(registro["perfil_escaneo"] for registro in registros)

    detalle_plantillas = ", ".join(
        f"{nombre}={cantidad}" for nombre, cantidad in sorted(por_plantilla.items())
    )
    detalle_perfiles = ", ".join(
        f"{nombre}={cantidad}" for nombre, cantidad in sorted(por_perfil.items())
    )
    return f"  plantillas: {detalle_plantillas}\n  escaneos:   {detalle_perfiles}"


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de la linea de comandos."""
    opciones = construir_analizador().parse_args(argumentos)

    if opciones.limpiar:
        eliminados = limpiar_salidas(opciones.salida)
        print(f"Limpieza previa: {eliminados} archivo(s) eliminado(s).")

    registros = generar_lote(
        cantidad=opciones.cantidad,
        semilla=opciones.semilla,
        nombre_perfil=opciones.perfil,
        plantilla_forzada=opciones.plantilla,
        directorio_salidas=opciones.salida,
        solo_pdf=opciones.solo_pdf,
    )

    directorio_gt = opciones.salida / cfg.SUBDIRECTORIO_GROUND_TRUTH
    print(f"Generados {len(registros)} contrato(s) con semilla {opciones.semilla}.")
    print(_resumir(registros))
    print(f"  ground truth: {directorio_gt / cfg.NOMBRE_MANIFIESTO}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
