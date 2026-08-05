"""Conversion de lo leido en el documento a la forma canonica del esquema.

La normalizacion es responsabilidad del extractor, no de la evaluacion: el
documento puede imprimir la fecha como ``07/06/2022``, ``07-06-2022`` o
``7 de junio de 2022``, pero el campo ``fecha_inicio`` siempre se entrega como
``2022-06-07``. Ver ``extractor/README.md``.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date

import configuracion as cfg
from formato_chileno import (
    canonizar_patente,
    canonizar_rut,
    patente_es_valida,
    patente_sin_vocales,
    rut_es_valido,
)

# Mes escrito en palabras -> numero. Se indexa sin acentos ni mayusculas.
_MESES = {
    nombre: numero
    for numero, nombre in enumerate(cfg.MESES_EN_PALABRAS, start=1)
}

_FECHA_NUMERICA = re.compile(r"\b([0-3]?\d)\s*[/\-.]\s*([01]?\d)\s*[/\-.]\s*((?:19|20)\d{2})\b")
_FECHA_TEXTUAL = re.compile(
    r"\b([0-3]?\d)\s+de\s+([a-záéíóú]+)\s+(?:del?\s+)?((?:19|20)\d{2})\b",
    re.IGNORECASE,
)
_MONTO = re.compile(r"\$?\s*(\d{1,3}(?:[.\s]\d{3})+|\d{4,})")


def sin_acentos(texto: str) -> str:
    """Quita los acentos de una cadena, dejando la enie intacta como ``n``."""
    descompuesto = unicodedata.normalize("NFKD", texto or "")
    return "".join(c for c in descompuesto if not unicodedata.combining(c))


def canonizar_texto(bruto: str) -> str:
    """Limpia un valor de texto libre: colapsa espacios y poda puntuacion suelta."""
    limpio = " ".join((bruto or "").split())
    return limpio.strip(" ,;:|-")


def canonizar_fecha(bruto: str) -> str:
    """Devuelve la fecha en ISO ``YYYY-MM-DD``, venga numerica o escrita en palabras.

    Devuelve cadena vacia si no reconoce ninguna fecha o si el resultado no es un
    dia real del calendario (por ejemplo un 31 de febrero mal leido).
    """
    texto = bruto or ""

    coincidencia = _FECHA_NUMERICA.search(texto)
    if coincidencia is not None:
        dia, mes, ano = (int(g) for g in coincidencia.groups())
        return _armar_fecha(ano, mes, dia)

    coincidencia = _FECHA_TEXTUAL.search(texto)
    if coincidencia is not None:
        dia, nombre_mes, ano = coincidencia.groups()
        mes = _MESES.get(sin_acentos(nombre_mes).lower())
        if mes is not None:
            return _armar_fecha(int(ano), mes, int(dia))

    return ""


def _armar_fecha(ano: int, mes: int, dia: int) -> str:
    """Construye la fecha ISO, o cadena vacia si la combinacion no existe."""
    try:
        return date(ano, mes, dia).isoformat()
    except ValueError:
        return ""


def canonizar_monto(bruto: str) -> int | None:
    """Devuelve el monto como entero de pesos, sin separadores ni simbolo.

    Ignora el separador de miles y descarta cualquier sufijo del estilo ``.-``.
    Devuelve ``None`` si no encuentra una cifra.
    """
    coincidencia = _MONTO.search(bruto or "")
    if coincidencia is None:
        return None
    return int(re.sub(r"[^\d]", "", coincidencia.group(1)))


def canonizar_entero(bruto: str) -> int | None:
    """Devuelve el primer numero entero que aparezca en el texto."""
    coincidencia = re.search(r"\b(\d+)\b", bruto or "")
    return int(coincidencia.group(1)) if coincidencia is not None else None


def canonizar_rut_leido(bruto: str, corregir_ocr: bool = False) -> str:
    """Canoniza un RUT y lo descarta si el digito verificador no cuadra.

    Validar el digito es la comprobacion mas barata y mas util de todo el
    extractor: convierte un campo que se leyo mal en un campo vacio, y un campo
    vacio se detecta a simple vista mientras que uno incorrecto no.
    """
    canonico = canonizar_rut(bruto, corregir_ocr=corregir_ocr)
    if not canonico or not rut_es_valido(canonico):
        return ""
    return canonico


def canonizar_patente_leida(bruto: str) -> str:
    """Canoniza una patente al formato sin separador y descarta las imposibles.

    El registro chileno excluye las vocales de las patentes, asi que una vocal en
    la parte alfabetica solo puede venir de una lectura errada: la O de un cero
    mal reconocido es el caso tipico. Es la unica validacion disponible aqui,
    porque una patente no tiene digito verificador que confirmarla.

    Descartar el candidato hace que se pruebe la siguiente aparicion de la patente
    en el documento, que en algunos layouts esta impresa mas de una vez.
    """
    canonica = canonizar_patente(bruto)
    if patente_es_valida(canonica) and not patente_sin_vocales(canonica):
        return ""
    return canonica
