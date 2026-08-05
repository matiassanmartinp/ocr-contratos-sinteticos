"""Pruebas de la generacion de un lote completo y de su ground truth.

Todas escriben en el ``tmp_path`` de pytest: nunca tocan el directorio
``salidas/`` del proyecto.
"""

from __future__ import annotations

import json
from datetime import date

import fitz  # PyMuPDF
import pytest

import configuracion as cfg
from esquema_contrato import CAMPOS_CONTRATO
from generador.datos_chilenos import meses_entre, patente_es_valida, rut_es_valido
from generador.ground_truth import leer_manifiesto
from generador.lote import construir_id_documento, generar_lote
from generador.plantillas import NOMBRES_PLANTILLAS

CANTIDAD = 4
SEMILLA = 2024


@pytest.fixture
def lote(tmp_path):
    """Genera un lote pequeno sin escaneo y devuelve registros y directorio."""
    registros = generar_lote(
        cantidad=CANTIDAD,
        semilla=SEMILLA,
        directorio_salidas=tmp_path,
        solo_pdf=True,
    )
    return registros, tmp_path


# =============================================================================
# ARTEFACTOS GENERADOS
# =============================================================================

def test_se_genera_un_pdf_y_un_json_por_contrato(lote):
    registros, directorio = lote
    assert len(registros) == CANTIDAD

    for registro in registros:
        assert (directorio / registro["archivos"]["pdf"]).is_file()
        carpeta = directorio / cfg.SUBDIRECTORIO_GROUND_TRUTH
        ruta_json = carpeta / f"{registro['id_documento']}.json"
        assert ruta_json.is_file()


def test_los_identificadores_son_correlativos(lote):
    registros, _ = lote
    esperados = [construir_id_documento(i) for i in range(1, CANTIDAD + 1)]
    assert [registro["id_documento"] for registro in registros] == esperados


def test_el_manifiesto_tiene_una_linea_por_contrato(lote):
    registros, directorio = lote
    ruta = directorio / cfg.SUBDIRECTORIO_GROUND_TRUTH / cfg.NOMBRE_MANIFIESTO

    consolidado = leer_manifiesto(ruta)
    assert len(consolidado) == CANTIDAD
    assert consolidado == registros


def test_las_rutas_del_ground_truth_son_relativas(lote):
    registros, _ = lote
    for registro in registros:
        assert not registro["archivos"]["pdf"].startswith("/")
        assert ":" not in registro["archivos"]["pdf"]  # sin unidad de Windows
        assert "\\" not in registro["archivos"]["pdf"]


# =============================================================================
# CONTENIDO DEL GROUND TRUTH
# =============================================================================

def test_el_ground_truth_trae_todos_los_campos_sin_vacios(lote):
    registros, _ = lote
    for registro in registros:
        campos = registro["campos"]
        assert set(campos) == set(CAMPOS_CONTRATO)
        for nombre, valor in campos.items():
            assert valor not in ("", None), f"{registro['id_documento']}.{nombre}"


def test_los_campos_del_ground_truth_son_canonicos(lote):
    registros, _ = lote
    for registro in registros:
        campos = registro["campos"]

        assert patente_es_valida(campos["ppu"])
        assert rut_es_valido(campos["rut_empresa"])
        assert rut_es_valido(campos["rut_representante"])
        assert isinstance(campos["valor_cuota"], int)
        assert isinstance(campos["ano"], int)
        # Fechas en ISO: fromisoformat falla si el formato no es YYYY-MM-DD.
        date.fromisoformat(campos["fecha_inicio"])
        date.fromisoformat(campos["fecha_termino"])


def test_el_plazo_concuerda_con_las_fechas(lote):
    registros, _ = lote
    for registro in registros:
        campos = registro["campos"]
        inicio = date.fromisoformat(campos["fecha_inicio"])
        termino = date.fromisoformat(campos["fecha_termino"])

        assert termino > inicio
        assert meses_entre(inicio, termino) == campos["plazo_meses"]


def test_el_ground_truth_registra_plantilla_y_formatos(lote):
    registros, _ = lote
    for registro in registros:
        assert registro["plantilla"] in NOMBRES_PLANTILLAS
        assert registro["semilla"] == SEMILLA
        assert set(registro["formatos_usados"]) == {
            "fecha", "monto", "patente", "etiqueta_rut_persona",
        }


# =============================================================================
# CORRESPONDENCIA ENTRE EL PDF Y EL GROUND TRUTH
# =============================================================================

def _texto_del_pdf(ruta_pdf) -> str:
    documento = fitz.open(str(ruta_pdf))
    try:
        return "".join(pagina.get_text() for pagina in documento)
    finally:
        documento.close()


def test_el_pdf_contiene_los_valores_del_ground_truth(lote):
    """Comprueba los campos que se imprimen tal cual, sin variante de formato."""
    registros, directorio = lote
    literales = (
        "razon_social", "rut_empresa", "giro", "domicilio",
        "nombre_representante", "rut_representante",
        "marca", "modelo", "numero_pagare",
    )

    for registro in registros:
        # El texto embebido puede traer saltos de linea dentro de una frase.
        texto = " ".join(_texto_del_pdf(directorio / registro["archivos"]["pdf"]).split())
        for nombre in literales:
            assert registro["campos"][nombre] in texto, (
                f"{registro['id_documento']}: falta {nombre} en el PDF"
            )


def test_el_pdf_no_menciona_datos_del_contrato_de_otro_documento(lote):
    registros, directorio = lote
    for registro in registros:
        texto = _texto_del_pdf(directorio / registro["archivos"]["pdf"])
        ajenos = [otro for otro in registros if otro is not registro]
        for otro in ajenos:
            assert otro["campos"]["rut_empresa"] not in texto


# =============================================================================
# DETERMINISMO
# =============================================================================

def _json_del_lote(directorio):
    carpeta = directorio / cfg.SUBDIRECTORIO_GROUND_TRUTH
    return {
        ruta.name: ruta.read_bytes()
        for ruta in sorted(carpeta.glob("*.json"))
    }


def test_la_misma_semilla_reproduce_el_lote_byte_a_byte(tmp_path):
    primera = tmp_path / "corrida_a"
    segunda = tmp_path / "corrida_b"

    generar_lote(cantidad=3, semilla=77, directorio_salidas=primera, solo_pdf=True)
    generar_lote(cantidad=3, semilla=77, directorio_salidas=segunda, solo_pdf=True)

    assert _json_del_lote(primera) == _json_del_lote(segunda)


def test_semillas_distintas_producen_lotes_distintos(tmp_path):
    primera = tmp_path / "corrida_a"
    segunda = tmp_path / "corrida_b"

    generar_lote(cantidad=3, semilla=77, directorio_salidas=primera, solo_pdf=True)
    generar_lote(cantidad=3, semilla=78, directorio_salidas=segunda, solo_pdf=True)

    assert _json_del_lote(primera) != _json_del_lote(segunda)


# =============================================================================
# OPCIONES DEL LOTE
# =============================================================================

@pytest.mark.parametrize("nombre_plantilla", NOMBRES_PLANTILLAS)
def test_se_puede_forzar_una_sola_plantilla(tmp_path, nombre_plantilla):
    registros = generar_lote(
        cantidad=2,
        semilla=5,
        plantilla_forzada=nombre_plantilla,
        directorio_salidas=tmp_path,
        solo_pdf=True,
    )
    assert {registro["plantilla"] for registro in registros} == {nombre_plantilla}


def test_un_lote_grande_usa_las_tres_plantillas(tmp_path):
    registros = generar_lote(
        cantidad=30, semilla=3, directorio_salidas=tmp_path, solo_pdf=True,
    )
    assert {registro["plantilla"] for registro in registros} == set(NOMBRES_PLANTILLAS)


def test_solo_pdf_no_genera_escaneos(lote):
    registros, directorio = lote
    for registro in registros:
        assert registro["archivos"]["escaneos"] == []
        assert registro["perfil_escaneo"] == "ninguno"
    assert not (directorio / cfg.SUBDIRECTORIO_ESCANEOS).exists()


def test_cantidad_invalida_falla_temprano(tmp_path):
    with pytest.raises(ValueError):
        generar_lote(cantidad=0, directorio_salidas=tmp_path)


def test_plantilla_desconocida_falla_con_mensaje_claro(tmp_path):
    with pytest.raises(ValueError, match="Plantilla desconocida"):
        generar_lote(
            cantidad=1,
            plantilla_forzada="inexistente",
            directorio_salidas=tmp_path,
            solo_pdf=True,
        )


def test_el_json_individual_coincide_con_el_registro_devuelto(lote):
    registros, directorio = lote
    carpeta = directorio / cfg.SUBDIRECTORIO_GROUND_TRUTH

    for registro in registros:
        guardado = json.loads(
            (carpeta / f"{registro['id_documento']}.json").read_text(encoding="utf-8")
        )
        assert guardado == registro
