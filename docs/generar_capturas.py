"""Regenera las imagenes que ilustran el README.

Las capturas son las unicas imagenes versionadas del repositorio. Se generan con
el propio proyecto y son 100% sinteticas, como todo lo demas. Este script existe
para que no queden huerfanas: si cambia una plantilla o un perfil de escaneo,
basta volver a ejecutarlo.

    python docs/generar_capturas.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from random import Random

from PIL import Image, ImageDraw, ImageFont

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))

from extractor import preproceso
from generador.datos_chilenos import generar_contrato
from generador.escaneo import simular_escaneo
from generador.render_pdf import renderizar_contrato
from rasterizado import rasterizar_pdf

DIRECTORIO_DOCS = RAIZ / "docs"
SEMILLA = 20260804

# Composicion de la tira de plantillas.
ANCHO_PAGINA = 620
MARGEN = 18
ALTO_ROTULO = 46
COLOR_FONDO = (245, 245, 247)
COLOR_TEXTO = (28, 28, 30)
COLOR_BORDE = (200, 200, 205)


def _tipografia(tamano: int) -> ImageFont.ImageFont:
    """Busca una tipografia del sistema y cae a la de PIL si no encuentra ninguna."""
    for nombre in ("DejaVuSans-Bold.ttf", "arialbd.ttf", "Arial Bold.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(nombre, tamano)
        except OSError:
            continue
    return ImageFont.load_default()


def _pagina_de(contrato, plantilla: str, temporal: Path, dpi: int = 150) -> Image.Image:
    """Renderiza un contrato con una plantilla y devuelve su primera pagina."""
    ruta_pdf = temporal / f"{plantilla}.pdf"
    renderizar_contrato(contrato, ruta_pdf, plantilla, Random(SEMILLA))
    return rasterizar_pdf(ruta_pdf, dpi=dpi)[0]


def componer_plantillas(contrato, temporal: Path) -> Path:
    """Arma la tira con los tres layouts lado a lado, cada uno rotulado."""
    paginas = []
    for plantilla in ("formal", "tabular", "compacta"):
        pagina = _pagina_de(contrato, plantilla, temporal)
        proporcion = ANCHO_PAGINA / pagina.width
        paginas.append((
            plantilla,
            pagina.convert("RGB").resize(
                (ANCHO_PAGINA, int(pagina.height * proporcion)), Image.LANCZOS,
            ),
        ))

    alto_pagina = max(imagen.height for _, imagen in paginas)
    ancho_total = MARGEN + len(paginas) * (ANCHO_PAGINA + MARGEN)
    alto_total = ALTO_ROTULO + alto_pagina + MARGEN

    lienzo = Image.new("RGB", (ancho_total, alto_total), COLOR_FONDO)
    dibujo = ImageDraw.Draw(lienzo)
    fuente = _tipografia(26)

    for indice, (nombre, imagen) in enumerate(paginas):
        x = MARGEN + indice * (ANCHO_PAGINA + MARGEN)
        dibujo.text((x + 2, 10), nombre, fill=COLOR_TEXTO, font=fuente)
        lienzo.paste(imagen, (x, ALTO_ROTULO))
        dibujo.rectangle(
            [x, ALTO_ROTULO, x + ANCHO_PAGINA - 1, ALTO_ROTULO + imagen.height - 1],
            outline=COLOR_BORDE,
        )

    destino = DIRECTORIO_DOCS / "plantillas.png"
    lienzo.save(destino, optimize=True)
    return destino


def componer_preproceso(contrato, temporal: Path) -> Path:
    """Arma la comparacion antes y despues del preproceso, sobre un escaneo degradado.

    Es la imagen que explica de un vistazo por que el preproceso pesa mas que
    cualquier ajuste del motor de OCR.
    """
    ruta_pdf = temporal / "para_escanear.pdf"
    renderizar_contrato(contrato, ruta_pdf, "formal", Random(SEMILLA))
    rutas = simular_escaneo(
        ruta_pdf, temporal, "degradado", Random(SEMILLA), "muestra",
    )

    with Image.open(rutas[0]) as escaneo:
        original = escaneo.convert("L")
    procesada = preproceso.preparar(original)

    # Se recorta la misma franja de texto en ambas, para poder compararlas.
    def recortar(imagen: Image.Image) -> Image.Image:
        ancho, alto = imagen.size
        caja = (int(ancho * 0.08), int(alto * 0.13), int(ancho * 0.95), int(alto * 0.33))
        recorte = imagen.crop(caja)
        proporcion = 780 / recorte.width
        return recorte.convert("RGB").resize(
            (780, int(recorte.height * proporcion)), Image.LANCZOS,
        )

    izquierda, derecha = recortar(original), recortar(procesada)
    alto = max(izquierda.height, derecha.height)

    lienzo = Image.new(
        "RGB", (MARGEN * 3 + izquierda.width * 2, ALTO_ROTULO + alto + MARGEN), COLOR_FONDO,
    )
    dibujo = ImageDraw.Draw(lienzo)
    fuente = _tipografia(24)

    for indice, (rotulo, imagen) in enumerate(
        (("escaneo degradado", izquierda), ("tras el preproceso", derecha))
    ):
        x = MARGEN + indice * (izquierda.width + MARGEN)
        dibujo.text((x + 2, 10), rotulo, fill=COLOR_TEXTO, font=fuente)
        lienzo.paste(imagen, (x, ALTO_ROTULO))
        dibujo.rectangle(
            [x, ALTO_ROTULO, x + imagen.width - 1, ALTO_ROTULO + imagen.height - 1],
            outline=COLOR_BORDE,
        )

    destino = DIRECTORIO_DOCS / "preproceso.png"
    lienzo.save(destino, optimize=True)
    return destino


def main() -> int:
    """Genera todas las capturas del README."""
    DIRECTORIO_DOCS.mkdir(parents=True, exist_ok=True)
    temporal = DIRECTORIO_DOCS / "_temporal"
    temporal.mkdir(exist_ok=True)

    contrato = generar_contrato(Random(SEMILLA))
    generadas = [
        componer_plantillas(contrato, temporal),
        componer_preproceso(contrato, temporal),
    ]

    for archivo in temporal.iterdir():
        archivo.unlink()
    temporal.rmdir()

    for ruta in generadas:
        print(f"{ruta.relative_to(RAIZ).as_posix()}  "
              f"({ruta.stat().st_size / 1024:.0f} KB)")
    print(f"\nDatos del contrato de las capturas: {contrato.ppu}, "
          f"{contrato.razon_social} — sinteticos, semilla {SEMILLA}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
