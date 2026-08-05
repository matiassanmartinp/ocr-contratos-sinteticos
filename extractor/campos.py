"""Reglas de extraccion de cada campo del contrato.

ESTRATEGIA
----------
Cada campo tiene una lista ordenada de patrones. Los primeros son de *etiqueta*
("Razon social", "R. SOCIAL:", "DOMICILIO:") y resuelven los layouts de ficha y
de formulario; los ultimos son de *estructura* ("dedicada a X, con oficinas en
Y") y resuelven el layout en prosa, donde no hay etiquetas.

De cada patron se recogen TODAS las coincidencias, no solo la primera, porque un
contrato individualiza a dos partes y ambas encajan en el mismo patron. La que se
descarta es la propia: los datos de la arrendadora estan en
``configuracion.VALORES_PROPIOS``. Conocer los datos propios y filtrarlos es
legitimo y es lo que hace cualquier extractor de produccion; es tambien el error
mas probable si no se hace.
"""

from __future__ import annotations

import re

import configuracion as cfg
from extractor import normalizacion as norma

# =============================================================================
# HELPERS
# =============================================================================

#: Un RUT dentro de un texto corrido. El separador de miles puede ser un punto o
#: un espacio: el OCR pierde los puntos con frecuencia y lee "99 000 001-8". Que
#: el patron sea generoso no genera falsos positivos, porque despues el digito
#: verificador descarta cualquier cosa que no sea un RUT de verdad.
_RUT_EN_TEXTO = re.compile(
    r"\b(\d{1,3}(?:[.\s]\d{3}){1,3}\s*[-—]\s*[\dkK]|\d{7,9}\s*[-—]\s*[\dkK])\b"
)

#: Cuantos caracteres antes del RUT se miran para saber de quien es.
_VENTANA_ETIQUETA_RUT = 60

#: Palabras que delatan que el RUT pertenece a una persona natural. Se comprueban
#: antes que las de empresa porque son mas especificas: en el layout compacto la
#: persona se rotula con un escueto "RUT:" y solo el contexto anterior distingue.
_INDICIOS_PERSONA = ("cedula", "c.i", "carnet", "rep. legal", "rep legal", "representante")
_INDICIOS_EMPRESA = ("rut emp", "rut empresa", "r.u.t", "rut")


def _comparable(valor: str) -> str:
    """Forma laxa para comparar dos textos: sin acentos, en minuscula, sin puntuacion."""
    return re.sub(r"[^a-z0-9]", "", norma.sin_acentos(valor or "").lower())


def _candidatos(texto: str, patrones: tuple[re.Pattern, ...]) -> list[str]:
    """Recoge las coincidencias de todos los patrones, en orden y sin repetir."""
    encontrados: list[str] = []
    for patron in patrones:
        for coincidencia in patron.finditer(texto):
            valor = coincidencia.group(1)
            if valor not in encontrados:
                encontrados.append(valor)
    return encontrados


def _elegir(candidatos: list[str], canonizador, valor_propio: str | None = None):
    """Devuelve el primer candidato canonizable que no sea el dato propio."""
    referencia = _comparable(valor_propio) if valor_propio else ""
    for bruto in candidatos:
        valor = canonizador(bruto)
        if valor in ("", None):
            continue
        if referencia and _comparable(str(valor)) == referencia:
            continue
        return valor
    # Cadena vacia para todos los campos, tambien los numericos: significa "no se
    # pudo leer", y la evaluacion lo cuenta como omision y no como error.
    return ""


def _extraer(texto, patrones, canonizador, campo_propio: str | None = None):
    """Aplica los patrones de un campo y elige el candidato que corresponde."""
    propio = cfg.VALORES_PROPIOS.get(campo_propio) if campo_propio else None
    return _elegir(_candidatos(texto, patrones), canonizador, propio)


# =============================================================================
# RUT DE LA EMPRESA Y DEL REPRESENTANTE
# =============================================================================

def clasificar_ruts(texto: str) -> tuple[list[str], list[str]]:
    """Separa los RUT del documento en los de empresa y los de persona natural.

    La distincion se hace por el texto que antecede a cada RUT, no por el tramo
    numerico: apoyarse en el rango seria un atajo que no se sostiene fuera de este
    dataset sintetico.
    """
    de_empresa: list[str] = []
    de_persona: list[str] = []

    for coincidencia in _RUT_EN_TEXTO.finditer(texto):
        inicio = max(0, coincidencia.start() - _VENTANA_ETIQUETA_RUT)
        contexto = norma.sin_acentos(texto[inicio:coincidencia.start()]).lower()
        bruto = coincidencia.group(1)

        if any(indicio in contexto for indicio in _INDICIOS_PERSONA):
            de_persona.append(bruto)
        elif any(indicio in contexto for indicio in _INDICIOS_EMPRESA):
            de_empresa.append(bruto)

    return de_empresa, de_persona


def _canonizador_de_rut(corregir_ocr: bool):
    """Devuelve el canonizador de RUT con o sin correccion de errores de lectura."""
    def canonizar(bruto: str) -> str:
        return norma.canonizar_rut_leido(bruto, corregir_ocr=corregir_ocr)
    return canonizar


def extraer_rut_empresa(texto: str, corregir_ocr: bool = False) -> str:
    """Devuelve el RUT de la empresa contraparte, descartando el propio."""
    de_empresa, _ = clasificar_ruts(texto)
    return _elegir(
        de_empresa, _canonizador_de_rut(corregir_ocr), cfg.VALORES_PROPIOS["rut_empresa"],
    )


def extraer_rut_representante(texto: str, corregir_ocr: bool = False) -> str:
    """Devuelve la cedula del representante de la contraparte, descartando la propia."""
    _, de_persona = clasificar_ruts(texto)
    return _elegir(
        de_persona, _canonizador_de_rut(corregir_ocr),
        cfg.VALORES_PROPIOS["rut_representante"],
    )


# =============================================================================
# PATRONES POR CAMPO
# =============================================================================

_RAZON_SOCIAL = (
    re.compile(r"R(?:az[oó]n)?\.?\s*social\s*:?\s+(.{3,90}?)\s+(?=RUT|R\.U\.T)", re.I),
    re.compile(r"\bes\s+([A-ZÁÉÍÓÚÑ][\w\.\s&·]{2,80}?)\s*,\s*RUT\s+\d", re.I),
)

_GIRO = (
    re.compile(r"\bgiro\s*:?\s+(.{3,90}?)\s+(?=domicilio\b|DOMICILIO)", re.I),
    re.compile(r"dedicad[ao]\s+a\s+(.{3,90}?)\s*,\s*con\s+oficinas", re.I),
)

_DOMICILIO = (
    re.compile(r"\bdomicilio\s*:?\s+(.{5,110}?)\s+(?=rep(?:resentante|\.)\s*legal)", re.I),
    re.compile(r"con\s+oficinas\s+en\s+(.{5,110}?)\s*,\s*que\s+act[uú]a", re.I),
)

_NOMBRE_REPRESENTANTE = (
    re.compile(r"rep(?:resentante|\.)\s*legal\s*:?\s+(.{5,70}?)"
               r"\s+(?=C\.I\.|RUT|CEDULA)", re.I),
    re.compile(r"su\s+representante\s+(.{5,70}?)\s*,\s*c[eé]dula", re.I),
)

_PATENTE = (
    re.compile(r"(?:placa\s+patente|patente|PPU)\s*(?:[uú]nica)?\s*:?\s*"
               r"([A-Z]{4}\s*[·\-\.]?\s*\d{2})\b", re.I),
)

# El valor de una etiqueta nunca cruza una coma: en el layout en prosa la frase
# sigue despues del dato ("modelo Kargo, fabricado el ano 2017") y sin esta
# restriccion el patron de etiqueta se comeria media oracion.
_MARCA = (
    re.compile(r"\bmarca\s*:?\s+([^,]{2,30}?)\s+(?=modelo\b|MODELO)", re.I),
    re.compile(r"veh[ií]culo\s+([A-ZÁÉÍÓÚÑ][\w\s\-]{1,28}?)\s*,\s*modelo", re.I),
)

_MODELO = (
    re.compile(r"\bmodelo\s*:?\s+([^,]{1,30}?)\s+(?=a[ñn]o\b|A[ÑN]O)", re.I),
    re.compile(r"\bmodelo\s+([\w\s\-]{1,28}?)\s*,\s*fabricado", re.I),
)

_ANO = (
    re.compile(r"a[ñn]o\s*:?\s*((?:19|20)\d{2})\b", re.I),
)

_FECHA_INICIO = (
    re.compile(r"(?:fecha\s+de\s+inicio|inicio|empieza\s+el|desde\s+el|a\s+contar\s+del)"
               r"\s*:?\s*([0-3]?\d\s*[/\-.]\s*[01]?\d\s*[/\-.]\s*(?:19|20)\d{2})", re.I),
    re.compile(r"(?:fecha\s+de\s+inicio|inicio|empieza\s+el|desde\s+el|a\s+contar\s+del)"
               r"\s*:?\s*([0-3]?\d\s+de\s+\w+\s+(?:del?\s+)?(?:19|20)\d{2})", re.I),
)

_FECHA_TERMINO = (
    re.compile(r"(?:fecha\s+de\s+t[eé]rmino|t[eé]rmino|termina\s+el|hasta\s+el|vence\s+el)"
               r"\s*:?\s*([0-3]?\d\s*[/\-.]\s*[01]?\d\s*[/\-.]\s*(?:19|20)\d{2})", re.I),
    re.compile(r"(?:fecha\s+de\s+t[eé]rmino|t[eé]rmino|termina\s+el|hasta\s+el|vence\s+el)"
               r"\s*:?\s*([0-3]?\d\s+de\s+\w+\s+(?:del?\s+)?(?:19|20)\d{2})", re.I),
)

_VALOR_CUOTA = (
    re.compile(r"(?:renta\s+mensual|valor\s+cuota|canon\s+mensual)\s*:?\s*(?:de\s+)?"
               r"(\$?\s*\d{1,3}(?:\.\d{3})+)", re.I),
    re.compile(r"pesos\s*\(\s*(\$?\s*\d{1,3}(?:\.\d{3})+)\s*\)", re.I),
)

# El simbolo de grado de "N°" es de lo que peor lee un OCR: sale como º, o, ?, ",
# o directamente se pierde. En vez de enumerar variantes, se admite cualquier
# relleno corto que no sea un digito entre la palabra y el numero.
_NUMERO_PAGARE = (
    re.compile(r"pagar[ée]\w*[^\d]{0,14}(\d{4,})", re.I),
)

_PLAZO_MESES = (
    re.compile(r"\b(\d{1,3})\s*meses\b", re.I),
)


# =============================================================================
# EXTRACCION COMPLETA
# =============================================================================

def extraer_campos(texto: str, corregir_ocr: bool = False) -> dict:
    """Extrae los quince campos del contrato desde el texto plano del documento.

    Devuelve un diccionario con las mismas claves de ``esquema_contrato``. Los
    campos que no se pudieron leer quedan como cadena vacia: es preferible un
    campo vacio, que se detecta a simple vista, a uno con un valor inventado.

    Con ``corregir_ocr`` activo se reparan en los RUT las confusiones tipicas de
    digitos, usando el digito verificador como confirmacion. Solo tiene sentido
    cuando el texto viene de un reconocimiento optico.
    """
    return {
        # -- Vehiculo --
        "ppu": _extraer(texto, _PATENTE, norma.canonizar_patente_leida),
        "marca": _extraer(texto, _MARCA, norma.canonizar_texto),
        "modelo": _extraer(texto, _MODELO, norma.canonizar_texto),
        "ano": _extraer(texto, _ANO, norma.canonizar_entero),

        # -- Arrendatario --
        "razon_social": _extraer(texto, _RAZON_SOCIAL, norma.canonizar_texto, "razon_social"),
        "rut_empresa": extraer_rut_empresa(texto, corregir_ocr),
        "giro": _extraer(texto, _GIRO, norma.canonizar_texto, "giro"),
        "domicilio": _extraer(texto, _DOMICILIO, norma.canonizar_texto, "domicilio"),

        # -- Representante legal --
        "nombre_representante": _extraer(
            texto, _NOMBRE_REPRESENTANTE, norma.canonizar_texto, "nombre_representante",
        ),
        "rut_representante": extraer_rut_representante(texto, corregir_ocr),

        # -- Condiciones economicas --
        "fecha_inicio": _extraer(texto, _FECHA_INICIO, norma.canonizar_fecha),
        "fecha_termino": _extraer(texto, _FECHA_TERMINO, norma.canonizar_fecha),
        "plazo_meses": _extraer(texto, _PLAZO_MESES, norma.canonizar_entero),
        "valor_cuota": _extraer(texto, _VALOR_CUOTA, norma.canonizar_monto),
        "numero_pagare": _extraer(texto, _NUMERO_PAGARE, norma.canonizar_texto),
    }
