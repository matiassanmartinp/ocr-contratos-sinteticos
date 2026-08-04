# Extracción de campos desde contratos en PDF mediante OCR

Proyecto de portafolio: extraer automáticamente los campos de contratos de
arriendo vehicular escaneados, y **medir** qué tan bien se extraen.

El problema es real; los datos, no. Este repositorio genera su propio dataset
sintético, de modo que cualquiera pueda clonarlo, reproducir el dataset completo
con una semilla y evaluar un extractor sin que exista un solo documento real de
por medio.

> **Estado:** generador, evaluación y extractor sobre texto nativo, terminados y
> medidos. Falta la vía OCR para documentos escaneados.

## Resultado actual

| Entrada | Exactitud por campo | Documentos perfectos |
|---|---|---|
| Texto nativo del PDF | **100,0%** | **100,0%** |
| Escaneo limpio | pendiente | |
| Escaneo medio | pendiente | |
| Escaneo degradado | pendiente | |

Medido sobre 200 contratos generados con una semilla distinta de la usada para
escribir los patrones: 3.000 campos, cero errores, cero omisiones y cero
confusiones con la contraparte.

Ese 100% es el **techo de la lógica de parseo**, no el rendimiento del sistema
completo. Separar las dos cosas es deliberado: midiendo primero sobre texto limpio
se sabe cuánto cuesta el OCR, y por lo tanto si conviene invertir en mejorar los
patrones o en mejorar la calidad del escaneo. Es la pregunta que de verdad importa
cuando el proceso corre sobre documentos reales.

```bash
python -m generador --cantidad 200 --semilla 777 --solo-pdf && python -m extractor && python -m evaluacion
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

Solo dependencias de Python — no requiere Tesseract, Poppler ni binarios
externos. El rasterizado usa PyMuPDF.

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
generador/            Datos sintéticos, plantillas, render PDF, escaneo, ground truth
extractor/            Lectura del PDF, patrones por campo, normalización canónica
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

Cubren el dígito verificador contra una implementación independiente, el formato
de las patentes, la coherencia entre fechas y plazo, que el ground truth esté
completo y que sus valores aparezcan efectivamente en el PDF, que el rasterizado
respete el DPI del perfil, que la degradación crezca con la agresividad del
perfil, y que dos corridas con la misma semilla produzcan JSON idénticos byte a
byte.
