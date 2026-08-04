# extractor/

Extrae los quince campos del contrato y los devuelve en su forma **canónica**.

> **Estado:** la vía de texto embebido está implementada y medida. La vía OCR,
> para los documentos escaneados, es lo que sigue.

```bash
python -m extractor --entrada salidas/pdf
```

Escribe `salidas/predicciones.jsonl`, una línea por documento, con los campos y
la metadata de proceso (método usado, segundos, caracteres leídos).

## Forma canónica de la salida

La normalización es responsabilidad del extractor, no de la evaluación:

| Campo | Forma canónica | Cómo puede venir impreso |
|---|---|---|
| `ppu` | `YWXT31` | `YWXT·31`, `YWXT-31`, `YWXT31` |
| `rut_empresa`, `rut_representante` | `99.453.789-K` | con o sin puntos |
| `fecha_inicio`, `fecha_termino` | `2022-06-07` | `07/06/2022`, `07-06-2022`, `7 de junio de 2022` |
| `valor_cuota` | `205000` | `$205.000`, `$205.000.-`, `doscientos cinco mil pesos ($205.000)` |
| `ano`, `plazo_meses` | enteros | |
| resto | texto, espacios colapsados | |

Un campo que no se pudo leer queda como cadena vacía. **Nunca se rellena con un
valor dudoso**: una omisión se detecta a simple vista en una revisión, un valor
equivocado se cuela hasta la planilla final.

## Cómo funciona

`texto.py` obtiene el texto del PDF y lo aplana: los saltos de línea de un PDF
marcan dónde terminó el margen, no dónde terminó la frase, así que aplanarlos
permite escribir patrones sobre el contenido y no sobre la maquetación.

`campos.py` aplica, por cada campo, una lista ordenada de patrones. Los primeros
son de **etiqueta** (`Razón social`, `R. SOCIAL:`, `DOMICILIO:`) y resuelven los
layouts de ficha y formulario; los últimos son de **estructura** (`dedicada a X,
con oficinas en Y`) y resuelven el layout en prosa, que no tiene etiquetas.

De cada patrón se recogen **todas** las coincidencias, no la primera. Un contrato
individualiza a dos partes y ambas encajan en el mismo patrón; la que se descarta
es la propia, comparando contra `configuracion.VALORES_PROPIOS`. Conocer los datos
de la empresa propia y filtrarlos es lo que hace cualquier extractor de producción,
y no hacerlo es el error más probable de todos.

Los RUT se clasifican en empresa y persona **por el texto que los antecede**, no
por el tramo numérico. Apoyarse en el rango sería un atajo que funciona en este
dataset y se rompe en cuanto cambian los datos. El layout compacto es el caso
difícil: rotula la cédula con un escueto `RUT:` y solo el `REP. LEGAL:` anterior
permite distinguirla del RUT de la empresa.

`normalizacion.py` lleva lo leído a la forma canónica y **valida el dígito
verificador** de cada RUT. Es la comprobación más barata del extractor y la que
mejor paga: convierte un error silencioso en una omisión visible.

## Resultado sobre texto nativo

100,0% de exactitud por campo y por documento, sobre 200 contratos generados con
una semilla distinta de la usada para escribir los patrones (3.000 campos, cero
errores, cero omisiones, cero confusiones con la arrendadora).

Ese número es el **techo de la lógica de parseo**, no el rendimiento del sistema:
mide los patrones sobre texto limpio, sin ruido de OCR. Sirve como línea base
contra la cual comparar la vía OCR, para poder atribuir cada punto perdido a su
causa real.

## Lo que sigue

`ocr.py`, con la misma interfaz que `texto.py`: rasterizar la imagen escaneada,
preprocesarla y pasarla por Tesseract en español. Ahí es donde
`canonizar_rut_leido(corregir_ocr=True)` empieza a ganarse el sueldo, corrigiendo
las confusiones típicas de dígitos con la validación del dígito verificador como
red de seguridad.
