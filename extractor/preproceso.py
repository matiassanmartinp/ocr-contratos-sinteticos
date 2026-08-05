"""Preparacion de una imagen escaneada antes de pasarla por OCR.

Enderezar y binarizar antes de reconocer rinde mas que cualquier ajuste de
parametros del motor: un motor de OCR asume renglones horizontales y tinta negra
sobre papel blanco, y un escaneo real no le entrega ninguna de las dos cosas.

Solo usa Pillow y numpy, sin OpenCV: la dependencia pesada no se justifica para
las tres operaciones que hacen falta.
"""

from __future__ import annotations

import numpy as np
from PIL import Image, ImageFilter

import configuracion as cfg


def corregir_iluminacion(imagen: Image.Image, parametros: dict | None = None) -> Image.Image:
    """Aplana la iluminacion dividiendo la pagina por su propio fondo.

    Un escaneo real no tiene el papel igual de blanco en todas partes: la tapa mal
    cerrada oscurece los bordes. Un umbral global sobre esa imagen deja las
    esquinas completamente negras, y el motor de OCR ve una pagina cubierta de
    manchas en vez de texto.

    El fondo se estima difuminando muchisimo la imagen, de modo que el texto
    desaparezca y quede solo la iluminacion; dividir por el devuelve un papel
    parejo. El difuminado se calcula sobre una copia diminuta porque la
    iluminacion es de frecuencia muy baja y no necesita resolucion.
    """
    parametros = parametros or cfg.PREPROCESO_OCR

    ancho_fondo = parametros["ancho_estimacion_fondo"]
    proporcion = ancho_fondo / imagen.width
    reducida = imagen.resize(
        (ancho_fondo, max(1, int(imagen.height * proporcion))), Image.BILINEAR,
    )
    difuminada = reducida.filter(
        ImageFilter.GaussianBlur(radius=parametros["radio_difuminado_fondo"])
    )
    fondo = difuminada.resize(imagen.size, Image.BILINEAR)

    original = np.asarray(imagen, dtype=np.float32)
    estimado = np.maximum(np.asarray(fondo, dtype=np.float32), 1.0)
    aplanada = np.clip(original / estimado * 255.0, 0, 255)

    return Image.fromarray(aplanada.astype(np.uint8), mode="L")


def medir_motas(original: Image.Image, filtrada: Image.Image, parametros: dict) -> float:
    """Estima que proporcion de la pagina es ruido de sal y pimienta.

    Un pixel que cambia mucho al reemplazarlo por la mediana de su vecindad era un
    pixel aislado, es decir ruido. Los trazos de las letras apenas se mueven.
    """
    diferencia = np.abs(
        np.asarray(original, dtype=np.int16) - np.asarray(filtrada, dtype=np.int16)
    )
    return float((diferencia > parametros["salto_minimo_mota"]).mean())


def quitar_motas(imagen: Image.Image, parametros: dict | None = None) -> Image.Image:
    """Elimina el ruido de sal y pimienta, pero solo si la pagina lo tiene.

    El filtro de mediana es el indicado para este ruido: un pixel aislado nunca es
    la mediana de su vecindad y desaparece, mientras que un trazo de letra, que
    ocupa varios pixeles seguidos, sobrevive. Sin este paso la binarizacion
    convierte cada mota del papel en una mancha negra y el motor de OCR ve una
    pagina cubierta de suciedad.

    Pero el filtro no es gratis: sobre un escaneo ya limpio adelgaza los trazos
    finos y empeora el reconocimiento. Por eso se mide primero cuanto ruido hay y
    se aplica solo cuando compensa, en vez de fijar la decision de antemano.
    """
    parametros = parametros or cfg.PREPROCESO_OCR
    tamano = parametros["tamano_filtro_mediana"]
    if tamano < 3:
        return imagen

    filtrada = imagen.filter(ImageFilter.MedianFilter(size=tamano))
    if medir_motas(imagen, filtrada, parametros) < parametros["umbral_motas"]:
        return imagen
    return filtrada


def estimar_inclinacion(imagen: Image.Image, parametros: dict | None = None) -> float:
    """Estima en grados cuanto esta inclinado el texto de la pagina.

    Usa el metodo del perfil de proyeccion: se prueban varios angulos y se elige
    aquel en que la suma de tinta por fila varia mas bruscamente. Cuando los
    renglones estan horizontales, las filas alternan entre mucha tinta (el texto)
    y ninguna (el interlineado), y esa alternancia es maxima; si la pagina esta
    torcida, cada fila cruza varios renglones y el perfil se aplana.

    El analisis corre sobre una copia reducida, porque el angulo no depende de la
    resolucion y hacerlo a tamano completo costaria decenas de rotaciones caras.
    """
    parametros = parametros or cfg.PREPROCESO_OCR

    ancho_analisis = parametros["ancho_analisis_inclinacion"]
    if imagen.width > ancho_analisis:
        proporcion = ancho_analisis / imagen.width
        reducida = imagen.resize(
            (ancho_analisis, max(1, int(imagen.height * proporcion))),
            Image.BILINEAR,
        )
    else:
        reducida = imagen

    rango = parametros["rango_busqueda_grados"]
    paso = parametros["paso_busqueda_grados"]
    angulos = np.arange(-rango, rango + paso / 2, paso)

    mejor_angulo = 0.0
    mejor_puntaje = -1.0

    for angulo in angulos:
        girada = reducida.rotate(angulo, resample=Image.BILINEAR, fillcolor=255)
        # Tinta por fila: 255 - gris, para que el texto sume y el papel no.
        perfil = (255.0 - np.asarray(girada, dtype=np.float32)).sum(axis=1)
        puntaje = float(np.var(np.diff(perfil)))
        if puntaje > mejor_puntaje:
            mejor_puntaje = puntaje
            mejor_angulo = float(angulo)

    return mejor_angulo


def enderezar(imagen: Image.Image,
              parametros: dict | None = None) -> tuple[Image.Image, float]:
    """Corrige la inclinacion de la pagina y devuelve la imagen y el angulo aplicado."""
    angulo = estimar_inclinacion(imagen, parametros)
    if abs(angulo) < 1e-6:
        return imagen, 0.0
    return imagen.rotate(angulo, resample=Image.BICUBIC, fillcolor=255), angulo


def umbral_de_otsu(arreglo: np.ndarray) -> int:
    """Calcula el umbral que mejor separa tinta de papel por el metodo de Otsu.

    Busca el corte que maximiza la varianza entre los dos grupos resultantes, sin
    necesidad de fijar un valor a mano: un escaneo oscuro y uno claro requieren
    umbrales distintos y elegirlo por imagen es lo que hace que funcione en los
    tres perfiles de degradacion.
    """
    histograma = np.bincount(arreglo.ravel(), minlength=256).astype(np.float64)
    total = histograma.sum()
    if total == 0:
        return 128

    niveles = np.arange(256)
    peso_fondo = np.cumsum(histograma)
    peso_frente = total - peso_fondo

    suma_total = float((niveles * histograma).sum())
    suma_fondo = np.cumsum(niveles * histograma)

    validos = (peso_fondo > 0) & (peso_frente > 0)
    if not validos.any():
        return 128

    media_fondo = np.divide(suma_fondo, peso_fondo, out=np.zeros(256), where=validos)
    media_frente = np.divide(
        suma_total - suma_fondo, peso_frente, out=np.zeros(256), where=validos,
    )
    varianza = peso_fondo * peso_frente * (media_fondo - media_frente) ** 2
    varianza[~validos] = -1.0

    return int(np.argmax(varianza))


def binarizar(imagen: Image.Image) -> Image.Image:
    """Deja la imagen en blanco y negro puro usando el umbral de Otsu."""
    arreglo = np.asarray(imagen.convert("L"), dtype=np.uint8)
    umbral = umbral_de_otsu(arreglo)
    binaria = np.where(arreglo > umbral, 255, 0).astype(np.uint8)
    return Image.fromarray(binaria, mode="L")


def ampliar_si_es_pequena(imagen: Image.Image, parametros: dict | None = None) -> Image.Image:
    """Agranda las imagenes de baja resolucion antes del OCR.

    Los motores de reconocimiento trabajan mejor con caracteres de cierta altura
    minima; un escaneo a 150 DPI queda por debajo y ampliarlo, aunque no agregue
    informacion, mejora el reconocimiento de manera consistente.
    """
    parametros = parametros or cfg.PREPROCESO_OCR
    if imagen.width >= parametros["ancho_minimo_para_ampliar"]:
        return imagen

    factor = parametros["factor_ampliacion"]
    return imagen.resize(
        (int(imagen.width * factor), int(imagen.height * factor)), Image.LANCZOS,
    )


def preparar(imagen: Image.Image, parametros: dict | None = None) -> Image.Image:
    """Aplica la cadena completa de preparacion previa al OCR."""
    parametros = parametros or cfg.PREPROCESO_OCR

    preparada = imagen.convert("L")

    # El orden de estos pasos pesa tanto como los pasos mismos:
    #
    # 1. La iluminacion se empareja primero, para que un unico umbral global
    #    sirva en toda la pagina y no solo en el centro.
    # 2. Las motas se quitan A RESOLUCION NATIVA, donde cada una ocupa un pixel
    #    y la mediana la borra. Si se ampliara antes, cada mota pasaria a ser un
    #    bloque de varios pixeles y el filtro ya no podria con ella.
    # 3. Recien despues se endereza y se amplia, sobre una imagen limpia.
    # 4. La binarizacion va al final, sobre la imagen ya ampliada, para que los
    #    bordes de las letras no queden dentados.
    if parametros["corregir_iluminacion"]:
        preparada = corregir_iluminacion(preparada, parametros)
    if parametros["tamano_filtro_mediana"] >= 3:
        preparada = quitar_motas(preparada, parametros)
    if parametros["corregir_inclinacion"]:
        preparada, _ = enderezar(preparada, parametros)

    preparada = ampliar_si_es_pequena(preparada, parametros)

    if parametros["binarizar"]:
        preparada = binarizar(preparada)

    return preparada
