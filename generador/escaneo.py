"""Simulacion de documentos escaneados.

Rasteriza un PDF nativo a imagen y le aplica las degradaciones tipicas de un
escaner de oficina: inclinacion leve del papel sobre el vidrio, iluminacion
despareja, desenfoque optico, ruido del sensor, motas de polvo y compresion JPEG
agresiva.

Todos los parametros vienen de ``configuracion.PERFILES_ESCANEO``; este modulo no
define ninguna constante de degradacion propia.
"""

from __future__ import annotations

from pathlib import Path
from random import Random

import numpy as np
from PIL import Image, ImageEnhance, ImageFilter

import configuracion as cfg
from rasterizado import rasterizar_pdf


def obtener_perfil(nombre_perfil: str) -> dict:
    """Devuelve los parametros del perfil de escaneo o falla con un mensaje claro."""
    try:
        return cfg.PERFILES_ESCANEO[nombre_perfil]
    except KeyError:
        disponibles = ", ".join(cfg.PERFILES_ESCANEO)
        raise ValueError(
            f"Perfil de escaneo desconocido: {nombre_perfil!r}. "
            f"Disponibles: {disponibles}."
        ) from None


def _aplicar_vineteado(arreglo: np.ndarray, intensidad: float) -> np.ndarray:
    """Oscurece progresivamente hacia los bordes, como la tapa mal cerrada de un escaner."""
    if intensidad <= 0:
        return arreglo

    alto, ancho = arreglo.shape
    eje_vertical = np.linspace(-1.0, 1.0, alto)[:, None]
    eje_horizontal = np.linspace(-1.0, 1.0, ancho)[None, :]
    radio = np.sqrt(eje_horizontal ** 2 + eje_vertical ** 2) / np.sqrt(2.0)

    return arreglo * (1.0 - intensidad * radio ** 2)


def _aplicar_sal_y_pimienta(
    arreglo: np.ndarray,
    tasa: float,
    generador: np.random.Generator,
) -> np.ndarray:
    """Salpica pixeles negros y blancos aislados, como polvo sobre el vidrio."""
    if tasa <= 0:
        return arreglo

    sorteo = generador.random(arreglo.shape)
    arreglo = np.where(sorteo < tasa / 2.0, 0.0, arreglo)
    arreglo = np.where(sorteo > 1.0 - tasa / 2.0, 255.0, arreglo)
    return arreglo


def degradar_imagen(
    imagen: Image.Image,
    parametros: dict,
    aleatorio: Random,
) -> Image.Image:
    """Aplica la cadena completa de degradaciones de un escaneo a una pagina.

    El orden imita el recorrido fisico de la senal: primero el papel se inclina y
    se ilumina de forma despareja, luego la optica desenfoca y recien al final el
    sensor agrega ruido.
    """
    generador = np.random.default_rng(aleatorio.getrandbits(32))

    # 1. Inclinacion del papel sobre el vidrio del escaner.
    grados = aleatorio.uniform(*parametros["grados_rotacion"])
    imagen = imagen.rotate(grados, resample=Image.BICUBIC, fillcolor=255)

    # 2. Iluminacion despareja.
    arreglo = np.asarray(imagen, dtype=np.float32)
    arreglo = _aplicar_vineteado(arreglo, parametros["intensidad_vineteado"])
    imagen = Image.fromarray(np.clip(arreglo, 0, 255).astype(np.uint8), mode="L")

    # 3. Desenfoque optico.
    radio = parametros["radio_desenfoque"]
    if radio > 0:
        imagen = imagen.filter(ImageFilter.GaussianBlur(radius=radio))

    # 4. Ruido del sensor y motas de polvo.
    arreglo = np.asarray(imagen, dtype=np.float32)
    sigma = parametros["sigma_ruido"]
    if sigma > 0:
        arreglo = arreglo + generador.normal(0.0, sigma, arreglo.shape)
    arreglo = _aplicar_sal_y_pimienta(arreglo, parametros["tasa_sal_pimienta"], generador)
    imagen = Image.fromarray(np.clip(arreglo, 0, 255).astype(np.uint8), mode="L")

    # 5. Respuesta del sensor: brillo y contraste.
    imagen = ImageEnhance.Brightness(imagen).enhance(
        aleatorio.uniform(*parametros["factor_brillo"])
    )
    imagen = ImageEnhance.Contrast(imagen).enhance(
        aleatorio.uniform(*parametros["factor_contraste"])
    )

    return imagen


def simular_escaneo(
    ruta_pdf: Path,
    directorio_destino: Path,
    nombre_perfil: str,
    aleatorio: Random,
    id_documento: str,
) -> list[Path]:
    """Rasteriza el PDF y guarda cada pagina degradada como JPEG.

    Devuelve las rutas de las imagenes generadas, una por pagina del documento.
    """
    parametros = obtener_perfil(nombre_perfil)
    directorio_destino.mkdir(parents=True, exist_ok=True)

    rutas_generadas: list[Path] = []
    for numero, pagina in enumerate(rasterizar_pdf(ruta_pdf, parametros["dpi"]), start=1):
        degradada = degradar_imagen(pagina, parametros, aleatorio)
        ruta_imagen = directorio_destino / f"{id_documento}_p{numero:02d}{cfg.EXTENSION_ESCANEO}"
        degradada.save(
            ruta_imagen,
            format="JPEG",
            quality=parametros["calidad_jpeg"],
            optimize=True,
        )
        rutas_generadas.append(ruta_imagen)

    return rutas_generadas
