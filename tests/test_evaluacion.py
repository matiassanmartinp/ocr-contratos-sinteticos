"""Pruebas del arnes de evaluacion.

Usan predicciones fabricadas a mano, no la salida del extractor: se esta
validando el instrumento de medicion, y un instrumento hay que contrastarlo
contra casos cuyo resultado se conoce de antemano.
"""

from __future__ import annotations

import pytest

import configuracion as cfg
from esquema_contrato import CAMPOS_CONTRATO
from evaluacion import metricas
from evaluacion.comparador import (
    CORRECTO,
    INCORRECTO,
    OMITIDO,
    comparar_lote,
    comparar_valor,
)
from evaluacion.informe import redactar

CAMPOS_PERFECTOS = {
    "ppu": "YWXT31",
    "marca": "Kirumo",
    "modelo": "Kargo",
    "ano": 2017,
    "razon_social": "Loma Blanca Transportes S.A.",
    "rut_empresa": "99.453.789-K",
    "giro": "Transporte de carga por carretera",
    "domicilio": "Pasaje El Peumo 4463, Valparaíso",
    "nombre_representante": "Tamara Donoso Lagos",
    "rut_representante": "50.513.214-9",
    "fecha_inicio": "2022-06-07",
    "fecha_termino": "2023-06-07",
    "plazo_meses": 12,
    "valor_cuota": 205_000,
    "numero_pagare": "126681",
}


def _ground_truth(cantidad: int = 2, plantilla: str = "tabular") -> list[dict]:
    return [
        {
            "id_documento": f"SINT-{i:04d}",
            "plantilla": plantilla,
            "perfil_escaneo": "ninguno",
            "campos": dict(CAMPOS_PERFECTOS),
        }
        for i in range(1, cantidad + 1)
    ]


def _prediccion(id_documento: str, **cambios) -> dict:
    campos = dict(CAMPOS_PERFECTOS)
    campos.update(cambios)
    return {"id_documento": id_documento, "campos": campos}


# =============================================================================
# COMPARACION DE UN VALOR
# =============================================================================

def test_un_valor_identico_es_correcto():
    assert comparar_valor("Kargo", "Kargo") == (CORRECTO, 1.0)


def test_un_valor_vacio_es_omision_y_no_error():
    estado, similitud = comparar_valor("Kargo", "")
    assert estado == OMITIDO
    assert similitud == 0.0


def test_un_valor_distinto_es_error_y_trae_su_similitud():
    estado, similitud = comparar_valor("Kargo", "Karqo")
    assert estado == INCORRECTO
    assert 0.5 < similitud < 1.0


def test_los_numeros_se_comparan_por_su_texto():
    assert comparar_valor(2017, "2017")[0] == CORRECTO


def test_los_espacios_sobrantes_no_cuentan_como_error():
    assert comparar_valor("Loma Blanca", "  Loma   Blanca ")[0] == CORRECTO


# =============================================================================
# METRICAS
# =============================================================================

def test_una_prediccion_perfecta_da_cien_por_ciento():
    esperados = _ground_truth(3)
    obtenidos = [_prediccion(r["id_documento"]) for r in esperados]

    resultados, sin_prediccion = comparar_lote(esperados, obtenidos)
    assert sin_prediccion == []
    assert metricas.resumen_global(resultados)["exactitud"] == 1.0
    assert metricas.exactitud_por_documento(resultados)["exactitud"] == 1.0


def test_un_solo_campo_malo_invalida_el_documento_completo():
    """La exactitud por documento es la que importa si nadie revisa la salida."""
    esperados = _ground_truth(2)
    obtenidos = [
        _prediccion("SINT-0001"),
        _prediccion("SINT-0002", modelo="Kargo, fabricado el"),
    ]
    resultados, _ = comparar_lote(esperados, obtenidos)

    por_documento = metricas.exactitud_por_documento(resultados)
    assert por_documento["completos"] == 1
    assert por_documento["exactitud"] == 0.5

    # Pero por campo el dano es de un campo entre treinta.
    assert metricas.resumen_global(resultados)["exactitud"] == pytest.approx(29 / 30)


def test_las_omisiones_y_los_errores_se_cuentan_por_separado():
    esperados = _ground_truth(1)
    obtenidos = [_prediccion("SINT-0001", modelo="", marca="Otra Marca")]

    resultados, _ = comparar_lote(esperados, obtenidos)
    por_campo = metricas.exactitud_por_campo(resultados)

    assert por_campo["modelo"]["omitidos"] == 1
    assert por_campo["modelo"]["incorrectos"] == 0
    assert por_campo["marca"]["incorrectos"] == 1
    assert por_campo["marca"]["omitidos"] == 0


def test_un_documento_sin_prediccion_cuenta_como_omitido_y_no_se_descarta():
    esperados = _ground_truth(2)
    obtenidos = [_prediccion("SINT-0001")]

    resultados, sin_prediccion = comparar_lote(esperados, obtenidos)
    assert sin_prediccion == ["SINT-0002"]
    assert metricas.exactitud_por_documento(resultados)["documentos"] == 2
    assert metricas.resumen_global(resultados)["exactitud"] == 0.5


def test_el_desglose_separa_por_plantilla():
    esperados = _ground_truth(1, plantilla="formal") + [
        {**r, "id_documento": "SINT-0002", "plantilla": "tabular"}
        for r in _ground_truth(1)
    ]
    obtenidos = [
        _prediccion("SINT-0001", modelo=""),
        _prediccion("SINT-0002"),
    ]
    resultados, _ = comparar_lote(esperados, obtenidos)
    desglose = metricas.desglosar(resultados, esperados, "plantilla")

    assert desglose["tabular"]["exactitud"] == 1.0
    assert desglose["formal"]["exactitud"] < 1.0


def test_se_detecta_la_confusion_con_la_propia_arrendadora():
    """Tomar los datos de la otra parte es un error distinto de leer cualquier cosa."""
    esperados = _ground_truth(1)
    obtenidos = [_prediccion("SINT-0001", razon_social=cfg.ARRENDADOR_RAZON_SOCIAL)]

    resultados, _ = comparar_lote(esperados, obtenidos)
    confusiones = metricas.confusion_con_la_contraparte(resultados)
    assert confusiones == {"razon_social": 1}


def test_sin_confusiones_el_conteo_queda_vacio():
    esperados = _ground_truth(1)
    obtenidos = [_prediccion("SINT-0001")]
    resultados, _ = comparar_lote(esperados, obtenidos)
    assert metricas.confusion_con_la_contraparte(resultados) == {}


def test_los_peores_campos_salen_ordenados_de_peor_a_mejor():
    esperados = _ground_truth(4)
    obtenidos = [
        _prediccion("SINT-0001", modelo="", marca=""),
        _prediccion("SINT-0002", modelo=""),
        _prediccion("SINT-0003", modelo=""),
        _prediccion("SINT-0004"),
    ]
    resultados, _ = comparar_lote(esperados, obtenidos)
    peores = metricas.campos_problematicos(resultados)

    assert peores[0]["campo"] == "modelo"
    assert [entrada["campo"] for entrada in peores] == ["modelo", "marca"]


# =============================================================================
# INFORME
# =============================================================================

def test_el_informe_menciona_los_campos_y_las_cifras_clave():
    esperados = _ground_truth(2)
    obtenidos = [_prediccion("SINT-0001"), _prediccion("SINT-0002", modelo="")]
    resultados, sin_prediccion = comparar_lote(esperados, obtenidos)

    texto = redactar(resultados, esperados, sin_prediccion, etiqueta="prueba")

    assert "prueba" in texto
    assert "modelo" in texto
    assert "Documentos evaluados : 2" in texto
    for campo in CAMPOS_CONTRATO:
        assert campo in texto
