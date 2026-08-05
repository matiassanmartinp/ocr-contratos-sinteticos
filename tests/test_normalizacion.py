"""Pruebas de la conversion de lo leido a la forma canonica del esquema."""

from __future__ import annotations

import pytest

from extractor import normalizacion as norma

# =============================================================================
# FECHAS
# =============================================================================

@pytest.mark.parametrize("bruto", [
    "07/06/2022",
    "07-06-2022",
    "07.06.2022",
    "7/6/2022",
    "7 de junio de 2022",
    "7 de junio del 2022",
    "Fecha de inicio 07/06/2022",
    "El uso empieza el 7 de junio de 2022 y termina",
])
def test_las_tres_formas_de_escribir_la_fecha_dan_el_mismo_iso(bruto):
    """El ground truth guarda ISO; cada plantilla imprime un formato distinto."""
    assert norma.canonizar_fecha(bruto) == "2022-06-07"


def test_la_fecha_textual_admite_mes_con_acento():
    assert norma.canonizar_fecha("3 de diciembre de 2024") == "2024-12-03"


@pytest.mark.parametrize("invalida", ["", "sin fecha", "32/13/2022", "31 de febrero de 2022"])
def test_una_fecha_imposible_se_descarta_en_vez_de_inventarse(invalida):
    assert norma.canonizar_fecha(invalida) == ""


# =============================================================================
# MONTOS
# =============================================================================

@pytest.mark.parametrize("bruto", [
    "$205.000",
    "$205.000.-",
    "205.000",
    "Renta mensual $205.000",
    "doscientos cinco mil pesos ($205.000)",
])
def test_las_variantes_de_monto_dan_el_mismo_entero(bruto):
    assert norma.canonizar_monto(bruto) == 205_000


def test_un_texto_sin_cifras_no_produce_monto():
    assert norma.canonizar_monto("sin monto") is None


# =============================================================================
# PATENTE
# =============================================================================

@pytest.mark.parametrize("bruto", ["YWXT31", "YWXT-31", "YWXT·31", "ywxt 31"])
def test_las_variantes_de_patente_dan_la_forma_sin_separador(bruto):
    assert norma.canonizar_patente_leida(bruto) == "YWXT31"


# =============================================================================
# RUT
# =============================================================================

def test_un_rut_valido_se_canoniza_con_puntos_y_guion():
    assert norma.canonizar_rut_leido("99453789-K") == "99.453.789-K"
    assert norma.canonizar_rut_leido("99.453.789-K") == "99.453.789-K"


def test_un_rut_con_digito_verificador_incorrecto_se_descarta():
    """Preferir un campo vacio a uno con un valor mal leido.

    Validar el digito verificador es la comprobacion mas barata del extractor:
    convierte un error silencioso en una omision visible.
    """
    assert norma.canonizar_rut_leido("99.453.789-3") == ""


def test_la_correccion_de_ocr_recupera_un_rut_con_letras_por_digitos():
    """El OCR confunde O con cero e I con uno; el digito verificador lo confirma."""
    assert norma.canonizar_rut_leido("994S3789-K", corregir_ocr=True) == "99.453.789-K"


def test_la_correccion_de_ocr_no_inventa_un_rut_cuando_igual_no_cuadra():
    assert norma.canonizar_rut_leido("11111111-9", corregir_ocr=True) == ""


# =============================================================================
# TEXTO
# =============================================================================

def test_el_texto_libre_pierde_espacios_sobrantes_y_puntuacion_de_borde():
    sucio = "  Loma  Blanca   Transportes S.A. ,"
    assert norma.canonizar_texto(sucio) == "Loma Blanca Transportes S.A."


def test_sin_acentos_deja_las_vocales_planas():
    assert norma.sin_acentos("Valparaíso Concepción") == "Valparaiso Concepcion"
