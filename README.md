# Extracción de campos desde contratos en PDF mediante OCR

Proyecto de portafolio: extraer automáticamente los campos de contratos de
arriendo vehicular escaneados, y **medir** qué tan bien se extraen.

El problema es real; los datos, no. Este repositorio genera su propio dataset
sintético, de modo que cualquiera pueda clonarlo, reproducir el dataset completo
con una semilla y evaluar un extractor sin que exista un solo documento real de
por medio.

> **Estado:** completo. Generación sintética, extracción por texto embebido y por
> OCR, y evaluación contra ground truth.

## Resultado

Treinta contratos, los **mismos treinta** en las cuatro filas: lo único que cambia
es la calidad de la imagen que entra. La degradación usa su propio generador
aleatorio, así que cambiar de perfil no cambia los datos y la comparación es
pareada.

| Entrada | Exactitud por campo | Documentos perfectos | Error | Omisión | s/doc |
|---|---|---|---|---|---|
| Texto nativo del PDF | **100,0%** | **100,0%** | 0,0% | 0,0% | 0,01 |
| Escaneo limpio (Tesseract) | 94,4% | 46,7% | 2,2% | 3,3% | 2,4 |
| Escaneo medio (Tesseract) | 80,7% | 0,0% | 7,3% | 12,0% | 1,9 |
| Escaneo degradado (Tesseract) | 31,1% | 0,0% | 11,1% | 57,8% | 2,0 |

Tres cosas que dice esta tabla y que no se ven en un promedio global:

**El parseo no es el cuello de botella.** Sobre texto limpio los quince campos
salen perfectos, también con una semilla nunca vista (200 documentos, 3.000
campos, cero errores). Todo lo que se pierde después lo pierde el OCR, no los
patrones. Si el objetivo fuera subir la precisión, invertir en mejorar las regex
sería trabajo desperdiciado; el margen está en la calidad del escaneo.

**La exactitud por documento se derrumba mucho antes que la exactitud por campo.**
Con escaneos limpios el 94,4% de los campos está bien, pero solo el 46,7% de los
contratos está *completo*. Quince campos por documento castigan duro: basta que
uno falle para invalidar la fila. Si la salida se usa sin revisión humana, la
segunda columna es la que manda.

**Hay un punto de quiebre, no una pendiente.** Entre limpio y medio se pierden 14
puntos; entre medio y degradado, 50. El perfil degradado (150 DPI, ruido fuerte,
JPEG al 55%) es donde Tesseract deja de servir: no se equivoca más, directamente
no lee, y el 57,8% de omisión lo confirma. Eso es una recomendación operativa
concreta: exigir un mínimo de calidad al digitalizar rinde más que cualquier
ajuste del extractor.

### La omisión es deliberada

Cuando el reconocimiento falla, el extractor prefiere devolver el campo vacío
antes que un valor dudoso. Los RUT se validan con su dígito verificador y las
patentes contra el alfabeto del registro chileno, que excluye vocales. Un campo
vacío se detecta en cualquier revisión; uno incorrecto se cuela hasta la planilla
final. Por eso el informe separa error de omisión en vez de sumarlos.

### Reproducir la medición

```bash
python -m generador --cantidad 30 --semilla 2026 --perfil medio
```

```bash
python -m extractor --entrada salidas/escaneos --motor tesseract
```

```bash
python -m evaluacion --etiqueta "OCR medio"
```

---

## Por qué el dataset es sintético

Los contratos de origen contienen razones sociales, RUT, domicilios y nombres de
personas identificables. Publicarlos —o publicar cualquier salida derivada de
ellos— no es una opción.

La alternativa habitual, anonimizar, deja el problema a medias: obliga a confiar
en que el reemplazo fue exhaustivo, y basta un domicilio olvidado en un contrato
para filtrar un dato personal.

Aquí el repositorio **no puede** filtrar nada, porque nunca contuvo nada:

- Todos los datos se generan en tiempo de ejecución desde catálogos inventados
  ([`configuracion.py`](configuracion.py)).
- Los RUT se sortean en tramos **no asignados** por el Servicio de Impuestos
  Internos (`99.xxx.xxx` para empresas, `5x.xxx.xxx` para personas). Formato y
  dígito verificador son idénticos a los reales; la colisión con una entidad
  existente es imposible.
- Las patentes usan el mismo criterio: el registro chileno asigna en orden
  alfabético correlativo y aún no llega a los prefijos `X`, `Y` y `Z`, así que una
  patente sintética no puede coincidir con la de un vehículo en circulación.
  Quedan 1,7 millones de combinaciones, de sobra para cualquier lote.
- La redacción de las plantillas es propia. No reproduce el articulado ni las
  fórmulas de apertura de ningún contrato concreto — ver la nota en
  [`plantilla_formal.py`](generador/plantillas/plantilla_formal.py).
- Las marcas y modelos de vehículo también son inventados, para no incluir
  marcas de terceros.
- El [`.gitignore`](.gitignore) excluye PDFs, imágenes, CSVs y planillas, además
  de las carpetas donde típicamente se sincronizan documentos reales.
- Nada generado se versiona: el dataset se reconstruye con la semilla.

---

## Instalación

```bash
pip install -r requirements.txt
```

Eso basta para generar el dataset y para extraer desde PDFs con texto embebido.

**Para la vía OCR hace falta además el binario de Tesseract**, que no se instala
con pip:

| Sistema | Comando |
|---|---|
| Debian / Ubuntu | `sudo apt-get install tesseract-ocr tesseract-ocr-spa` |
| macOS | `brew install tesseract tesseract-lang` |
| Windows | Instalador de [UB Mannheim](https://github.com/UB-Mannheim/tesseract/wiki), marcando el idioma español |

Comprobar que quedó bien, incluido el idioma:

```bash
tesseract --list-langs
```

Debe aparecer `spa`. Si el binario no está en el `PATH`, indicar su ruta en la
variable de entorno `TESSERACT_EXE` (ver [`.env.example`](.env.example)).

### Google Document AI (opcional)

El proceso real usa Document AI. El repositorio trae la integración, pero **no
contiene ninguna credencial**: todo se lee del entorno.

```bash
pip install -r requirements-opcional.txt
```

```bash
cp .env.example .env
```

Completar en `.env` la ruta al JSON de la cuenta de servicio y el nombre de
recurso del procesador. El archivo `.env` y cualquier JSON de credenciales están
excluidos en el [`.gitignore`](.gitignore). Sin estas variables el proyecto
funciona igual con Tesseract; solo se desactiva `--motor documentai`.

## Uso

Generar un lote de 50 contratos repartidos entre las tres calidades de escaneo:

```bash
python -m generador --cantidad 50 --semilla 42 --perfil mixto
```

Opciones principales:

| Argumento | Efecto |
|---|---|
| `--cantidad N` | Cuántos contratos generar |
| `--semilla N` | Fija el lote completo; misma semilla ⇒ mismo dataset |
| `--perfil` | `limpio`, `medio`, `degradado` o `mixto` |
| `--plantilla` | Fuerza un layout: `formal`, `tabular` o `compacta` |
| `--solo-pdf` | Omite el rasterizado (solo PDFs nativos) |
| `--limpiar` | Borra los artefactos previos antes de generar |

Extraer y medir:

```bash
python -m extractor --entrada salidas/escaneos --motor tesseract
```

| `--motor` | Qué usa |
|---|---|
| `auto` | Texto embebido si el documento lo trae; si no, Tesseract |
| `nativo` | Solo texto embebido, sin OCR. Es el techo de la lógica de parseo |
| `tesseract` | OCR local. No necesita credenciales |
| `documentai` | Google Cloud Document AI. Requiere credenciales en el entorno |

Resultado en `salidas/`:

```
salidas/
├── pdf/            SINT-0001.pdf         PDF nativo, con texto embebido
├── escaneos/       SINT-0001_p01.jpg     imagen degradada, simula un escaneo
└── ground_truth/   SINT-0001.json        valores canónicos + metadata
                    manifiesto.jsonl      el lote completo, una línea por contrato
```

## Cómo está armado el desafío

El generador no busca producir documentos bonitos, sino documentos **difíciles de
extraer por posición**, que es la trampa clásica de este tipo de proyectos.

**Tres layouts distintos.** `formal` es prosa corrida con los datos embebidos en
párrafos; `tabular` es una ficha de campo y valor; `compacta` es un formulario a
dos columnas con membrete lateral, tipografía menor y etiquetas abreviadas. Un
mismo campo cae en tres lugares completamente distintos de la página.

**El mismo dato impreso de formas distintas.** El ground truth guarda el valor
canónico; cada plantilla lo renderiza a su manera:

| Campo | `formal` | `tabular` | `compacta` |
|---|---|---|---|
| Fecha | `12 de marzo de 2024` | `12/03/2024` | `12-03-2024` |
| Monto | `cuatrocientos cincuenta mil pesos ($450.000)` | `$450.000` | `$450.000.-` |
| Patente | `BCDF·12` | `BCDF-12` | `BCDF12` |
| RUT persona | `cédula de identidad N°` | `C.I. N°` | `RUT:` |

**Una contraparte que no se debe extraer.** Todos los contratos incluyen a la
arrendadora ficticia `Flota Meridiano SpA`, con su propio RUT y su propio
representante legal, que **no** forman parte del ground truth. Confundirla con el
arrendatario es el error más probable, y es el mismo problema que aparece en los
contratos reales, donde conviven la empresa mandante y la contraparte.

**Degradación de escaneo en tres niveles.** Rasterizado a DPI variable,
inclinación del papel, iluminación despareja, desenfoque óptico, ruido de sensor,
motas de polvo y compresión JPEG agresiva. Todos los parámetros viven en
`PERFILES_ESCANEO`, en [`configuracion.py`](configuracion.py).

## Campos extraídos

Quince campos, con nombres alineados al esquema del extractor de producción para
que lo validado en sintético se transfiera sin renombrar nada:

`ppu`, `marca`, `modelo`, `ano`, `razon_social`, `rut_empresa`, `giro`,
`domicilio`, `nombre_representante`, `rut_representante`, `fecha_inicio`,
`fecha_termino`, `plazo_meses`, `valor_cuota`, `numero_pagare`.

Definición y forma canónica de cada uno en
[`esquema_contrato.py`](esquema_contrato.py).

> **Sobre la cédula:** en Chile la cédula de identidad de una persona natural es
> su RUN, o sea el mismo número que su RUT. Por eso hay un solo campo,
> `rut_representante`, y no un `cedula` que duplicaría el dato. Lo que sí varía
> es la etiqueta con que cada plantilla lo rotula.

## Estructura

```
configuracion.py      Todos los parámetros ajustables, en un solo lugar
esquema_contrato.py   Definición de los 15 campos y su forma canónica
formato_chileno.py    RUT con dígito verificador y patente, compartidos
rasterizado.py        PDF a imagen, compartido por generador y extractor
generador/            Datos sintéticos, plantillas, render PDF, escaneo, ground truth
extractor/            Lectura (nativa y OCR), preproceso, patrones, normalización
evaluacion/           Comparación contra ground truth y métricas
tests/                Pruebas con pytest
```

El flujo completo son tres comandos encadenables:

```bash
python -m generador --cantidad 50 --semilla 42 --solo-pdf
```

```bash
python -m extractor
```

```bash
python -m evaluacion --etiqueta "texto nativo"
```

## Pruebas

```bash
python -m pytest -q
```

145 pruebas. Cubren el dígito verificador contra una implementación independiente,
el formato de las patentes, la coherencia entre fechas y plazo, que el ground truth
esté completo y que sus valores aparezcan efectivamente en el PDF, que el
rasterizado respete el DPI del perfil, que la degradación crezca con la agresividad
del perfil, que dos corridas con la misma semilla produzcan JSON idénticos byte a
byte, que la extracción sobre texto nativo sea perfecta en los tres layouts, que
nunca se devuelvan los datos de la contraparte fija, que el enderezado recupere el
ángulo con que se torció la página, y que la evaluación cuente por separado errores
y omisiones.

Las pruebas de OCR se saltan solas si Tesseract no está instalado. Las de Document
AI nunca contactan al servicio: solo comprueban que la falta de credenciales se
informe con un mensaje útil.

El [CI](.github/workflows/pruebas.yml) corre todo en Python 3.11, 3.12 y 3.13, con
Tesseract instalado, y además verifica el flujo completo de extremo a extremo y que
ningún artefacto generado se cuele al repositorio.
