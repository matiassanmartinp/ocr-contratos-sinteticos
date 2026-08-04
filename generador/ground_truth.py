"""Persistencia del ground truth de cada contrato generado.

Por cada documento se escribe un JSON con los valores canonicos de sus campos y
la metadata necesaria para reproducirlo y para analizar despues los errores del
extractor (que plantilla se uso, con que perfil de escaneo, con que variantes de
formato). Ademas se consolida un manifiesto en formato JSONL para evaluar lotes
completos sin abrir archivo por archivo.

Las rutas se guardan siempre relativas al directorio de salidas y con separador
``/``: asi dos corridas con la misma semilla producen JSON identicos byte a byte
en cualquier maquina.
"""

from __future__ import annotations

import json
from pathlib import Path

import configuracion as cfg
from esquema_contrato import CAMPOS_CONTRATO, ContratoSintetico


def _ruta_relativa(ruta: Path, directorio_base: Path) -> str:
    """Expresa una ruta relativa al directorio de salidas, con separador ``/``."""
    return ruta.resolve().relative_to(directorio_base.resolve()).as_posix()


def construir_registro(
    id_documento: str,
    contrato: ContratoSintetico,
    nombre_plantilla: str,
    variantes_formato: dict,
    nombre_perfil: str,
    semilla: int,
    ruta_pdf: Path,
    rutas_escaneos: list[Path],
    directorio_base: Path,
) -> dict:
    """Arma el registro de ground truth de un contrato, listo para serializar."""
    return {
        "id_documento": id_documento,
        "plantilla": nombre_plantilla,
        "perfil_escaneo": nombre_perfil,
        "semilla": semilla,
        "formatos_usados": dict(variantes_formato),
        "archivos": {
            "pdf": _ruta_relativa(ruta_pdf, directorio_base),
            "escaneos": [_ruta_relativa(ruta, directorio_base) for ruta in rutas_escaneos],
        },
        "campos": contrato.a_diccionario(),
    }


def guardar_ground_truth(registro: dict, directorio: Path) -> Path:
    """Escribe el JSON individual de un contrato y devuelve su ruta."""
    directorio.mkdir(parents=True, exist_ok=True)
    ruta_json = directorio / f"{registro['id_documento']}.json"
    ruta_json.write_text(
        json.dumps(registro, ensure_ascii=False, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return ruta_json


def escribir_manifiesto(registros: list[dict], directorio: Path) -> Path:
    """Consolida todos los registros en un JSONL, una linea por contrato."""
    directorio.mkdir(parents=True, exist_ok=True)
    ruta_manifiesto = directorio / cfg.NOMBRE_MANIFIESTO

    lineas = [
        json.dumps(registro, ensure_ascii=False, sort_keys=True)
        for registro in registros
    ]
    ruta_manifiesto.write_text("\n".join(lineas) + "\n", encoding="utf-8")
    return ruta_manifiesto


def leer_manifiesto(ruta_manifiesto: Path) -> list[dict]:
    """Carga un manifiesto JSONL como lista de registros."""
    with ruta_manifiesto.open(encoding="utf-8") as archivo:
        return [json.loads(linea) for linea in archivo if linea.strip()]


def validar_registro(registro: dict) -> None:
    """Comprueba que el registro traiga todos los campos del esquema.

    Falla temprano si alguien agrega un campo a ``ContratoSintetico`` y olvida
    propagarlo al generador.
    """
    campos_presentes = set(registro.get("campos", {}))
    faltantes = set(CAMPOS_CONTRATO) - campos_presentes
    if faltantes:
        raise ValueError(
            f"Ground truth incompleto en {registro.get('id_documento')}: "
            f"faltan los campos {sorted(faltantes)}."
        )
