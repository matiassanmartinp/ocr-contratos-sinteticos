"""Pruebas del preproceso de imagen y de los motores de OCR.

Las que necesitan el binario de Tesseract se saltan solas si no esta instalado,
para que la bateria completa siga corriendo en una maquina sin OCR local. Las de
Document AI nunca contactan al servicio: solo comprueban que la falta de
credenciales se informe con un mensaje util en vez de reventar.
"""

from __future__ import annotations

import numpy as np
import pytest
from PIL import Image

import configuracion as cfg
from esquema_contrato import CAMPOS_CONTRATO
from extractor import ocr, preproceso
from extractor.pipeline import extraer_de_directorio, obtener_texto
from generador.lote import generar_lote

necesita_tesseract = pytest.mark.skipif(
    not ocr.tesseract_esta_disponible(),
    reason="Tesseract no esta instalado en esta maquina",
)


def _pagina_de_prueba(inclinacion: float = 0.0, vineteado: float = 0.0,
                      motas: float = 0.0, semilla: int = 0) -> Image.Image:
    """Fabrica una pagina blanca con renglones negros y la degrada a pedido."""
    generador = np.random.default_rng(semilla)
    arreglo = np.full((600, 480), 255, dtype=np.float32)
    for fila in range(60, 540, 40):
        arreglo[fila:fila + 12, 60:420] = 0.0  # renglon de "texto"

    if vineteado > 0:
        vertical = np.linspace(-1.0, 1.0, arreglo.shape[0])[:, None]
        horizontal = np.linspace(-1.0, 1.0, arreglo.shape[1])[None, :]
        radio = np.sqrt(horizontal ** 2 + vertical ** 2) / np.sqrt(2.0)
        arreglo = arreglo * (1.0 - vineteado * radio ** 2)

    if motas > 0:
        sorteo = generador.random(arreglo.shape)
        arreglo = np.where(sorteo < motas / 2, 0.0, arreglo)
        arreglo = np.where(sorteo > 1 - motas / 2, 255.0, arreglo)

    imagen = Image.fromarray(np.clip(arreglo, 0, 255).astype(np.uint8), mode="L")
    if inclinacion:
        imagen = imagen.rotate(-inclinacion, resample=Image.BICUBIC, fillcolor=255)
    return imagen


# =============================================================================
# ENDEREZADO
# =============================================================================

@pytest.mark.parametrize("inclinacion", [-2.0, -1.0, 1.0, 2.0])
def test_se_estima_la_inclinacion_de_la_pagina(inclinacion):
    """El perfil de proyeccion debe recuperar el angulo con que se torcio la hoja."""
    pagina = _pagina_de_prueba(inclinacion=inclinacion)
    estimada = preproceso.estimar_inclinacion(pagina)
    assert abs(estimada - inclinacion) <= 0.35, f"estimo {estimada} para {inclinacion}"


def test_una_pagina_derecha_no_se_gira():
    assert abs(preproceso.estimar_inclinacion(_pagina_de_prueba())) <= 0.25


def test_enderezar_devuelve_el_angulo_que_aplico():
    pagina = _pagina_de_prueba(inclinacion=1.5)
    _, angulo = preproceso.enderezar(pagina)
    assert abs(angulo - 1.5) <= 0.35


# =============================================================================
# ILUMINACION Y RUIDO
# =============================================================================

def test_la_correccion_de_iluminacion_empareja_el_papel():
    """Con la tapa mal cerrada los bordes quedan oscuros y un umbral global falla."""
    pagina = _pagina_de_prueba(vineteado=0.45)
    corregida = preproceso.corregir_iluminacion(pagina)

    def brillo_de_esquina(imagen):
        arreglo = np.asarray(imagen, dtype=np.float32)
        return float(arreglo[:40, :40].mean())

    def brillo_de_centro(imagen):
        arreglo = np.asarray(imagen, dtype=np.float32)
        alto = arreglo.shape[0]
        return float(arreglo[alto // 2 - 20:alto // 2 + 20, 20:60].mean())

    desnivel_antes = abs(brillo_de_centro(pagina) - brillo_de_esquina(pagina))
    desnivel_despues = abs(brillo_de_centro(corregida) - brillo_de_esquina(corregida))
    assert desnivel_despues < desnivel_antes / 2


def test_el_filtro_de_mediana_se_aplica_cuando_hay_motas():
    sucia = _pagina_de_prueba(motas=0.05, semilla=1)
    limpia = preproceso.quitar_motas(sucia)
    assert np.asarray(limpia).tobytes() != np.asarray(sucia).tobytes()


def test_el_filtro_de_mediana_se_omite_en_una_pagina_limpia():
    """Sobre un escaneo sin ruido el filtro adelgaza los trazos y perjudica."""
    limpia = _pagina_de_prueba()
    resultado = preproceso.quitar_motas(limpia)
    assert np.asarray(resultado).tobytes() == np.asarray(limpia).tobytes()


def test_medir_motas_crece_con_el_ruido():
    poco = _pagina_de_prueba(motas=0.01, semilla=2)
    mucho = _pagina_de_prueba(motas=0.10, semilla=2)
    parametros = cfg.PREPROCESO_OCR

    def medir(imagen):
        from PIL import ImageFilter
        filtrada = imagen.filter(ImageFilter.MedianFilter(size=3))
        return preproceso.medir_motas(imagen, filtrada, parametros)

    assert medir(poco) < medir(mucho)


# =============================================================================
# BINARIZACION
# =============================================================================

def test_otsu_separa_los_dos_tonos_de_la_pagina():
    """Lo que importa es que la particion sea la correcta, no el valor del umbral.

    Con una imagen de solo dos tonos, cualquier corte entre ambos produce la misma
    separacion y todos son igual de validos.
    """
    arreglo = np.concatenate([
        np.full(5_000, 30, dtype=np.uint8), np.full(5_000, 220, dtype=np.uint8),
    ])
    umbral = preproceso.umbral_de_otsu(arreglo)
    assert 30 <= umbral < 220, umbral

    # Con el convenio de binarizar (mayor que el umbral es papel), la tinta queda
    # de un lado y el papel del otro.
    assert not (umbral < 30)
    assert umbral < 220


def test_otsu_se_adapta_a_una_pagina_oscura_y_a_una_clara():
    """Un escaneo subexpuesto y uno sobreexpuesto necesitan umbrales distintos."""
    oscura = np.concatenate([
        np.full(5_000, 10, dtype=np.uint8), np.full(5_000, 90, dtype=np.uint8),
    ])
    clara = np.concatenate([
        np.full(5_000, 150, dtype=np.uint8), np.full(5_000, 245, dtype=np.uint8),
    ])
    assert preproceso.umbral_de_otsu(oscura) < preproceso.umbral_de_otsu(clara)


def test_binarizar_deja_solo_blanco_y_negro():
    binaria = np.asarray(preproceso.binarizar(_pagina_de_prueba(vineteado=0.2)))
    assert set(np.unique(binaria)).issubset({0, 255})


def test_preparar_no_altera_el_tipo_de_imagen():
    preparada = preproceso.preparar(_pagina_de_prueba(inclinacion=1.0, motas=0.03))
    assert preparada.mode == "L"


# =============================================================================
# TESSERACT
# =============================================================================

@necesita_tesseract
def test_tesseract_lee_un_contrato_escaneado(tmp_path):
    registros = generar_lote(
        cantidad=1, semilla=404, nombre_perfil="limpio", directorio_salidas=tmp_path,
    )
    ruta_escaneo = tmp_path / registros[0]["archivos"]["escaneos"][0]

    texto = ocr.leer_con_tesseract(ruta_escaneo)
    assert len(texto) > cfg.MINIMO_CARACTERES_TEXTO_NATIVO
    assert "CONTRATO" in texto.upper()


@necesita_tesseract
def test_el_pipeline_extrae_desde_imagenes_y_no_solo_desde_pdf(tmp_path):
    """Los escaneos son JPG: el extractor debe aceptarlos igual que un PDF."""
    generar_lote(
        cantidad=1, semilla=405, nombre_perfil="limpio", directorio_salidas=tmp_path,
    )
    registros = extraer_de_directorio(
        tmp_path / cfg.SUBDIRECTORIO_ESCANEOS, motor=cfg.MOTOR_TESSERACT,
    )
    assert len(registros) == 1
    assert registros[0]["metodo"] == cfg.MOTOR_TESSERACT
    assert set(registros[0]["campos"]) == set(CAMPOS_CONTRATO)


@necesita_tesseract
def test_el_identificador_ignora_el_sufijo_de_pagina(tmp_path):
    """SINT-0001_p01.jpg debe evaluarse contra el ground truth de SINT-0001."""
    generar_lote(
        cantidad=1, semilla=406, nombre_perfil="limpio", directorio_salidas=tmp_path,
    )
    registros = extraer_de_directorio(
        tmp_path / cfg.SUBDIRECTORIO_ESCANEOS, motor=cfg.MOTOR_TESSERACT,
    )
    assert registros[0]["id_documento"] == "SINT-0001"


# =============================================================================
# DESPACHO ENTRE MOTORES
# =============================================================================

def test_el_motor_auto_prefiere_el_texto_embebido(tmp_path):
    """Reconocer por OCR lo que ya venia escrito seria perder precision y tiempo."""
    registros = generar_lote(
        cantidad=1, semilla=407, directorio_salidas=tmp_path, solo_pdf=True,
    )
    ruta_pdf = tmp_path / registros[0]["archivos"]["pdf"]
    _, motor_usado = obtener_texto(ruta_pdf, cfg.MOTOR_AUTO)
    assert motor_usado == cfg.MOTOR_NATIVO


def test_pedir_texto_nativo_de_una_imagen_falla_con_un_mensaje_claro(tmp_path):
    ruta = tmp_path / "escaneo.jpg"
    _pagina_de_prueba().save(ruta)
    with pytest.raises(ValueError, match="no tiene texto embebido"):
        obtener_texto(ruta, cfg.MOTOR_NATIVO)


def test_se_reconocen_las_extensiones_de_imagen():
    from pathlib import Path
    assert ocr.es_imagen(Path("x.jpg"))
    assert ocr.es_imagen(Path("x.PNG"))
    assert not ocr.es_imagen(Path("x.pdf"))


def test_un_motor_inexistente_falla_con_un_mensaje_claro(tmp_path):
    with pytest.raises(ValueError, match="Motor de OCR desconocido"):
        ocr.leer(tmp_path / "cualquiera.pdf", "inventado")


# =============================================================================
# DOCUMENT AI: SOLO LA CONFIGURACION, NUNCA EL SERVICIO
# =============================================================================

def test_sin_credenciales_document_ai_se_declara_no_configurado(monkeypatch):
    monkeypatch.setattr(cfg, "DOCAI_PROCESADOR", "")
    monkeypatch.setattr(cfg, "DOCAI_CREDENCIALES", "")
    assert not ocr.documentai_esta_configurado()


def test_con_ambas_variables_document_ai_se_declara_configurado(monkeypatch):
    monkeypatch.setattr(cfg, "DOCAI_PROCESADOR", "projects/x/locations/us/processors/y")
    monkeypatch.setattr(cfg, "DOCAI_CREDENCIALES", "/ruta/a/credenciales.json")
    assert ocr.documentai_esta_configurado()


def test_el_repositorio_no_trae_credenciales_escritas():
    """La configuracion de Document AI debe venir del entorno y de ningun otro lado."""
    import inspect

    fuente = inspect.getsource(cfg)
    assert 'os.environ.get("GOOGLE_DOCAI_PROCESSOR"' in fuente
    assert 'os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"' in fuente
    # Sin credenciales en el entorno, el valor por defecto es vacio y no un
    # identificador real olvidado en el codigo.
    import os
    if not os.environ.get("GOOGLE_DOCAI_PROCESSOR"):
        assert cfg.DOCAI_PROCESADOR == ""
