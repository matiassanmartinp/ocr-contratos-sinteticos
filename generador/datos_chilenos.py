"""Generacion de valores sinteticos con forma chilena valida.

Cubre RUT con digito verificador correcto, patente en formato nacional moderno y
el resto de los campos del contrato. Todas las funciones reciben una instancia de
``random.Random`` en lugar de usar el modulo global: asi el lote completo queda
determinado por una sola semilla y es reproducible byte a byte.
"""

from __future__ import annotations

import calendar
import re
from datetime import date, timedelta
from random import Random

import configuracion as cfg
from esquema_contrato import ContratoSintetico

# Factores del algoritmo modulo 11 usado por el Servicio de Impuestos Internos.
_FACTORES_MODULO_11 = (2, 3, 4, 5, 6, 7)

_PATRON_PPU_NUEVA = re.compile(r"^[A-Z]{4}\d{2}$")


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


def rut_es_valido(rut: str) -> bool:
    """Indica si el digito verificador del RUT coincide con el que corresponde."""
    normalizado = normalizar_rut(rut)
    if "-" not in normalizado:
        return False
    cuerpo, digito = normalizado.rsplit("-", 1)
    if not cuerpo.isdigit() or not digito:
        return False
    return calcular_digito_verificador(cuerpo) == digito


def generar_rut(aleatorio: Random, rango: tuple[int, int]) -> str:
    """Genera un RUT formateado y valido dentro del rango de cuerpos indicado."""
    cuerpo = aleatorio.randint(*rango)
    return formatear_rut(cuerpo, calcular_digito_verificador(cuerpo))


# =============================================================================
# PATENTE VEHICULAR
# =============================================================================

def generar_patente(aleatorio: Random) -> str:
    """Genera una patente en formato nacional moderno, sin separador (``XKDF12``).

    Usa solo el conjunto de letras admitido por el registro chileno, que excluye
    las vocales para evitar combinaciones ambiguas o inconvenientes. La primera
    letra se restringe ademas a un prefijo aun no emitido, de modo que la patente
    no pueda coincidir con la de un vehiculo real en circulacion.
    """
    letras = aleatorio.choice(cfg.LETRAS_INICIALES_PATENTE) + "".join(
        aleatorio.choice(cfg.LETRAS_PATENTE)
        for _ in range(cfg.LARGO_LETRAS_PATENTE - 1)
    )
    digitos = "".join(
        str(aleatorio.randint(0, 9))
        for _ in range(cfg.LARGO_DIGITOS_PATENTE)
    )
    return letras + digitos


def patente_es_valida(ppu: str) -> bool:
    """Verifica que la patente tenga la forma canonica de cuatro letras y dos digitos."""
    return bool(_PATRON_PPU_NUEVA.fullmatch(ppu or ""))


# =============================================================================
# PERSONAS, EMPRESAS Y DOMICILIOS
# =============================================================================

def generar_nombre_persona(aleatorio: Random) -> str:
    """Compone un nombre completo ficticio: nombre de pila y dos apellidos."""
    nombre = aleatorio.choice(cfg.NOMBRES_PILA)
    apellido_paterno, apellido_materno = aleatorio.sample(cfg.APELLIDOS, 2)
    return f"{nombre} {apellido_paterno} {apellido_materno}"


def generar_razon_social(aleatorio: Random) -> str:
    """Compone una razon social ficticia: nucleo, rubro y sufijo societario."""
    nucleo = aleatorio.choice(cfg.NUCLEOS_RAZON_SOCIAL)
    rubro = aleatorio.choice(cfg.RUBROS_RAZON_SOCIAL)
    sufijo = aleatorio.choice(cfg.SUFIJOS_SOCIETARIOS)
    return f"{nucleo} {rubro} {sufijo}"


def generar_domicilio(aleatorio: Random) -> str:
    """Compone un domicilio ficticio con via, numero, oficina opcional y comuna."""
    via = aleatorio.choice(cfg.TIPOS_VIA)
    calle = aleatorio.choice(cfg.NOMBRES_CALLE)
    numero = aleatorio.randint(100, 9_999)
    comuna = aleatorio.choice(cfg.COMUNAS)

    partes = [f"{via} {calle} {numero}"]
    if aleatorio.random() < 0.35:
        partes.append(f"oficina {aleatorio.randint(2, 180)}")
    partes.append(comuna)
    return ", ".join(partes)


# =============================================================================
# VEHICULO Y CONDICIONES ECONOMICAS
# =============================================================================

def generar_vehiculo(aleatorio: Random) -> tuple[str, str, int]:
    """Elige marca, modelo y ano de un vehiculo ficticio."""
    marca = aleatorio.choice(tuple(cfg.MARCAS_Y_MODELOS))
    modelo = aleatorio.choice(cfg.MARCAS_Y_MODELOS[marca])
    ano = aleatorio.randint(*cfg.RANGO_ANO_VEHICULO)
    return marca, modelo, ano


def generar_valor_cuota(aleatorio: Random) -> int:
    """Sortea el monto mensual del arriendo, redondeado al multiplo configurado."""
    minimo, maximo = cfg.RANGO_VALOR_CUOTA
    multiplo = cfg.MULTIPLO_VALOR_CUOTA
    pasos = aleatorio.randint(minimo // multiplo, maximo // multiplo)
    return pasos * multiplo


def generar_numero_pagare(aleatorio: Random) -> str:
    """Sortea el numero del pagare que garantiza el contrato."""
    return str(aleatorio.randint(*cfg.RANGO_NUMERO_PAGARE))


def sumar_meses(fecha: date, meses: int) -> date:
    """Suma meses calendario ajustando el dia al ultimo valido del mes destino."""
    total_meses = fecha.month - 1 + meses
    ano = fecha.year + total_meses // 12
    mes = total_meses % 12 + 1
    dia = min(fecha.day, calendar.monthrange(ano, mes)[1])
    return date(ano, mes, dia)


def meses_entre(fecha_inicio: date, fecha_termino: date) -> int:
    """Cuenta los meses calendario completos entre dos fechas.

    Inversa de :func:`sumar_meses`: se usa en las pruebas para comprobar que el
    campo ``plazo_meses`` sea coherente con las fechas impresas en el contrato.
    """
    meses = (fecha_termino.year - fecha_inicio.year) * 12 + (
        fecha_termino.month - fecha_inicio.month
    )
    if fecha_termino.day < fecha_inicio.day:
        # El dia se ajusto hacia atras (por ejemplo 31 de enero + 1 mes = 28 de
        # febrero); ese mes igual esta completo si no queda dia siguiente en el mes.
        ultimo_dia_destino = calendar.monthrange(fecha_termino.year, fecha_termino.month)[1]
        if fecha_termino.day != ultimo_dia_destino:
            meses -= 1
    return meses


def generar_periodo(aleatorio: Random) -> tuple[str, str, int]:
    """Sortea fecha de inicio, plazo y fecha de termino coherentes entre si.

    La fecha de termino siempre es posterior a la de inicio y el plazo en meses
    corresponde exactamente a la diferencia entre ambas.
    """
    minima = date.fromisoformat(cfg.FECHA_INICIO_MINIMA)
    maxima = date.fromisoformat(cfg.FECHA_INICIO_MAXIMA)
    dias_disponibles = (maxima - minima).days

    fecha_inicio = minima + timedelta(days=aleatorio.randint(0, dias_disponibles))
    plazo_meses = aleatorio.choice(cfg.PLAZOS_MESES_POSIBLES)
    fecha_termino = sumar_meses(fecha_inicio, plazo_meses)

    return fecha_inicio.isoformat(), fecha_termino.isoformat(), plazo_meses


# =============================================================================
# CONTRATO COMPLETO
# =============================================================================

def generar_contrato(aleatorio: Random) -> ContratoSintetico:
    """Arma un contrato sintetico completo con todos sus campos canonicos."""
    marca, modelo, ano = generar_vehiculo(aleatorio)
    fecha_inicio, fecha_termino, plazo_meses = generar_periodo(aleatorio)

    return ContratoSintetico(
        ppu=generar_patente(aleatorio),
        marca=marca,
        modelo=modelo,
        ano=ano,
        razon_social=generar_razon_social(aleatorio),
        rut_empresa=generar_rut(aleatorio, cfg.RANGO_RUT_EMPRESA),
        giro=aleatorio.choice(cfg.GIROS),
        domicilio=generar_domicilio(aleatorio),
        nombre_representante=generar_nombre_persona(aleatorio),
        rut_representante=generar_rut(aleatorio, cfg.RANGO_RUT_PERSONA),
        fecha_inicio=fecha_inicio,
        fecha_termino=fecha_termino,
        plazo_meses=plazo_meses,
        valor_cuota=generar_valor_cuota(aleatorio),
        numero_pagare=generar_numero_pagare(aleatorio),
    )
