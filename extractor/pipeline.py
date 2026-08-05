"""Orquestacion del extractor: de un PDF a un registro de campos.

Mantiene el mismo formato de registro que el ground truth del generador, de modo
que el modulo de evaluacion pueda comparar ambos sin traducir nada.
"""

from __future__ import annotations

import json
import re
import time
from pathlib import Path

import configuracion as cfg
from extractor import campos as reglas
from extractor import ocr
from extractor import texto as lector

#: Un escaneo se nombra SINT-0001_p01.jpg; el ground truth lo indexa como SINT-0001.
_SUFIJO_PAGINA = re.compile(r"_p\d+$")


def _id_desde_archivo(ruta: Path) -> str:
    """Deduce el identificador del documento a partir del nombre del archivo."""
    return _SUFIJO_PAGINA.sub("", ruta.stem)


def obtener_texto(ruta: Path, motor: str) -> tuple[str, str]:
    """Obtiene el texto del documento y devuelve tambien que motor termino usandose.

    Con ``auto`` se prefiere el texto embebido, que es exacto y gratis, y solo se
    recurre al OCR cuando el documento no lo trae. Es la politica que tiene sentido
    en produccion: pagar por reconocer una imagen lo que ya venia escrito en el
    archivo seria tirar plata y precision a la vez.
    """
    if motor in (cfg.MOTOR_TESSERACT, cfg.MOTOR_DOCUMENTAI):
        return ocr.leer(ruta, motor), motor

    if ocr.es_imagen(ruta):
        if motor == cfg.MOTOR_NATIVO:
            raise ValueError(
                f"{ruta.name} es una imagen y no tiene texto embebido: "
                f"usar --motor tesseract o --motor documentai."
            )
        return ocr.leer(ruta, cfg.MOTOR_TESSERACT), cfg.MOTOR_TESSERACT

    contenido = lector.extraer_texto_nativo(ruta)
    if lector.tiene_texto_util(contenido):
        return contenido, cfg.MOTOR_NATIVO
    if motor == cfg.MOTOR_NATIVO:
        return contenido, cfg.MOTOR_NATIVO
    return ocr.leer(ruta, cfg.MOTOR_TESSERACT), cfg.MOTOR_TESSERACT


def extraer_de_pdf(ruta_pdf: Path, id_documento: str | None = None,
                   motor: str = cfg.MOTOR_POR_DEFECTO) -> dict:
    """Extrae los campos de un contrato y devuelve su registro de prediccion.

    Acepta tanto un PDF como una imagen escaneada. El registro incluye el motor
    usado y el tiempo empleado, para poder analizar despues el costo de cada via
    de lectura ademas de su precision.
    """
    ruta_pdf = Path(ruta_pdf)
    comienzo = time.perf_counter()

    contenido, motor_usado = obtener_texto(ruta_pdf, motor)
    # La correccion de confusiones de digitos solo tiene sentido sobre texto
    # reconocido: en texto embebido no hay errores de lectura que reparar.
    valores = reglas.extraer_campos(
        contenido, corregir_ocr=motor_usado != cfg.MOTOR_NATIVO,
    )

    return {
        "id_documento": id_documento or _id_desde_archivo(ruta_pdf),
        "origen": ruta_pdf.name,
        "metodo": motor_usado,
        "segundos": round(time.perf_counter() - comienzo, 4),
        "caracteres": len(contenido),
        "campos": valores,
    }


def extraer_de_directorio(directorio: Path,
                          motor: str = cfg.MOTOR_POR_DEFECTO) -> list[dict]:
    """Extrae todos los documentos de un directorio, ordenados por nombre.

    Reconoce tanto PDF como imagenes, de modo que el mismo comando sirve para el
    directorio de PDF nativos y para el de escaneos.
    """
    directorio = Path(directorio)
    if not directorio.is_dir():
        raise ValueError(f"No existe el directorio: {directorio}")

    extensiones = (".pdf", *ocr.EXTENSIONES_IMAGEN)
    rutas = sorted(
        ruta for ruta in directorio.iterdir()
        if ruta.is_file() and ruta.suffix.lower() in extensiones
    )
    return [extraer_de_pdf(ruta, motor=motor) for ruta in rutas]


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
