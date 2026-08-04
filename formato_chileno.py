"""Primitivas de RUT y patente chilenos, compartidas por todo el proyecto.

El generador las usa para producir valores validos y el extractor para
reconocerlos y devolverlos en forma canonica. Viven en la raiz, y no dentro de
uno de los dos paquetes, para que ninguno dependa del otro.
"""

from __future__ import annotations

import re

import configuracion as cfg

# Factores del algoritmo modulo 11 usado por el Servicio de Impuestos Internos.
_FACTORES_MODULO_11 = (2, 3, 4, 5, 6, 7)

_PATRON_PPU_NUEVA = re.compile(r"^[A-Z]{4}\d{2}$")

#: Confusiones tipicas del OCR sobre digitos. Se aplican solo al cuerpo del RUT,
#: donde cualquier caracter no numerico es necesariamente un error de lectura.
_CORRECCIONES_OCR_DIGITOS = str.maketrans({
    "O": "0", "o": "0",
    "I": "1", "l": "1", "|": "1",
    "S": "5",
    "B": "8",
})


# =============================================================================
# RUT
# =============================================================================

def calcular_digito_verificador(cuerpo: int | str) -> str:
    """Calcula el digito verificador de un RUT mediante el algoritmo modulo 11.

    Recorre los digitos del cuerpo de derecha a izquierda multiplicandolos por la
    serie ciclica 2,3,4,5,6,7 y acumula. El digito es ``11 - (suma % 11)``, con
    dos casos especiales: 11 se representa como ``"0"`` y 10 como ``"K"``.
    """
    digitos = re.sub(r"[^0-9]", "", str(cuerpo))
    if not digitos:
        raise ValueError("El cuerpo del RUT no contiene digitos.")

    acumulado = 0
    for posicion, digito in enumerate(reversed(digitos)):
        acumulado += int(digito) * _FACTORES_MODULO_11[posicion % len(_FACTORES_MODULO_11)]

    resto = 11 - (acumulado % 11)
    if resto == 11:
        return "0"
    if resto == 10:
        return "K"
    return str(resto)


def formatear_rut(cuerpo: int | str, digito_verificador: str) -> str:
    """Arma un RUT legible con separador de miles y guion: ``99.123.456-7``."""
    return f"{int(cuerpo):,}".replace(",", ".") + f"-{digito_verificador}"


def normalizar_rut(rut: str) -> str:
    """Deja un RUT en la forma compacta ``99123456-7`` (sin puntos, en mayuscula)."""
    limpio = re.sub(r"[^0-9Kk\-]", "", (rut or "")).upper()
    return limpio.strip("-")


def canonizar_rut(rut: str, corregir_ocr: bool = False) -> str:
    """Devuelve el RUT en la forma canonica del proyecto: ``99.123.456-7``.

    Con ``corregir_ocr`` activo, sustituye en el cuerpo las confusiones tipicas
    del reconocimiento optico (la letra O por un cero, la ele por un uno) antes
    de validar. El digito verificador nunca se corrige: si no cuadra, el RUT se
    considera mal leido y se descarta.
    """
    bruto = (rut or "").upper()

    # La correccion va ANTES de buscar el RUT, no despues: una letra en medio del
    # cuerpo parte el numero en dos y el patron ya no lo reconoceria completo.
    # Ninguna de las letras sustituidas es un digito verificador valido, asi que
    # aplicarla a toda la cadena no puede estropear el digito.
    if corregir_ocr:
        bruto = bruto.translate(_CORRECCIONES_OCR_DIGITOS)

    coincidencia = re.search(r"(\d[\d\.\s]*)[\-\s]*([\dK])\b", bruto)
    if coincidencia is None:
        return ""

    cuerpo_bruto, digito = coincidencia.groups()
    cuerpo = re.sub(r"[^0-9]", "", cuerpo_bruto)
    if not cuerpo:
        return ""

    return formatear_rut(cuerpo, digito)


def rut_es_valido(rut: str) -> bool:
    """Indica si el digito verificador del RUT coincide con el que corresponde."""
    normalizado = normalizar_rut(rut)
    if "-" not in normalizado:
        return False
    cuerpo, digito = normalizado.rsplit("-", 1)
    if not cuerpo.isdigit() or not digito:
        return False
    return calcular_digito_verificador(cuerpo) == digito


# =============================================================================
# PATENTE
# =============================================================================

def canonizar_patente(patente: str) -> str:
    """Devuelve la patente sin separador y en mayuscula: ``YWXT31``.

    Acepta las tres formas que imprimen las plantillas (``YWXT·31``, ``YWXT-31``
    y ``YWXT31``) y cualquier otro separador intermedio.
    """
    return re.sub(r"[^A-Z0-9]", "", (patente or "").upper())


def patente_es_valida(ppu: str) -> bool:
    """Verifica que la patente tenga la forma canonica de cuatro letras y dos digitos."""
    return bool(_PATRON_PPU_NUEVA.fullmatch(ppu or ""))


def patente_sin_vocales(ppu: str) -> bool:
    """Indica si la patente respeta el alfabeto del registro chileno, que excluye vocales."""
    if not patente_es_valida(ppu):
        return False
    return all(letra in cfg.LETRAS_PATENTE for letra in ppu[:cfg.LARGO_LETRAS_PATENTE])
