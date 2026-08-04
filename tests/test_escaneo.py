"""Pruebas del rasterizado y la degradacion que simulan un documento escaneado."""

from __future__ import annotations

from random import Random

import numpy as np
import pytest
from PIL import Image

import configuracion as cfg
from generador import escaneo
from generador.lote import generar_lote

# Dimensiones de una hoja A4 en pulgadas, para contrastar contra el DPI del perfil.
ANCHO_A4_PULGADAS = 8.27
ALTO_A4_PULGADAS = 11.69
TOLERANCIA_PIXELES = 3


@pytest.fixture
def pdf_de_prueba(tmp_path):
    """Genera un unico PDF nativo y devuelve su ruta."""
    registros = generar_lote(
        cantidad=1,
        semilla=101,
        plantilla_forzada="tabular",
        directorio_salidas=tmp_path,
        solo_pdf=True,
    )
    return tmp_path / registros[0]["archivos"]["pdf"]


# =============================================================================
# RASTERIZADO
# =============================================================================

def test_el_rasterizado_devuelve_una_imagen_por_pagina(pdf_de_prueba):
    paginas = escaneo.rasterizar_pdf(pdf_de_prueba, dpi=150)
    assert len(paginas) == 1
    assert paginas[0].mode == "L"


@pytest.mark.parametrize("nombre_perfil", tuple(cfg.PERFILES_ESCANEO))
def test_las_dimensiones_corresponden_al_dpi_del_perfil(pdf_de_prueba, nombre_perfil):
    dpi = cfg.PERFILES_ESCANEO[nombre_perfil]["dpi"]
    imagen = escaneo.rasterizar_pdf(pdf_de_prueba, dpi=dpi)[0]

    assert abs(imagen.width - round(ANCHO_A4_PULGADAS * dpi)) <= TOLERANCIA_PIXELES
    assert abs(imagen.height - round(ALTO_A4_PULGADAS * dpi)) <= TOLERANCIA_PIXELES


# =============================================================================
# DEGRADACION
# =============================================================================

def test_la_degradacion_conserva_modo_y_tamano(pdf_de_prueba):
    original = escaneo.rasterizar_pdf(pdf_de_prueba, dpi=150)[0]
    degradada = escaneo.degradar_imagen(
        original, cfg.PERFILES_ESCANEO["medio"], Random(1)
    )
    assert degradada.mode == "L"
    assert degradada.size == original.size


def test_la_degradacion_modifica_la_imagen(pdf_de_prueba):
    original = escaneo.rasterizar_pdf(pdf_de_prueba, dpi=150)[0]
    degradada = escaneo.degradar_imagen(
        original, cfg.PERFILES_ESCANEO["medio"], Random(1)
    )
    assert np.asarray(original).tobytes() != np.asarray(degradada).tobytes()


def test_el_perfil_degradado_ensucia_mas_que_el_limpio(pdf_de_prueba):
    """La desviacion respecto del original debe crecer con la agresividad del perfil."""
    original = np.asarray(escaneo.rasterizar_pdf(pdf_de_prueba, dpi=150)[0], dtype=np.float32)

    def desviacion(nombre_perfil: str) -> float:
        imagen = Image.fromarray(original.astype(np.uint8), mode="L")
        degradada = escaneo.degradar_imagen(
            imagen, cfg.PERFILES_ESCANEO[nombre_perfil], Random(3)
        )
        return float(np.abs(np.asarray(degradada, dtype=np.float32) - original).mean())

    assert desviacion("limpio") < desviacion("medio") < desviacion("degradado")


def test_la_misma_semilla_degrada_igual(pdf_de_prueba):
    original = escaneo.rasterizar_pdf(pdf_de_prueba, dpi=150)[0]
    parametros = cfg.PERFILES_ESCANEO["degradado"]

    primera = escaneo.degradar_imagen(original, parametros, Random(9))
    segunda = escaneo.degradar_imagen(original, parametros, Random(9))
    assert np.asarray(primera).tobytes() == np.asarray(segunda).tobytes()


# =============================================================================
# ESCANEO COMPLETO
# =============================================================================

def test_simular_escaneo_guarda_un_jpeg_por_pagina(pdf_de_prueba, tmp_path):
    destino = tmp_path / "escaneos_prueba"
    rutas = escaneo.simular_escaneo(
        pdf_de_prueba, destino, "medio", Random(2), "SINT-0001"
    )

    assert len(rutas) == 1
    assert rutas[0].name == f"SINT-0001_p01{cfg.EXTENSION_ESCANEO}"
    assert rutas[0].is_file()

    with Image.open(rutas[0]) as imagen:
        assert imagen.format == "JPEG"
        assert imagen.mode == "L"


def test_el_lote_completo_genera_escaneos(tmp_path):
    registros = generar_lote(
        cantidad=2, semilla=55, nombre_perfil="limpio", directorio_salidas=tmp_path,
    )
    for registro in registros:
        assert registro["perfil_escaneo"] == "limpio"
        assert len(registro["archivos"]["escaneos"]) == 1
        assert (tmp_path / registro["archivos"]["escaneos"][0]).is_file()


def test_el_perfil_mixto_reparte_entre_los_perfiles(tmp_path):
    registros = generar_lote(
        cantidad=30, semilla=6, nombre_perfil=cfg.PERFIL_MIXTO,
        directorio_salidas=tmp_path, solo_pdf=True,
    )
    # Con solo_pdf el perfil no se aplica, pero igual debe quedar resuelto a uno
    # de los nombres validos cuando se pide escaneo real.
    registros_con_escaneo = generar_lote(
        cantidad=30, semilla=6, nombre_perfil=cfg.PERFIL_MIXTO,
        directorio_salidas=tmp_path / "con_escaneo",
    )
    perfiles = {registro["perfil_escaneo"] for registro in registros_con_escaneo}
    assert perfiles.issubset(set(cfg.PERFILES_ESCANEO))
    assert len(perfiles) > 1
    assert all(registro["perfil_escaneo"] == "ninguno" for registro in registros)


@pytest.mark.parametrize("nombre_invalido", ["borroso", "", "MEDIO"])
def test_perfil_desconocido_falla_con_mensaje_claro(nombre_invalido):
    with pytest.raises(ValueError, match="Perfil de escaneo desconocido"):
        escaneo.obtener_perfil(nombre_invalido)
