"""Pruebas del extractor de extremo a extremo, contra el ground truth del generador."""

from __future__ import annotations

import pytest

import configuracion as cfg
from esquema_contrato import CAMPOS_CONTRATO
from extractor import campos as reglas
from extractor import texto as lector
from extractor.pipeline import extraer_de_directorio, extraer_de_pdf
from generador.lote import generar_lote
from generador.plantillas import NOMBRES_PLANTILLAS

CANTIDAD = 9
SEMILLA = 314


@pytest.fixture(scope="module")
def lote_extraido(tmp_path_factory):
    """Genera un lote de PDF nativos y lo pasa por el extractor."""
    directorio = tmp_path_factory.mktemp("lote")
    esperados = generar_lote(
        cantidad=CANTIDAD, semilla=SEMILLA, directorio_salidas=directorio, solo_pdf=True,
    )
    obtenidos = extraer_de_directorio(directorio / cfg.SUBDIRECTORIO_PDF)
    return esperados, {registro["id_documento"]: registro for registro in obtenidos}


# =============================================================================
# EXTRACCION COMPLETA
# =============================================================================

def test_se_extrae_un_registro_por_pdf(lote_extraido):
    esperados, obtenidos = lote_extraido
    assert len(obtenidos) == len(esperados) == CANTIDAD


def test_el_metodo_usado_es_texto_nativo(lote_extraido):
    _, obtenidos = lote_extraido
    for registro in obtenidos.values():
        assert registro["metodo"] == cfg.METODO_TEXTO_NATIVO


def test_todos_los_campos_del_esquema_estan_presentes(lote_extraido):
    _, obtenidos = lote_extraido
    for registro in obtenidos.values():
        assert set(registro["campos"]) == set(CAMPOS_CONTRATO)


def test_sobre_texto_nativo_se_extraen_todos_los_campos_correctamente(lote_extraido):
    """Es el techo de la logica de parseo, sin ruido de OCR de por medio."""
    esperados, obtenidos = lote_extraido
    fallos = []
    for registro in esperados:
        campos_esperados = registro["campos"]
        campos_obtenidos = obtenidos[registro["id_documento"]]["campos"]
        for campo in CAMPOS_CONTRATO:
            if str(campos_obtenidos[campo]) != str(campos_esperados[campo]):
                fallos.append(
                    f"{registro['id_documento']} [{registro['plantilla']}] {campo}: "
                    f"esperado {campos_esperados[campo]!r}, "
                    f"obtenido {campos_obtenidos[campo]!r}"
                )
    assert not fallos, "\n".join(fallos)


@pytest.mark.parametrize("nombre_plantilla", NOMBRES_PLANTILLAS)
def test_cada_layout_se_extrae_igual_de_bien(tmp_path, nombre_plantilla):
    """Ningun campo puede depender de la maquetacion de una plantilla concreta."""
    esperados = generar_lote(
        cantidad=3, semilla=99, plantilla_forzada=nombre_plantilla,
        directorio_salidas=tmp_path, solo_pdf=True,
    )
    obtenidos = {
        registro["id_documento"]: registro["campos"]
        for registro in extraer_de_directorio(tmp_path / cfg.SUBDIRECTORIO_PDF)
    }
    for registro in esperados:
        for campo in CAMPOS_CONTRATO:
            assert str(obtenidos[registro["id_documento"]][campo]) == str(registro["campos"][campo]), (
                f"{nombre_plantilla}/{campo}"
            )


# =============================================================================
# LA CONFUSION QUE HAY QUE EVITAR
# =============================================================================

def test_nunca_se_devuelven_los_datos_de_la_propia_arrendadora(lote_extraido):
    """El error mas probable: extraer la parte equivocada del contrato.

    Los datos de la arrendadora aparecen en todos los documentos y encajan en los
    mismos patrones que los del arrendatario.
    """
    _, obtenidos = lote_extraido
    for registro in obtenidos.values():
        for campo, valor_propio in cfg.VALORES_PROPIOS.items():
            assert registro["campos"][campo] != valor_propio, (
                f"{registro['id_documento']}: {campo} tomo el dato de la arrendadora"
            )


def test_los_ruts_se_clasifican_por_contexto_y_no_por_tramo():
    """El layout compacto rotula la cedula con un escueto RUT:, sin decir cedula."""
    texto = (
        "R. SOCIAL: Andes Austral SpA RUT EMP.: 99.283.060-3 "
        "REP. LEGAL: Karina Norambuena Illanes RUT: 51.110.460-2"
    )
    de_empresa, de_persona = reglas.clasificar_ruts(texto)
    assert de_empresa == ["99.283.060-3"]
    assert de_persona == ["51.110.460-2"]


# =============================================================================
# ROBUSTEZ
# =============================================================================

def test_un_texto_vacio_no_revienta_y_devuelve_todo_vacio():
    campos = reglas.extraer_campos("")
    assert set(campos) == set(CAMPOS_CONTRATO)
    assert all(valor == "" for valor in campos.values())


def test_un_rut_con_digito_alterado_se_omite_en_vez_de_devolverse():
    """Un campo vacio se ve; uno con un valor equivocado se cuela hasta la planilla."""
    texto = "R. SOCIAL: Andes Austral SpA RUT EMP.: 99.283.060-9"
    assert reglas.extraer_rut_empresa(texto) == ""


def test_se_detecta_cuando_el_pdf_no_trae_texto_util():
    assert not lector.tiene_texto_util("")
    assert not lector.tiene_texto_util("x" * (cfg.MINIMO_CARACTERES_TEXTO_NATIVO - 1))
    assert lector.tiene_texto_util("x" * cfg.MINIMO_CARACTERES_TEXTO_NATIVO)


def test_el_registro_de_prediccion_trae_la_metadata_de_proceso(tmp_path):
    esperados = generar_lote(
        cantidad=1, semilla=8, directorio_salidas=tmp_path, solo_pdf=True,
    )
    ruta_pdf = tmp_path / esperados[0]["archivos"]["pdf"]
    registro = extraer_de_pdf(ruta_pdf)

    assert registro["id_documento"] == esperados[0]["id_documento"]
    assert registro["segundos"] >= 0
    assert registro["caracteres"] > cfg.MINIMO_CARACTERES_TEXTO_NATIVO
