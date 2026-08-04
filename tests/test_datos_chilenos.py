"""Pruebas de los generadores de datos con forma chilena valida."""

from __future__ import annotations

import re
from datetime import date, timedelta
from random import Random

import pytest

import configuracion as cfg
from generador import datos_chilenos as dc

CANTIDAD_MUESTRA = 1_000
VOCALES = set("AEIOU")


def _digito_verificador_referencia(cuerpo: str) -> str:
    """Implementacion independiente del modulo 11, para contrastar la del proyecto.

    Se escribe distinto a proposito (suma ponderada explicita en vez de ciclo de
    factores) para que un error en una de las dos no se replique en la otra.
    """
    suma = 0
    multiplicador = 2
    for digito in reversed(str(cuerpo)):
        suma += int(digito) * multiplicador
        multiplicador = 2 if multiplicador == 7 else multiplicador + 1
    resto = suma % 11
    valor = 11 - resto
    if valor == 11:
        return "0"
    if valor == 10:
        return "K"
    return str(valor)


# =============================================================================
# RUT
# =============================================================================

@pytest.mark.parametrize("cuerpo, esperado", [
    ("1", "9"),
    ("12", "4"),
    ("11111111", "1"),
    ("99000001", "8"),
    ("50000001", "5"),
])
def test_digito_verificador_casos_conocidos(cuerpo, esperado):
    assert dc.calcular_digito_verificador(cuerpo) == esperado


def test_digito_verificador_coincide_con_implementacion_independiente():
    aleatorio = Random(2024)
    for _ in range(CANTIDAD_MUESTRA):
        cuerpo = str(aleatorio.randint(1_000_000, 99_999_999))
        assert dc.calcular_digito_verificador(cuerpo) == _digito_verificador_referencia(cuerpo)


def test_digito_verificador_rechaza_cuerpo_sin_digitos():
    with pytest.raises(ValueError):
        dc.calcular_digito_verificador("sin-numeros")


@pytest.mark.parametrize("rango", [cfg.RANGO_RUT_EMPRESA, cfg.RANGO_RUT_PERSONA])
def test_ruts_generados_son_validos_y_estan_en_rango(rango):
    aleatorio = Random(7)
    for _ in range(CANTIDAD_MUESTRA):
        rut = dc.generar_rut(aleatorio, rango)
        assert dc.rut_es_valido(rut), rut

        cuerpo = int(dc.normalizar_rut(rut).split("-")[0])
        assert rango[0] <= cuerpo <= rango[1]


def test_formato_del_rut_lleva_puntos_y_guion():
    assert dc.formatear_rut(99123456, "7") == "99.123.456-7"


@pytest.mark.parametrize("rut_invalido", ["99.123.456-0", "99123456", "", "-", "abc-1"])
def test_rut_es_valido_detecta_ruts_incorrectos(rut_invalido):
    assert not dc.rut_es_valido(rut_invalido)


def test_ruts_de_la_arrendadora_fija_son_validos():
    """La contraparte de configuracion.py tambien debe tener digitos correctos."""
    assert dc.rut_es_valido(cfg.ARRENDADOR_RUT)
    assert dc.rut_es_valido(cfg.ARRENDADOR_RUT_REPRESENTANTE)


# =============================================================================
# PATENTE
# =============================================================================

def test_patentes_generadas_cumplen_el_formato_nacional():
    aleatorio = Random(11)
    for _ in range(CANTIDAD_MUESTRA):
        patente = dc.generar_patente(aleatorio)
        assert re.fullmatch(r"[A-Z]{4}\d{2}", patente), patente
        assert dc.patente_es_valida(patente)


def test_patentes_no_contienen_vocales():
    aleatorio = Random(12)
    for _ in range(CANTIDAD_MUESTRA):
        letras = dc.generar_patente(aleatorio)[:cfg.LARGO_LETRAS_PATENTE]
        assert not VOCALES.intersection(letras), letras


def test_patentes_usan_un_prefijo_aun_no_emitido():
    """Garantiza que ninguna patente sintetica pueda existir en el registro real."""
    aleatorio = Random(16)
    for _ in range(CANTIDAD_MUESTRA):
        patente = dc.generar_patente(aleatorio)
        assert patente[0] in cfg.LETRAS_INICIALES_PATENTE, patente


@pytest.mark.parametrize("invalida", ["ABC12", "BCDF123", "BCDF-12", "bcdf12", ""])
def test_patente_es_valida_rechaza_formatos_incorrectos(invalida):
    assert not dc.patente_es_valida(invalida)


# =============================================================================
# FECHAS
# =============================================================================

def test_meses_entre_es_la_inversa_de_sumar_meses():
    aleatorio = Random(13)
    for _ in range(200):
        inicio = date(2020, 1, 1) + timedelta(days=aleatorio.randint(0, 2_000))
        meses = aleatorio.choice(cfg.PLAZOS_MESES_POSIBLES)
        assert dc.meses_entre(inicio, dc.sumar_meses(inicio, meses)) == meses


def test_sumar_meses_ajusta_el_dia_al_ultimo_valido():
    assert dc.sumar_meses(date(2024, 1, 31), 1) == date(2024, 2, 29)
    assert dc.sumar_meses(date(2023, 1, 31), 1) == date(2023, 2, 28)


def test_periodo_generado_es_coherente():
    aleatorio = Random(14)
    for _ in range(300):
        inicio, termino, plazo = dc.generar_periodo(aleatorio)
        fecha_inicio = date.fromisoformat(inicio)
        fecha_termino = date.fromisoformat(termino)

        assert fecha_termino > fecha_inicio
        assert plazo in cfg.PLAZOS_MESES_POSIBLES
        assert dc.meses_entre(fecha_inicio, fecha_termino) == plazo
        assert date.fromisoformat(cfg.FECHA_INICIO_MINIMA) <= fecha_inicio
        assert fecha_inicio <= date.fromisoformat(cfg.FECHA_INICIO_MAXIMA)


# =============================================================================
# CONTRATO Y DETERMINISMO
# =============================================================================

def test_valor_cuota_respeta_rango_y_multiplo():
    aleatorio = Random(15)
    for _ in range(500):
        valor = dc.generar_valor_cuota(aleatorio)
        assert cfg.RANGO_VALOR_CUOTA[0] <= valor <= cfg.RANGO_VALOR_CUOTA[1]
        assert valor % cfg.MULTIPLO_VALOR_CUOTA == 0


def test_la_misma_semilla_produce_el_mismo_contrato():
    primero = dc.generar_contrato(Random(99))
    segundo = dc.generar_contrato(Random(99))
    assert primero == segundo


def test_semillas_distintas_producen_contratos_distintos():
    assert dc.generar_contrato(Random(1)) != dc.generar_contrato(Random(2))


def test_contrato_generado_no_deja_campos_vacios():
    aleatorio = Random(21)
    for _ in range(50):
        contrato = dc.generar_contrato(aleatorio)
        for nombre, valor in contrato.a_diccionario().items():
            assert valor not in ("", None), nombre
