"""Interfaz de linea de comandos del extractor.

    python -m extractor --entrada salidas/pdf
"""

from __future__ import annotations

import argparse
import sys
from collections import Counter
from pathlib import Path

import configuracion as cfg
from extractor.pipeline import escribir_predicciones, extraer_de_directorio, extraer_de_pdf

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def construir_analizador() -> argparse.ArgumentParser:
    """Define los argumentos aceptados por la linea de comandos."""
    analizador = argparse.ArgumentParser(
        prog="python -m extractor",
        description="Extrae los campos de contratos en PDF y guarda las predicciones.",
    )
    analizador.add_argument(
        "--entrada", type=Path,
        default=cfg.DIRECTORIO_SALIDAS / cfg.SUBDIRECTORIO_PDF,
        help="Directorio con los documentos, o la ruta de uno suelto. Acepta PDF "
             "e imagenes escaneadas (por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--motor", default=cfg.MOTOR_POR_DEFECTO, choices=cfg.MOTORES_DISPONIBLES,
        help="Motor de lectura. 'auto' usa el texto embebido si lo hay y cae a "
             "Tesseract si no; 'documentai' requiere credenciales de Google Cloud "
             "(por defecto: %(default)s).",
    )
    analizador.add_argument(
        "--salida", type=Path, default=None,
        help=f"Archivo JSONL de predicciones "
             f"(por defecto: <salidas>/{cfg.NOMBRE_ARCHIVO_PREDICCIONES}).",
    )
    return analizador


def main(argumentos: list[str] | None = None) -> int:
    """Punto de entrada de la linea de comandos."""
    opciones = construir_analizador().parse_args(argumentos)

    if opciones.entrada.is_file():
        registros = [extraer_de_pdf(opciones.entrada, motor=opciones.motor)]
    else:
        registros = extraer_de_directorio(opciones.entrada, motor=opciones.motor)

    if not registros:
        print(f"No se encontro ningun PDF en {opciones.entrada}.")
        return 1

    ruta_salida = opciones.salida or (
        cfg.DIRECTORIO_SALIDAS / cfg.NOMBRE_ARCHIVO_PREDICCIONES
    )
    escribir_predicciones(registros, ruta_salida)

    vacios = sum(
        1 for registro in registros for valor in registro["campos"].values() if valor == ""
    )
    total_campos = sum(len(registro["campos"]) for registro in registros)
    metodos = Counter(registro["metodo"] for registro in registros)

    segundos = sum(registro["segundos"] for registro in registros)
    print(f"Procesados {len(registros)} documento(s) en {segundos:.1f} s "
          f"({segundos / len(registros):.2f} s por documento).")
    print(f"  metodos:      {dict(metodos)}")
    print(f"  campos vacios: {vacios} de {total_campos}")
    print(f"  predicciones:  {ruta_salida}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
