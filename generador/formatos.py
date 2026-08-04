"""Variantes de formato para imprimir un mismo valor canonico.

El ground truth guarda siempre el valor canonico (fecha ISO, monto entero,
patente sin separador). Cada plantilla elige aqui como renderizarlo, de modo que
el extractor tenga que reconocer el dato y no una cadena literal fija.
"""

from __future__ import annotations

from datetime import date

import configuracion as cfg

# -- Numeros a palabras (0 a 999.999) ----------------------------------------

_UNIDADES = (
    "cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho",
    "nueve", "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis",
    "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós",
    "veintitrés", "veinticuatro", "veinticinco", "veintiséis", "veintisiete",
    "veintiocho", "veintinueve",
)

_DECENAS = (
    "", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta",
    "ochenta", "noventa",
)

_CENTENAS = (
    "", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos",
    "seiscientos", "setecientos", "ochocientos", "novecientos",
)


def _menor_a_mil_en_palabras(numero: int) -> str:
    """Escribe en palabras un entero entre 0 y 999."""
    if numero < 30:
        return _UNIDADES[numero]
    if numero < 100:
        decena, unidad = divmod(numero, 10)
        if unidad == 0:
            return _DECENAS[decena]
        return f"{_DECENAS[decena]} y {_UNIDADES[unidad]}"
    if numero == 100:
        return "cien"
    centena, resto = divmod(numero, 100)
    if resto == 0:
        return _CENTENAS[centena]
    return f"{_CENTENAS[centena]} {_menor_a_mil_en_palabras(resto)}"


def numero_a_palabras(numero: int) -> str:
    """Escribe en palabras un entero entre 0 y 999.999.

    Aplica la apocope del castellano: ``21.000`` se lee "veintiun mil" y no
    "veintiuno mil".
    """
    if not 0 <= numero <= 999_999:
        raise ValueError("Solo se admiten enteros entre 0 y 999.999.")
    if numero < 1_000:
        return _menor_a_mil_en_palabras(numero)

    miles, resto = divmod(numero, 1_000)
    if miles == 1:
        parte_miles = "mil"
    else:
        parte_miles = f"{_menor_a_mil_en_palabras(miles)} mil"
        parte_miles = parte_miles.replace("veintiuno mil", "veintiún mil")
        parte_miles = parte_miles.replace("uno mil", "un mil")

    if resto == 0:
        return parte_miles
    return f"{parte_miles} {_menor_a_mil_en_palabras(resto)}"


# -- Fechas -------------------------------------------------------------------

def fecha_textual(fecha_iso: str) -> str:
    """Convierte ``2024-03-12`` en ``12 de marzo de 2024``."""
    valor = date.fromisoformat(fecha_iso)
    return f"{valor.day} de {cfg.MESES_EN_PALABRAS[valor.month - 1]} de {valor.year}"


def fecha_numerica(fecha_iso: str, separador: str = "/") -> str:
    """Convierte ``2024-03-12`` en ``12/03/2024`` con el separador indicado."""
    valor = date.fromisoformat(fecha_iso)
    return f"{valor.day:02d}{separador}{valor.month:02d}{separador}{valor.year}"


# -- Montos -------------------------------------------------------------------

def monto_con_puntos(valor: int) -> str:
    """Formatea ``450000`` como ``450.000``."""
    return f"{valor:,}".replace(",", ".")


def monto_con_simbolo(valor: int) -> str:
    """Formatea ``450000`` como ``$450.000``."""
    return f"${monto_con_puntos(valor)}"


def monto_con_sufijo(valor: int) -> str:
    """Formatea ``450000`` como ``$450.000.-``, uso frecuente en documentos chilenos."""
    return f"${monto_con_puntos(valor)}.-"


def monto_en_palabras(valor: int) -> str:
    """Formatea ``450000`` como ``cuatrocientos cincuenta mil pesos ($450.000)``."""
    return f"{numero_a_palabras(valor)} pesos ({monto_con_simbolo(valor)})"


# -- Patente ------------------------------------------------------------------

def patente_punto_medio(ppu: str) -> str:
    """Formatea ``BCDF12`` como ``BCDF·12``."""
    return f"{ppu[:cfg.LARGO_LETRAS_PATENTE]}·{ppu[cfg.LARGO_LETRAS_PATENTE:]}"


def patente_guion(ppu: str) -> str:
    """Formatea ``BCDF12`` como ``BCDF-12``."""
    return f"{ppu[:cfg.LARGO_LETRAS_PATENTE]}-{ppu[cfg.LARGO_LETRAS_PATENTE:]}"


def patente_sin_separador(ppu: str) -> str:
    """Devuelve la patente tal cual, sin separador: ``BCDF12``."""
    return ppu
