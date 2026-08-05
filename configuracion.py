"""Parametros centralizados del proyecto.

Toda constante ajustable del generador vive aqui: rutas, semilla, rangos de los
valores sinteticos, catalogos de vocabulario y perfiles de degradacion del
escaneo. Ningun otro modulo define literales de configuracion propios.

AVISO DE PRIVACIDAD
-------------------
Los catalogos de este archivo son inventados. No corresponden a empresas,
personas, marcas de vehiculo ni domicilios reales. Ver README.md.
"""

import os
from pathlib import Path

# =============================================================================
# 1. RUTAS
# =============================================================================

DIRECTORIO_RAIZ = Path(__file__).resolve().parent
DIRECTORIO_SALIDAS = DIRECTORIO_RAIZ / "salidas"

SUBDIRECTORIO_PDF = "pdf"
SUBDIRECTORIO_ESCANEOS = "escaneos"
SUBDIRECTORIO_GROUND_TRUTH = "ground_truth"

NOMBRE_MANIFIESTO = "manifiesto.jsonl"


# =============================================================================
# 2. EJECUCION
# =============================================================================

SEMILLA_POR_DEFECTO = 42
CANTIDAD_POR_DEFECTO = 10

# Prefijo y ancho del identificador de documento: SINT-0001, SINT-0002, ...
PREFIJO_ID_DOCUMENTO = "SINT"
ANCHO_ID_DOCUMENTO = 4


# =============================================================================
# 3. RANGOS DE RUT
# =============================================================================
# Se usan deliberadamente tramos NO asignados por el Servicio de Impuestos
# Internos. El formato y el digito verificador son identicos a los reales, pero
# la probabilidad de colisionar con un RUT existente es nula. Si en algun
# momento se necesita realismo estadistico (por ejemplo empresas en 76.xxx.xxx),
# basta cambiar estos dos rangos.

RANGO_RUT_EMPRESA = (99_000_000, 99_999_999)
RANGO_RUT_PERSONA = (50_000_000, 59_999_999)


# =============================================================================
# 4. PATENTE VEHICULAR
# =============================================================================
# Formato chileno moderno: cuatro letras y dos digitos (LLLL-NN). El registro
# nacional excluye las vocales y algunas consonantes ambiguas.

LETRAS_PATENTE = "BCDFGHJKLPRSTVWXYZ"
LARGO_LETRAS_PATENTE = 4
LARGO_DIGITOS_PATENTE = 2

# El registro chileno asigna las patentes en orden alfabetico correlativo, asi que
# los prefijos del final del abecedario todavia no estan emitidos. Restringir la
# primera letra a ese tramo garantiza que una patente sintetica no pueda coincidir
# con la de un vehiculo en circulacion, sin perder el formato ni el realismo.
# Mismo criterio que los tramos de RUT no asignados de la seccion 3.
# Deja 3 x 18^3 x 100 = 1.749.600 combinaciones posibles.
LETRAS_INICIALES_PATENTE = "XYZ"


# =============================================================================
# 5. RANGOS DE LOS DATOS DEL CONTRATO
# =============================================================================

RANGO_ANO_VEHICULO = (2016, 2025)

RANGO_VALOR_CUOTA = (180_000, 950_000)
MULTIPLO_VALOR_CUOTA = 5_000

PLAZOS_MESES_POSIBLES = (12, 18, 24, 36, 48, 60)

# Ventana en la que puede caer la fecha de inicio del arriendo (inclusive).
FECHA_INICIO_MINIMA = "2021-01-01"
FECHA_INICIO_MAXIMA = "2025-06-30"

RANGO_NUMERO_PAGARE = (100_000, 999_999)


# =============================================================================
# 6. CONTRAPARTE FIJA (ARRENDADORA)
# =============================================================================
# Empresa ficticia que arrienda el vehiculo. Aparece en TODOS los contratos y
# sus datos NO forman parte del ground truth: existe justamente para que el
# extractor tenga que distinguir cual de las dos partes es la que interesa.
# Es el mismo problema que se da en los contratos reales, donde conviven la
# empresa mandante y la contraparte.
#
# Los RUT de abajo son validos (digito verificador correcto) y caen en el mismo
# tramo no asignado que el resto de los datos sinteticos.

ARRENDADOR_RAZON_SOCIAL = "Flota Meridiano SpA"
ARRENDADOR_RUT = "99.000.001-8"
ARRENDADOR_GIRO = "Arriendo de vehículos motorizados sin chofer"
ARRENDADOR_DOMICILIO = "Avenida Los Pinos 1450, piso 6, Providencia"
ARRENDADOR_REPRESENTANTE = "Andrés Vergara Solís"
ARRENDADOR_RUT_REPRESENTANTE = "50.000.001-5"


# =============================================================================
# 7. PLANTILLAS
# =============================================================================
# Peso relativo de cada layout cuando se genera un lote sin forzar plantilla.
# Tres layouts distintos impiden que el extractor dependa de posiciones fijas.

DISTRIBUCION_PLANTILLAS = {
    "formal": 0.40,
    "tabular": 0.30,
    "compacta": 0.30,
}


# =============================================================================
# 8. PERFILES DE ESCANEO
# =============================================================================
# Cada perfil describe una calidad de digitalizacion. Ningun literal numerico de
# degradacion vive fuera de este diccionario.
#
#   dpi                   resolucion del rasterizado del PDF
#   grados_rotacion       inclinacion aleatoria, en grados (min, max)
#   sigma_ruido           desviacion estandar del ruido gaussiano (escala 0-255)
#   tasa_sal_pimienta     fraccion de pixeles forzados a negro o blanco
#   radio_desenfoque      radio del desenfoque gaussiano, en pixeles
#   factor_brillo         multiplicador de brillo (min, max)
#   factor_contraste      multiplicador de contraste (min, max)
#   intensidad_vineteado  0 = iluminacion pareja, 1 = bordes muy oscuros
#   calidad_jpeg          calidad de compresion (1-95)

PERFILES_ESCANEO = {
    "limpio": {
        "dpi": 300,
        "grados_rotacion": (-0.3, 0.3),
        "sigma_ruido": 2.0,
        "tasa_sal_pimienta": 0.0,
        "radio_desenfoque": 0.3,
        "factor_brillo": (0.98, 1.02),
        "factor_contraste": (0.98, 1.02),
        "intensidad_vineteado": 0.05,
        "calidad_jpeg": 92,
    },
    "medio": {
        "dpi": 200,
        "grados_rotacion": (-1.2, 1.2),
        "sigma_ruido": 8.0,
        "tasa_sal_pimienta": 0.0015,
        "radio_desenfoque": 0.7,
        "factor_brillo": (0.90, 1.08),
        "factor_contraste": (0.88, 1.10),
        "intensidad_vineteado": 0.18,
        "calidad_jpeg": 75,
    },
    "degradado": {
        "dpi": 150,
        "grados_rotacion": (-2.5, 2.5),
        "sigma_ruido": 16.0,
        "tasa_sal_pimienta": 0.0060,
        "radio_desenfoque": 1.1,
        "factor_brillo": (0.80, 1.15),
        "factor_contraste": (0.78, 1.18),
        "intensidad_vineteado": 0.30,
        "calidad_jpeg": 55,
    },
}

PERFIL_ESCANEO_POR_DEFECTO = "medio"

# Valor especial de --perfil: reparte el lote entre los tres perfiles.
PERFIL_MIXTO = "mixto"

EXTENSION_ESCANEO = ".jpg"


# =============================================================================
# 9. EXTRACTOR
# =============================================================================

# Datos de la propia arrendadora. El extractor los descarta cuando aparecen como
# candidatos: en un contrato conviven las dos partes y la que interesa es siempre
# la contraparte. Conocer los datos propios es legitimo y es exactamente lo que
# hace un extractor de produccion.
def _valores_propios() -> dict:
    return {
        "rut_empresa": ARRENDADOR_RUT,
        "rut_representante": ARRENDADOR_RUT_REPRESENTANTE,
        "razon_social": ARRENDADOR_RAZON_SOCIAL,
        "nombre_representante": ARRENDADOR_REPRESENTANTE,
        "giro": ARRENDADOR_GIRO,
        "domicilio": ARRENDADOR_DOMICILIO,
    }


VALORES_PROPIOS = _valores_propios()

#: Motores de lectura disponibles.
#:   nativo      texto embebido del PDF, sin OCR. Es el techo de la logica de parseo.
#:   tesseract   OCR local, gratuito y sin credenciales.
#:   documentai  OCR de Google Cloud, el que corre en produccion.
#:   auto        usa el texto embebido si lo hay y cae a tesseract si no.
MOTOR_NATIVO = "nativo"
MOTOR_TESSERACT = "tesseract"
MOTOR_DOCUMENTAI = "documentai"
MOTOR_AUTO = "auto"

MOTORES_DISPONIBLES = (MOTOR_AUTO, MOTOR_NATIVO, MOTOR_TESSERACT, MOTOR_DOCUMENTAI)
MOTOR_POR_DEFECTO = MOTOR_AUTO

#: Minimo de caracteres para considerar que un PDF trae texto embebido util.
#: Por debajo de este umbral el documento se trata como escaneado.
MINIMO_CARACTERES_TEXTO_NATIVO = 200

NOMBRE_ARCHIVO_PREDICCIONES = "predicciones.jsonl"

# -- Tesseract ----------------------------------------------------------------
# El binario NO se instala con pip. Ver README. Si no esta en el PATH, indicar su
# ruta en la variable de entorno TESSERACT_EXE.
TESSERACT_EJECUTABLE = os.environ.get("TESSERACT_EXE", "")
TESSERACT_IDIOMA = "spa"
TESSERACT_CONFIG = "--oem 3 --psm 4"
TESSERACT_DPI_RASTERIZADO = 300

# -- Preproceso de imagen antes del OCR ---------------------------------------
# Un escaner deja el papel inclinado y la iluminacion despareja; enderezar y
# binarizar antes de reconocer vale mas que cualquier ajuste del motor.
PREPROCESO_OCR = {
    # Enderezado de la pagina.
    "corregir_inclinacion": True,
    "rango_busqueda_grados": 3.0,
    "paso_busqueda_grados": 0.25,
    "ancho_analisis_inclinacion": 900,

    # Ampliacion de escaneos de baja resolucion.
    "ancho_minimo_para_ampliar": 1400,
    "factor_ampliacion": 2.0,

    # Aplanado de la iluminacion. El fondo se estima sobre una copia diminuta,
    # porque la iluminacion es de frecuencia muy baja.
    "corregir_iluminacion": True,
    "ancho_estimacion_fondo": 160,
    "radio_difuminado_fondo": 12,

    # Filtro de mediana contra el ruido de sal y pimienta. El tamano debe ser
    # impar. Se aplica solo si la pagina supera "umbral_motas" de pixeles
    # ruidosos: sobre un escaneo limpio el filtro adelgaza los trazos y perjudica.
    "tamano_filtro_mediana": 3,
    "salto_minimo_mota": 40,
    # Valor elegido midiendo sobre los tres perfiles. No los separa limpiamente
    # porque sus niveles de ruido se solapan: subirlo favorece los escaneos
    # buenos y castiga los medios. Se prefirio el lado de los casos dificiles,
    # que es donde el filtro realmente hace falta.
    "umbral_motas": 0.004,

    "binarizar": True,
}

# -- Google Document AI -------------------------------------------------------
# TODAS las credenciales vienen del entorno. Este repositorio no contiene ni debe
# contener claves: ver .env.example.
#
#   GOOGLE_APPLICATION_CREDENTIALS  ruta al JSON de la cuenta de servicio
#   GOOGLE_DOCAI_PROCESSOR          projects/<id>/locations/<loc>/processors/<id>
#   GOOGLE_DOCAI_LOCATION           "us" o "eu", segun donde este el procesador
DOCAI_PROCESADOR = os.environ.get("GOOGLE_DOCAI_PROCESSOR", "")
DOCAI_UBICACION = os.environ.get("GOOGLE_DOCAI_LOCATION", "us")
DOCAI_CREDENCIALES = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS", "")
DOCAI_TIMEOUT_SEGUNDOS = 45
DOCAI_PARSEO_NATIVO_PDF = True


# =============================================================================
# 10. EVALUACION
# =============================================================================

#: Campos cuyo valor es texto libre. Se comparan tras normalizar espacios, y
#: ademas se les calcula similitud de caracteres, que es lo informativo cuando
#: el texto viene de OCR y difiere en una letra.
CAMPOS_TEXTO_LIBRE = (
    "razon_social", "giro", "domicilio", "nombre_representante",
    "marca", "modelo",
)

#: Dimensiones del ground truth por las que se puede desglosar el resultado.
DIMENSIONES_DESGLOSE = ("plantilla", "perfil_escaneo")


# =============================================================================
# 11. CATALOGOS DE VOCABULARIO (inventados)
# =============================================================================

# Los acentos y la letra enie son intencionales: los contratos reales los llevan
# y el extractor debe resolverlos correctamente sobre texto salido de OCR.

NOMBRES_PILA = (
    "Alonso", "Bernardita", "Camilo", "Daniela", "Esteban", "Fernanda",
    "Gonzalo", "Hilda", "Ignacio", "Javiera", "Karina", "Lucas",
    "Macarena", "Nicolás", "Olivia", "Patricio", "Rocío", "Sebastián",
    "Tamara", "Valentina", "Ximena", "Rodrigo", "Constanza", "Emilia",
)

APELLIDOS = (
    "Alarcón", "Bustamante", "Cárdenas", "Donoso", "Escalante", "Fuenzalida",
    "Guzmán", "Herrera", "Illanes", "Jaramillo", "Lagos", "Maldonado",
    "Norambuena", "Olivares", "Peralta", "Quintana", "Riquelme", "Sandoval",
    "Tapia", "Urrutia", "Valdivia", "Zambrano", "Cifuentes", "Mardones",
)

# Piezas para componer razones sociales ficticias.
NUCLEOS_RAZON_SOCIAL = (
    "Andes Austral", "Cumbre Verde", "Ruta Norte", "Vega Central",
    "Patagonia Log", "Terra Nova", "Puerto Claro", "Alto Nevado",
    "Cordillera Azul", "Bahía Serena", "Valle Hondo", "Punta Lima",
    "Sur Directo", "Cauce Limpio", "Faro Once", "Loma Blanca",
)

RUBROS_RAZON_SOCIAL = (
    "Transportes", "Logística", "Distribuidora", "Servicios",
    "Comercializadora", "Ingeniería", "Constructora", "Maquinarias",
)

SUFIJOS_SOCIETARIOS = ("S.A.", "SpA", "Ltda.", "S.A.", "SpA")

GIROS = (
    "Transporte de carga por carretera",
    "Distribución mayorista de alimentos",
    "Servicios de ingeniería y montaje",
    "Arriendo de maquinaria y equipos",
    "Comercio al por mayor de insumos industriales",
    "Servicios de logística y almacenaje",
    "Construcción de obras menores",
    "Mantenimiento de equipos industriales",
)

# Nombres de calle genericos, no vinculados a una direccion real concreta.
NOMBRES_CALLE = (
    "Los Aromos", "Las Acacias", "Los Cipreses", "El Roble",
    "Avenida Central", "Los Alerces", "Las Encinas", "El Peumo",
    "Los Canelos", "Avenida Los Pinos", "Las Camelias", "El Boldo",
)

TIPOS_VIA = ("Calle", "Avenida", "Pasaje")

COMUNAS = (
    "Providencia", "Ñuñoa", "La Florida", "Maipú", "Puente Alto",
    "San Miguel", "Quilicura", "Renca", "Peñalolén", "Macul",
    "Concepción", "Valparaíso", "Rancagua", "Temuco", "Antofagasta",
)

CIUDADES = (
    "Santiago", "Valparaíso", "Concepción", "Rancagua", "Temuco",
    "Antofagasta", "La Serena", "Puerto Montt",
)

# Marcas y modelos INVENTADOS. Se evitan marcas reales por la restriccion de no
# incluir nombres de empresas existentes; para un extractor basado en regex la
# diferencia es irrelevante, y deja el repositorio libre de marcas de terceros.
MARCAS_Y_MODELOS = {
    "Nordvik": ("K-200", "K-350", "Trailmax"),
    "Kirumo": ("Serie 4", "Serie 7", "Kargo"),
    "Talvera": ("Vantor", "Vantor XL", "Urbe"),
    "Zentara": ("Lumen X", "Lumen S", "Delta 9"),
    "Aurox": ("Carga 1500", "Carga 2500", "Pico"),
    "Velmar": ("Rumbo", "Rumbo Plus", "Costa"),
}

MESES_EN_PALABRAS = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
