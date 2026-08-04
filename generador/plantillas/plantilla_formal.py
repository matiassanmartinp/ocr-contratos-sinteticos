"""Plantilla 1: contrato en prosa corrida.

Los datos van embebidos dentro de parrafos, sin tabla ni etiquetas alineadas. Es
el layout mas dificil para una extraccion posicional: la misma informacion cae en
una coordenada distinta en cada documento segun el largo de los nombres y del
domicilio.

REDACCION
---------
La redaccion es propia y deliberadamente distinta de la que usan los contratos de
arriendo chilenos habituales. En particular se evitan la formula de apertura
"En <ciudad>, a <dia> de <mes> de <ano>, entre ...", los giros "en adelante" y
"se ha convenido", y la numeracion de clausulas en ordinales escritos. El unico
rasgo compartido con cualquier contrato es la fecha escrita en palabras, que es un
formato del idioma y no una frase de un documento concreto.
"""

from __future__ import annotations

from random import Random

from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

import configuracion as cfg
from esquema_contrato import ContratoSintetico
from generador import formatos

NOMBRE = "formal"

#: Variantes de formato que usa esta plantilla, registradas en el ground truth.
VARIANTES_FORMATO = {
    "fecha": "textual",
    "monto": "palabras",
    "patente": "punto_medio",
    "etiqueta_rut_persona": "cédula",
}

CONFIGURACION_PAGINA = {
    "pagesize": A4,
    "leftMargin": 3.0 * cm,
    "rightMargin": 3.0 * cm,
    "topMargin": 2.5 * cm,
    "bottomMargin": 2.5 * cm,
}

_TITULO = ParagraphStyle(
    "formal_titulo",
    fontName="Times-Bold",
    fontSize=13,
    leading=16,
    alignment=TA_CENTER,
    spaceAfter=16,
)

_CUERPO = ParagraphStyle(
    "formal_cuerpo",
    fontName="Times-Roman",
    fontSize=10.5,
    leading=15,
    alignment=TA_JUSTIFY,
    spaceAfter=10,
    firstLineIndent=1.0 * cm,
)

_CLAUSULA = ParagraphStyle(
    "formal_clausula",
    parent=_CUERPO,
    firstLineIndent=0,
    leftIndent=0.7 * cm,
)

_FIRMA = ParagraphStyle(
    "formal_firma",
    fontName="Times-Roman",
    fontSize=9.5,
    leading=13,
    alignment=TA_CENTER,
)

_ESTILO_FIRMAS = TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LINEABOVE", (0, 0), (0, 0), 0.6, "#000000"),
    ("LINEABOVE", (2, 0), (2, 0), 0.6, "#000000"),
    ("TOPPADDING", (0, 0), (-1, -1), 5),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 0),
])

#: Ancho de cada columna del bloque de firmas, con un canal libre al medio.
_ANCHO_COLUMNA_FIRMA = 6.5 * cm
_ANCHO_CANAL_FIRMA = 2.0 * cm


def _bloque_firmas(nombre_izquierda: str, empresa_izquierda: str,
                   nombre_derecha: str, empresa_derecha: str) -> Table:
    """Arma las dos lineas de firma lado a lado, separadas por un canal en blanco."""
    fila = [
        Paragraph(f"{nombre_izquierda}<br/>por {empresa_izquierda}", _FIRMA),
        Paragraph("", _FIRMA),
        Paragraph(f"{nombre_derecha}<br/>por {empresa_derecha}", _FIRMA),
    ]
    tabla = Table(
        [fila],
        colWidths=(_ANCHO_COLUMNA_FIRMA, _ANCHO_CANAL_FIRMA, _ANCHO_COLUMNA_FIRMA),
        hAlign="CENTER",
    )
    tabla.setStyle(_ESTILO_FIRMAS)
    return tabla


def construir(contrato: ContratoSintetico, aleatorio: Random) -> list:
    """Devuelve los elementos de reportlab que componen el contrato en prosa."""
    ciudad = aleatorio.choice(cfg.CIUDADES)
    fecha_inicio = formatos.fecha_textual(contrato.fecha_inicio)
    fecha_termino = formatos.fecha_textual(contrato.fecha_termino)
    patente = formatos.patente_punto_medio(contrato.ppu)
    monto = formatos.monto_en_palabras(contrato.valor_cuota)

    elementos: list = [
        Paragraph("CONTRATO DE ARRIENDO DE VEHÍCULO MOTORIZADO", _TITULO),
    ]

    elementos.append(Paragraph(
        f"Suscriben este documento dos partes. La primera es "
        f"<b>{cfg.ARRENDADOR_RAZON_SOCIAL}</b>, RUT {cfg.ARRENDADOR_RUT}, dedicada a "
        f"{cfg.ARRENDADOR_GIRO}, con oficinas en {cfg.ARRENDADOR_DOMICILIO}, que actúa "
        f"por medio de su representante {cfg.ARRENDADOR_REPRESENTANTE}, cédula "
        f"{cfg.ARRENDADOR_RUT_REPRESENTANTE}, a quien este texto llama LA PROPIETARIA.",
        _CUERPO,
    ))

    elementos.append(Paragraph(
        f"La segunda es <b>{contrato.razon_social}</b>, RUT {contrato.rut_empresa}, "
        f"dedicada a {contrato.giro}, con oficinas en {contrato.domicilio}, que actúa "
        f"por medio de su representante {contrato.nombre_representante}, cédula "
        f"{contrato.rut_representante}, a quien este texto llama LA USUARIA. Ambas "
        f"aceptan las reglas que siguen.",
        _CUERPO,
    ))

    elementos.append(Paragraph(
        f"<b>1. Qué se arrienda.</b> LA PROPIETARIA cede el uso de un vehículo "
        f"{contrato.marca}, modelo {contrato.modelo}, fabricado el año {contrato.ano} e "
        f"inscrito bajo la patente {patente}. El vehículo figura a nombre de LA "
        f"PROPIETARIA en el registro correspondiente y no pesa sobre él gravamen alguno.",
        _CLAUSULA,
    ))

    elementos.append(Paragraph(
        f"<b>2. Por cuánto tiempo.</b> El uso empieza el {fecha_inicio} y termina el "
        f"{fecha_termino}, lo que suma {contrato.plazo_meses} meses. Cualquier extensión "
        f"requiere un anexo firmado por ambas partes con treinta días de anticipación al "
        f"vencimiento.",
        _CLAUSULA,
    ))

    elementos.append(Paragraph(
        f"<b>3. Cuánto se paga.</b> LA USUARIA entrega a LA PROPIETARIA {monto} por cada "
        f"mes de uso. El pago se hace dentro de los primeros cinco días del mes que se "
        f"está pagando, por transferencia a la cuenta bancaria que LA PROPIETARIA "
        f"informe por escrito.",
        _CLAUSULA,
    ))

    elementos.append(Paragraph(
        f"<b>4. Qué respalda el pago.</b> LA USUARIA firma junto con este documento un "
        f"pagaré número {contrato.numero_pagare}. El documento se devuelve cuando "
        f"termina el uso y se revisa el estado del vehículo.",
        _CLAUSULA,
    ))

    elementos.append(Paragraph(
        "<b>5. Qué se puede y qué no.</b> LA USUARIA destina el vehículo únicamente al "
        "rubro que declaró, lo mantiene en buen estado y responde por multas y daños "
        "ocurridos mientras lo tiene. No puede prestarlo, traspasarlo ni volver a "
        "arrendarlo sin permiso escrito de LA PROPIETARIA.",
        _CLAUSULA,
    ))

    elementos.append(Paragraph(
        f"<b>6. Dónde se resuelve un desacuerdo.</b> Las partes registran domicilio en "
        f"{ciudad}. Cualquier discusión sobre este documento se resuelve ante los "
        f"tribunales de esa ciudad.",
        _CLAUSULA,
    ))

    elementos.append(Spacer(1, 2.2 * cm))
    elementos.append(_bloque_firmas(
        cfg.ARRENDADOR_REPRESENTANTE, cfg.ARRENDADOR_RAZON_SOCIAL,
        contrato.nombre_representante, contrato.razon_social,
    ))

    return elementos
