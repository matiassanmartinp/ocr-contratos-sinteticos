"""Plantilla 3: formulario compacto a dos columnas con membrete lateral.

Tipografia menor, etiquetas abreviadas y datos repartidos en dos columnas
paralelas, de modo que un mismo campo puede aparecer a la izquierda o a la
derecha de la pagina. El membrete lateral se dibuja directamente sobre el canvas
y desplaza todo el contenido hacia la derecha.
"""

from __future__ import annotations

from random import Random

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

import configuracion as cfg
from esquema_contrato import ContratoSintetico
from generador import formatos

NOMBRE = "compacta"

VARIANTES_FORMATO = {
    "fecha": "numerica_guion",
    "monto": "sufijo_punto_guion",
    "patente": "sin_separador",
    "etiqueta_rut_persona": "RUT",
}

#: Ancho de la banda vertical del membrete.
ANCHO_MEMBRETE = 1.8 * cm

CONFIGURACION_PAGINA = {
    "pagesize": A4,
    "leftMargin": ANCHO_MEMBRETE + 1.0 * cm,
    "rightMargin": 1.4 * cm,
    "topMargin": 1.6 * cm,
    "bottomMargin": 1.6 * cm,
}

_TITULO = ParagraphStyle(
    "compacta_titulo",
    fontName="Helvetica-Bold",
    fontSize=11,
    leading=13,
    spaceAfter=2,
)

_REFERENCIA = ParagraphStyle(
    "compacta_referencia",
    fontName="Courier",
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#333333"),
    spaceAfter=10,
)

_SECCION = ParagraphStyle(
    "compacta_seccion",
    fontName="Helvetica-Bold",
    fontSize=8,
    leading=10,
    textColor=colors.HexColor("#111111"),
    spaceBefore=8,
    spaceAfter=3,
)

_DATO = ParagraphStyle(
    "compacta_dato",
    fontName="Helvetica",
    fontSize=7.6,
    leading=10,
)

_CUERPO = ParagraphStyle(
    "compacta_cuerpo",
    fontName="Helvetica",
    fontSize=7.4,
    leading=9.6,
    alignment=TA_JUSTIFY,
    spaceAfter=4,
)

_ESTILO_REJILLA = TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 10),
    ("TOPPADDING", (0, 0), (-1, -1), 1.5),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 1.5),
    ("LINEBELOW", (0, 0), (-1, -1), 0.25, colors.HexColor("#CCCCCC")),
])

_ANCHOS_REJILLA = (8.4 * cm, 8.4 * cm)


def _rejilla(pares: list[tuple[str, str]]) -> Table:
    """Distribuye pares etiqueta/valor en dos columnas, llenando de izquierda a derecha."""
    celdas = [
        Paragraph(f"<b>{etiqueta}</b> {valor}", _DATO)
        for etiqueta, valor in pares
    ]
    if len(celdas) % 2:
        celdas.append(Paragraph("", _DATO))

    filas = [celdas[i:i + 2] for i in range(0, len(celdas), 2)]
    tabla = Table(filas, colWidths=_ANCHOS_REJILLA, hAlign="LEFT")
    tabla.setStyle(_ESTILO_REJILLA)
    return tabla


_ESTILO_FIRMAS = TableStyle([
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 0),
    ("RIGHTPADDING", (0, 0), (-1, -1), 18),
    ("TOPPADDING", (0, 0), (-1, -1), 0),
])


def _bloque_firmas(nombre_arrendadora: str, nombre_arrendatario: str) -> Table:
    """Arma las dos firmas lado a lado, con el nombre bajo la linea de firma."""
    fila = [
        Paragraph(
            f"______________________________<br/>{nombre_arrendadora}<br/>"
            f"<b>P. ARRENDADORA</b>",
            _DATO,
        ),
        Paragraph(
            f"______________________________<br/>{nombre_arrendatario}<br/>"
            f"<b>P. ARRENDATARIO</b>",
            _DATO,
        ),
    ]
    tabla = Table([fila], colWidths=_ANCHOS_REJILLA, hAlign="LEFT")
    tabla.setStyle(_ESTILO_FIRMAS)
    return tabla


def dibujar_fondo(canvas, doc) -> None:
    """Dibuja la banda lateral con el nombre de la arrendadora en vertical."""
    canvas.saveState()
    alto_pagina = doc.pagesize[1]

    canvas.setFillColor(colors.HexColor("#E4E4E4"))
    canvas.rect(0, 0, ANCHO_MEMBRETE, alto_pagina, stroke=0, fill=1)

    canvas.setFillColor(colors.HexColor("#555555"))
    canvas.setFont("Helvetica-Bold", 9)
    canvas.translate(ANCHO_MEMBRETE / 2 + 3, 2.5 * cm)
    canvas.rotate(90)
    canvas.drawString(0, 0, cfg.ARRENDADOR_RAZON_SOCIAL.upper())
    canvas.restoreState()


def construir(contrato: ContratoSintetico, aleatorio: Random) -> list:
    """Devuelve los elementos de reportlab que componen el formulario compacto."""
    ciudad = aleatorio.choice(cfg.CIUDADES)
    fecha_inicio = formatos.fecha_numerica(contrato.fecha_inicio, "-")
    fecha_termino = formatos.fecha_numerica(contrato.fecha_termino, "-")
    patente = formatos.patente_sin_separador(contrato.ppu)
    monto = formatos.monto_con_sufijo(contrato.valor_cuota)

    elementos: list = [
        Paragraph("CONTRATO DE ARRENDAMIENTO DE VEHÍCULO MOTORIZADO", _TITULO),
        Paragraph(
            f"ARRENDADORA: {cfg.ARRENDADOR_RAZON_SOCIAL} | RUT {cfg.ARRENDADOR_RUT} | "
            f"LUGAR: {ciudad}",
            _REFERENCIA,
        ),
        Paragraph("DATOS DEL ARRENDATARIO", _SECCION),
        _rejilla([
            ("R. SOCIAL:", contrato.razon_social),
            ("RUT EMP.:", contrato.rut_empresa),
            ("GIRO:", contrato.giro),
            ("DOMICILIO:", contrato.domicilio),
            ("REP. LEGAL:", contrato.nombre_representante),
            ("RUT:", contrato.rut_representante),
        ]),
        Paragraph("DATOS DEL VEHÍCULO", _SECCION),
        _rejilla([
            ("PPU:", patente),
            ("MARCA:", contrato.marca),
            ("MODELO:", contrato.modelo),
            ("AÑO:", str(contrato.ano)),
        ]),
        Paragraph("CONDICIONES", _SECCION),
        _rejilla([
            ("INICIO:", fecha_inicio),
            ("TÉRMINO:", fecha_termino),
            ("PLAZO:", f"{contrato.plazo_meses} meses"),
            ("RENTA MENSUAL:", monto),
            ("PAGARÉ N°:", contrato.numero_pagare),
        ]),
        Paragraph("ESTIPULACIONES", _SECCION),
    ]

    elementos.append(Paragraph(
        f"El arrendatario individualizado precedentemente toma en arrendamiento el "
        f"vehículo {contrato.marca} {contrato.modelo} {contrato.ano}, PPU {patente}, "
        f"desde el {fecha_inicio} hasta el {fecha_termino}, por una renta mensual de "
        f"{monto} pagadera por mes anticipado. Se garantiza con pagaré "
        f"N° {contrato.numero_pagare}.",
        _CUERPO,
    ))
    elementos.append(Paragraph(
        "Prohibida la cesión y el subarriendo sin autorización escrita. El arrendatario "
        "responde de los daños, multas e infracciones cursadas durante la vigencia del "
        "contrato. Domicilio y jurisdicción: los indicados en el encabezado.",
        _CUERPO,
    ))

    elementos.append(Spacer(1, 1.4 * cm))
    elementos.append(_bloque_firmas(
        cfg.ARRENDADOR_REPRESENTANTE,
        contrato.nombre_representante,
    ))

    return elementos
