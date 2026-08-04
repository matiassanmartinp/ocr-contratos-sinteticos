"""Orquestacion de la generacion de un lote de contratos.

Toda la aleatoriedad del lote proviene de una unica instancia de
``random.Random`` inicializada con la semilla: el PDF, la eleccion de plantilla,
el perfil de escaneo y hasta el ruido de la imagen se derivan de ahi. Dos
corridas con la misma semilla producen exactamente el mismo dataset.
"""

from __future__ import annotations

from pathlib import Path
from random import Random

import configuracion as cfg
from generador import escaneo, ground_truth, render_pdf
from generador.datos_chilenos import generar_contrato
from generador.plantillas import NOMBRES_PLANTILLAS, obtener_plantilla


def _pesos_plantillas() -> tuple[tuple[str, ...], tuple[float, ...]]:
    """Devuelve los nombres de plantilla y sus pesos segun la configuracion."""
    nombres = tuple(cfg.DISTRIBUCION_PLANTILLAS)
    pesos = tuple(cfg.DISTRIBUCION_PLANTILLAS[nombre] for nombre in nombres)

    desconocidas = set(nombres) - set(NOMBRES_PLANTILLAS)
    if desconocidas:
        raise ValueError(
            f"DISTRIBUCION_PLANTILLAS menciona plantillas inexistentes: "
            f"{sorted(desconocidas)}."
        )
    return nombres, pesos


def _elegir_plantilla(aleatorio: Random, plantilla_forzada: str | None) -> str:
    """Elige el layout del documento, respetando la distribucion configurada."""
    if plantilla_forzada is not None:
        obtener_plantilla(plantilla_forzada)  # valida el nombre
        return plantilla_forzada

    nombres, pesos = _pesos_plantillas()
    return aleatorio.choices(nombres, weights=pesos, k=1)[0]


def _elegir_perfil(aleatorio: Random, nombre_perfil: str) -> str:
    """Resuelve el perfil de escaneo del documento, expandiendo el valor ``mixto``."""
    if nombre_perfil == cfg.PERFIL_MIXTO:
        return aleatorio.choice(tuple(cfg.PERFILES_ESCANEO))

    escaneo.obtener_perfil(nombre_perfil)  # valida el nombre
    return nombre_perfil


def construir_id_documento(indice: int) -> str:
    """Arma el identificador correlativo del documento: ``SINT-0001``."""
    return f"{cfg.PREFIJO_ID_DOCUMENTO}-{indice:0{cfg.ANCHO_ID_DOCUMENTO}d}"


def limpiar_salidas(directorio_salidas: Path) -> int:
    """Borra los artefactos generados previamente y devuelve cuantos elimino.

    Solo toca los tres subdirectorios de salida conocidos y solo archivos: nunca
    elimina directorios ni sale del arbol de salidas.
    """
    subdirectorios = (
        cfg.SUBDIRECTORIO_PDF,
        cfg.SUBDIRECTORIO_ESCANEOS,
        cfg.SUBDIRECTORIO_GROUND_TRUTH,
    )

    eliminados = 0
    for nombre in subdirectorios:
        subdirectorio = directorio_salidas / nombre
        if not subdirectorio.is_dir():
            continue
        for archivo in subdirectorio.iterdir():
            if archivo.is_file() and archivo.name != ".gitkeep":
                archivo.unlink()
                eliminados += 1
    return eliminados


def generar_lote(
    cantidad: int = cfg.CANTIDAD_POR_DEFECTO,
    semilla: int = cfg.SEMILLA_POR_DEFECTO,
    nombre_perfil: str = cfg.PERFIL_ESCANEO_POR_DEFECTO,
    plantilla_forzada: str | None = None,
    directorio_salidas: Path | None = None,
    solo_pdf: bool = False,
) -> list[dict]:
    """Genera ``cantidad`` contratos completos y devuelve sus registros de ground truth.

    Por cada contrato produce el PDF nativo, opcionalmente su version escaneada y
    degradada, y el JSON con los valores canonicos de los campos. Al terminar
    escribe el manifiesto consolidado del lote.
    """
    if cantidad < 1:
        raise ValueError("La cantidad de contratos debe ser al menos 1.")

    directorio_salidas = Path(directorio_salidas or cfg.DIRECTORIO_SALIDAS)
    directorio_pdf = directorio_salidas / cfg.SUBDIRECTORIO_PDF
    directorio_escaneos = directorio_salidas / cfg.SUBDIRECTORIO_ESCANEOS
    directorio_ground_truth = directorio_salidas / cfg.SUBDIRECTORIO_GROUND_TRUTH

    aleatorio = Random(semilla)
    registros: list[dict] = []

    for indice in range(1, cantidad + 1):
        id_documento = construir_id_documento(indice)

        contrato = generar_contrato(aleatorio)
        nombre_plantilla = _elegir_plantilla(aleatorio, plantilla_forzada)
        perfil_documento = _elegir_perfil(aleatorio, nombre_perfil)

        ruta_pdf = render_pdf.renderizar_contrato(
            contrato,
            directorio_pdf / f"{id_documento}.pdf",
            nombre_plantilla,
            aleatorio,
        )

        rutas_escaneos: list[Path] = []
        if not solo_pdf:
            rutas_escaneos = escaneo.simular_escaneo(
                ruta_pdf,
                directorio_escaneos,
                perfil_documento,
                aleatorio,
                id_documento,
            )

        registro = ground_truth.construir_registro(
            id_documento=id_documento,
            contrato=contrato,
            nombre_plantilla=nombre_plantilla,
            variantes_formato=obtener_plantilla(nombre_plantilla).VARIANTES_FORMATO,
            nombre_perfil="ninguno" if solo_pdf else perfil_documento,
            semilla=semilla,
            ruta_pdf=ruta_pdf,
            rutas_escaneos=rutas_escaneos,
            directorio_base=directorio_salidas,
        )
        ground_truth.validar_registro(registro)
        ground_truth.guardar_ground_truth(registro, directorio_ground_truth)
        registros.append(registro)

    ground_truth.escribir_manifiesto(registros, directorio_ground_truth)
    return registros
