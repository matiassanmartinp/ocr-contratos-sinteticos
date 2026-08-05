"""Plantilla 2: ficha tabular con clausulas breves.

Los datos se presentan en una tabla de dos columnas (etiqueta y valor) y las
condiciones legales quedan resumidas debajo. La informacion cae siempre en una
celda, pero la altura de cada fila varia con el largo del texto, de modo que las
coordenadas absolutas siguen sin ser estables.
"""

from __future__ import annotations

from random import Random

from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER, TA_JUSTIFY
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, Spacer, Table, TableStyle

import configuracion as cfg
from esquema_contrato import ContratoSintetico
from generador import formatos

NOMBRE = "tabular"

VARIANTES_FORMATO = {
    "fecha": "numerica_barra",
    "monto": "simbolo_peso",
    "patente": "guion",
    "etiqueta_rut_persona": "C.I. N°",
}

CONFIGURACION_PAGINA = {
    "pagesize": A4,
    "leftMargin": 2.2 * cm,
    "rightMargin": 2.2 * cm,
    "topMargin": 2.0 * cm,
    "bottomMargin": 2.0 * cm,
}

_TITULO = ParagraphStyle(
    "tabular_titulo",
    fontName="Helvetica-Bold",
    fontSize=14,
    leading=17,
    alignment=TA_CENTER,
    spaceAfter=4,
)

_SUBTITULO = ParagraphStyle(
    "tabular_subtitulo",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
    alignment=TA_CENTER,
    textColor=colors.HexColor("#444444"),
    spaceAfter=14,
)

_SECCION = ParagraphStyle(
    "tabular_seccion",
    fontName="Helvetica-Bold",
    fontSize=10,
    leading=13,
    spaceBefore=10,
    spaceAfter=6,
)

_CELDA = ParagraphStyle(
    "tabular_celda",
    fontName="Helvetica",
    fontSize=9,
    leading=12,
)

_CELDA_ETIQUETA = ParagraphStyle(
    "tabular_celda_etiqueta",
    parent=_CELDA,
    fontName="Helvetica-Bold",
)

_CUERPO = ParagraphStyle(
    "tabular_cuerpo",
    fontName="Helvetica",
    fontSize=9,
    leading=12.5,
    alignment=TA_JUSTIFY,
    spaceAfter=6,
)

_ESTILO_TABLA = TableStyle([
    ("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
    ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EFEFEF")),
    ("VALIGN", (0, 0), (-1, -1), "TOP"),
    ("LEFTPADDING", (0, 0), (-1, -1), 5),
    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
    ("TOPPADDING", (0, 0), (-1, -1), 4),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
])

_ANCHOS_COLUMNA = (5.2 * cm, 11.4 * cm)


def _tabla(filas: list[tuple[str, str]]) -> Table:
    """Arma una tabla de dos columnas a partir de pares etiqueta/valor."""
    contenido = [
        [Paragraph(etiqueta, _CELDA_ETIQUETA), Paragraph(valor, _CELDA)]
        for etiqueta, valor in filas
    ]
    tabla = Table(contenido, colWidths=_ANCHOS_COLUMNA, hAlign="LEFT")
    tabla.setStyle(_ESTILO_TABLA)
    return tabla


def construir(contrato: ContratoSintetico, aleatorio: Random) -> list:
    """Devuelve los elementos de reportlab que componen la ficha tabular."""
    ciudad = aleatorio.choice(cfg.CIUDADES)
    fecha_inicio = formatos.fecha_numerica(contrato.fecha_inicio, "/")
    fecha_termino = formatos.fecha_numerica(contrato.fecha_termino, "/")
    patente = formatos.patente_guion(contrato.ppu)
    monto = formatos.monto_con_simbolo(contrato.valor_cuota)

    elementos: list = [
        Paragraph("CONTRATO DE ARRENDAMIENTO DE VEHÍCULO", _TITULO),
        Paragraph(
            f"{cfg.ARRENDADOR_RAZON_SOCIAL} &nbsp;·&nbsp; RUT {cfg.ARRENDADOR_RUT} "
            f"&nbsp;·&nbsp; {ciudad}",
            _SUBTITULO,
        ),
        Paragraph("1. INDIVIDUALIZACIÓN DEL ARRENDATARIO", _SECCION),
        _tabla([
            ("Razón social", contrato.razon_social),
            ("RUT empresa", contrato.rut_empresa),
            ("Giro", contrato.giro),
            ("Domicilio", contrato.domicilio),
            ("Representante legal", contrato.nombre_representante),
            ("C.I. N°", contrato.rut_representante),
        ]),
        Paragraph("2. INDIVIDUALIZACIÓN DEL VEHÍCULO", _SECCION),
        _tabla([
            ("Placa patente", patente),
            ("Marca", contrato.marca),
            ("Modelo", contrato.modelo),
            ("Año", str(contrato.ano)),
        ]),
        Paragraph("3. CONDICIONES DEL ARRENDAMIENTO", _SECCION),
        _tabla([
            ("Fecha de inicio", fecha_inicio),
            ("Fecha de término", fecha_termino),
            ("Plazo", f"{contrato.plazo_meses} meses"),
            ("Renta mensual", monto),
            ("Pagaré N°", contrato.numero_pagare),
        ]),
        Paragraph("4. CLÁUSULAS GENERALES", _SECCION),
    ]

    elementos.append(Paragraph(
        f"El ARRENDATARIO individualizado en el punto 1 toma en arrendamiento el vehículo "
        f"del punto 2, de propiedad de {cfg.ARRENDADOR_RAZON_SOCIAL}, por el plazo y la "
        f"renta señalados en el punto 3. La renta se paga por mes anticipado dentro de los "
        f"primeros cinco días de cada mes.",
        _CUERPO,
    ))
    elementos.append(Paragraph(
        f"El cumplimiento de las obligaciones se garantiza con el pagaré "
        f"N° {contrato.numero_pagare}, suscrito por el ARRENDATARIO en este mismo acto.",
        _CUERPO,
    ))
    elementos.append(Paragraph(
        "El vehículo no podrá ser cedido ni subarrendado sin autorización escrita de la "
        "ARRENDADORA. Las partes fijan domicilio en la ciudad indicada en el encabezado.",
        _CUERPO,
    ))

    elementos.append(Spacer(1, 1.4 * cm))
    elementos.append(_tabla([
        ("Firma ARRENDADORA", f"{cfg.ARRENDADOR_REPRESENTANTE}<br/><br/>____________________"),
        ("Firma ARRENDATARIO",
         f"{contrato.nombre_representante}<br/><br/>____________________"),
    ]))

    return elementos
