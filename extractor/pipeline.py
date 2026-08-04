"""Orquestacion del extractor: de un PDF a un registro de campos.

Mantiene el mismo formato de registro que el ground truth del generador, de modo
que el modulo de evaluacion pueda comparar ambos sin traducir nada.
"""

from __future__ import annotations

import json
import time
from pathlib import Path

import configuracion as cfg
from extractor import campos as reglas
from extractor import texto as lector


def extraer_de_pdf(ruta_pdf: Path, id_documento: str | None = None) -> dict:
    """Extrae los campos de un contrato en PDF y devuelve su registro de prediccion.

    El registro incluye el metodo usado y el tiempo empleado, para poder analizar
    despues el costo de cada via de lectura ademas de su precision.
    """
    ruta_pdf = Path(ruta_pdf)
    comienzo = time.perf_counter()

    contenido = lector.extraer_texto_nativo(ruta_pdf)
    if not lector.tiene_texto_util(contenido):
        # El PDF es una imagen escaneada sin texto embebido. La via OCR se
        # implementa en la fase siguiente; por ahora se informa y se sigue.
        metodo = "sin_texto"
        valores = {campo: "" for campo in reglas.extraer_campos("")}
    else:
        metodo = cfg.METODO_TEXTO_NATIVO
        valores = reglas.extraer_campos(contenido)

    return {
        "id_documento": id_documento or ruta_pdf.stem,
        "origen": ruta_pdf.name,
        "metodo": metodo,
        "segundos": round(time.perf_counter() - comienzo, 4),
        "caracteres": len(contenido),
        "campos": valores,
    }


def extraer_de_directorio(directorio_pdf: Path) -> list[dict]:
    """Extrae todos los PDF de un directorio, ordenados por nombre de archivo."""
    directorio_pdf = Path(directorio_pdf)
    if not directorio_pdf.is_dir():
        raise ValueError(f"No existe el directorio de PDF: {directorio_pdf}")

    return [extraer_de_pdf(ruta) for ruta in sorted(directorio_pdf.glob("*.pdf"))]


def escribir_predicciones(registros: list[dict], ruta_salida: Path) -> Path:
    """Guarda las predicciones en JSONL, una linea por documento."""
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    lineas = [json.dumps(registro, ensure_ascii=False, sort_keys=True) for registro in registros]
    ruta_salida.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta_salida


def leer_predicciones(ruta: Path) -> list[dict]:
    """Carga un archivo de predicciones en JSONL."""
    with Path(ruta).open(encoding="utf-8") as archivo:
        return [json.loads(linea) for linea in archivo if linea.strip()]
