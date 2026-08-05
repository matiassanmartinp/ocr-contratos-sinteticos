"""Lectura por OCR, con dos motores tras una misma interfaz.

``tesseract``
    Local, gratuito y sin credenciales. Es el motor por defecto: permite que
    cualquiera clone el repositorio, ejecute el pipeline completo y reproduzca
    las cifras publicadas sin abrir una cuenta en ningun proveedor.

``documentai``
    Google Cloud Document AI, que es el motor que corre en el proceso real.
    Requiere credenciales, que se leen exclusivamente del entorno: este
    repositorio no contiene ni debe contener ninguna clave. Ver ``.env.example``.

Ambos devuelven texto plano, de modo que ``campos.py`` no se entera de cual se
uso. Esa indiferencia es lo que permite comparar los dos motores sobre el mismo
conjunto de documentos y decidir con datos si el de pago se justifica.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image

import configuracion as cfg
from extractor import preproceso
from extractor.texto import normalizar_espacios
from rasterizado import rasterizar_pdf

EXTENSIONES_IMAGEN = (".jpg", ".jpeg", ".png", ".tif", ".tiff", ".bmp")

_TIPOS_MIME = {
    ".pdf": "application/pdf",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".png": "image/png",
    ".tif": "image/tiff",
    ".tiff": "image/tiff",
    ".bmp": "image/bmp",
}


class MotorNoDisponible(RuntimeError):
    """El motor pedido no se puede usar en este entorno.

    Se distingue a proposito de un fallo de lectura: que falte una dependencia o
    una credencial no es un error del documento, y el mensaje debe decir que hay
    que instalar o configurar.
    """


def es_imagen(ruta: Path) -> bool:
    """Indica si la ruta apunta a una imagen y no a un PDF."""
    return Path(ruta).suffix.lower() in EXTENSIONES_IMAGEN


def cargar_paginas(ruta: Path, dpi: int | None = None) -> list[Image.Image]:
    """Devuelve las paginas del documento como imagenes, venga PDF o imagen suelta."""
    ruta = Path(ruta)
    if es_imagen(ruta):
        with Image.open(ruta) as imagen:
            return [imagen.convert("L")]
    return rasterizar_pdf(ruta, dpi or cfg.TESSERACT_DPI_RASTERIZADO)


# =============================================================================
# TESSERACT
# =============================================================================

def _importar_pytesseract():
    """Importa pytesseract y configura el binario, o explica que falta."""
    try:
        import pytesseract
    except ImportError as error:  # pragma: no cover - depende del entorno
        raise MotorNoDisponible(
            "Falta el paquete pytesseract. Instalar con: pip install pytesseract"
        ) from error

    if cfg.TESSERACT_EJECUTABLE:
        pytesseract.pytesseract.tesseract_cmd = cfg.TESSERACT_EJECUTABLE
    return pytesseract


def tesseract_esta_disponible() -> bool:
    """Indica si el motor local se puede usar, sin lanzar excepcion."""
    try:
        _importar_pytesseract().get_tesseract_version()
        return True
    except Exception:
        return False


def leer_con_tesseract(ruta: Path, aplicar_preproceso: bool = True) -> str:
    """Reconoce el texto de un documento con Tesseract en espanol.

    Cada pagina se prepara antes de reconocerla: enderezada, ampliada si venia en
    baja resolucion y binarizada. Ese paso previo pesa mas en el resultado que
    cualquier ajuste de los parametros del motor.
    """
    pytesseract = _importar_pytesseract()

    try:
        pytesseract.get_tesseract_version()
    except Exception as error:
        raise MotorNoDisponible(
            "No se encontro el binario de Tesseract. Instalarlo (ver README) o "
            "indicar su ruta en la variable de entorno TESSERACT_EXE."
        ) from error

    reconocidas: list[str] = []
    for pagina in cargar_paginas(ruta):
        preparada = preproceso.preparar(pagina) if aplicar_preproceso else pagina
        reconocidas.append(pytesseract.image_to_string(
            preparada, lang=cfg.TESSERACT_IDIOMA, config=cfg.TESSERACT_CONFIG,
        ))

    return normalizar_espacios(" ".join(reconocidas))


# =============================================================================
# GOOGLE DOCUMENT AI
# =============================================================================

_CLIENTE_DOCAI = None


def documentai_esta_configurado() -> bool:
    """Indica si hay credenciales y procesador definidos en el entorno."""
    return bool(cfg.DOCAI_PROCESADOR) and bool(cfg.DOCAI_CREDENCIALES)


def _obtener_cliente_docai():
    """Crea el cliente de Document AI una sola vez y lo reutiliza.

    Las credenciales las resuelve la propia biblioteca de Google a partir de
    ``GOOGLE_APPLICATION_CREDENTIALS``; aqui no se leen ni se manipulan claves.
    """
    global _CLIENTE_DOCAI
    if _CLIENTE_DOCAI is not None:
        return _CLIENTE_DOCAI

    try:
        from google.api_core.client_options import ClientOptions
        from google.cloud import documentai
    except ImportError as error:
        raise MotorNoDisponible(
            "Falta la biblioteca de Google Cloud. Instalar con: "
            "pip install -r requirements-opcional.txt"
        ) from error

    if not cfg.DOCAI_PROCESADOR:
        raise MotorNoDisponible(
            "Falta la variable de entorno GOOGLE_DOCAI_PROCESSOR con el nombre de "
            "recurso del procesador. Ver .env.example."
        )
    if not cfg.DOCAI_CREDENCIALES:
        raise MotorNoDisponible(
            "Falta la variable de entorno GOOGLE_APPLICATION_CREDENTIALS con la "
            "ruta al JSON de la cuenta de servicio. Ver .env.example."
        )

    opciones = ClientOptions(
        api_endpoint=f"{cfg.DOCAI_UBICACION}-documentai.googleapis.com"
    )
    _CLIENTE_DOCAI = documentai.DocumentProcessorServiceClient(client_options=opciones)
    return _CLIENTE_DOCAI


def leer_con_document_ai(ruta: Path) -> str:
    """Reconoce el texto de un documento con Google Cloud Document AI.

    El documento se envia tal cual, sin preproceso local: el servicio hace su
    propio enderezado y realce, y adelantarse suele empeorar el resultado.
    """
    from google.cloud import documentai  # importado ya validado por el cliente

    cliente = _obtener_cliente_docai()
    ruta = Path(ruta)
    tipo_mime = _TIPOS_MIME.get(ruta.suffix.lower())
    if tipo_mime is None:
        raise ValueError(f"Tipo de archivo no admitido por Document AI: {ruta.suffix}")

    solicitud = documentai.ProcessRequest(
        name=cfg.DOCAI_PROCESADOR,
        raw_document=documentai.RawDocument(
            content=ruta.read_bytes(), mime_type=tipo_mime,
        ),
        process_options=documentai.ProcessOptions(
            ocr_config=documentai.OcrConfig(
                enable_native_pdf_parsing=cfg.DOCAI_PARSEO_NATIVO_PDF,
            ),
        ),
    )

    respuesta = cliente.process_document(
        request=solicitud, timeout=cfg.DOCAI_TIMEOUT_SEGUNDOS,
    )
    return normalizar_espacios(respuesta.document.text)


# =============================================================================
# DESPACHO
# =============================================================================

def leer(ruta: Path, motor: str) -> str:
    """Reconoce el texto del documento con el motor indicado."""
    if motor == cfg.MOTOR_TESSERACT:
        return leer_con_tesseract(ruta)
    if motor == cfg.MOTOR_DOCUMENTAI:
        return leer_con_document_ai(ruta)
    raise ValueError(f"Motor de OCR desconocido: {motor!r}")
