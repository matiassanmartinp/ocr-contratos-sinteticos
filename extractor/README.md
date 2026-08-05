# extractor/

Extrae los quince campos del contrato y los devuelve en su forma **canónica**.

Funciona con tres vías de lectura tras una misma interfaz: texto embebido del PDF,
Tesseract en local y Google Cloud Document AI. `campos.py` recibe una cadena y no
sabe de cuál vino, que es lo que permite comparar motores sobre documentos
idénticos.

```bash
python -m extractor --entrada salidas/pdf --motor nativo
```

```bash
python -m extractor --entrada salidas/escaneos --motor tesseract
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

### El techo de la lógica de parseo

El 100% sobre texto nativo se sostiene también con una semilla distinta de la usada
para escribir los patrones: 200 contratos, 3.000 campos, cero errores, cero
omisiones, cero confusiones con la arrendadora.

Ese número no es el rendimiento del sistema, es su **techo**: mide los patrones sin
ruido de OCR de por medio. Sirve para atribuir cada punto perdido a su causa real,
y lo que dice es que el margen de mejora no está en las regex sino en la calidad
del escaneo.

## La vía OCR

`ocr.py` despacha entre los dos motores y devuelve texto plano en ambos casos.

**Tesseract.** Antes de reconocer, `preproceso.py` endereza la página por el método
del perfil de proyección, aplana la iluminación dividiendo por su propio fondo,
quita las motas con un filtro de mediana **solo si la página las tiene** —sobre un
escaneo limpio el filtro adelgaza los trazos y perjudica— y binariza con el umbral
de Otsu. El orden importa tanto como los pasos: las motas se quitan a resolución
nativa, porque ampliar primero convierte cada una en un bloque que la mediana ya no
puede borrar. Sin ese preproceso el perfil degradado cae de 31% a 3%.

**Document AI.** Recibe el documento tal cual, sin preproceso local: el servicio
aplica su propio realce y adelantarse suele empeorar el resultado. Las credenciales
se leen del entorno y no existen en el repositorio. Es el motor de reconocimiento
del sistema original del que salió esta réplica; aquí es una vía que hay que activar
explícitamente, para que el repositorio funcione sin credencial alguna.

Sobre texto reconocido se activa `corregir_ocr=True`, que repara las confusiones
típicas de dígitos en los RUT —la O por un cero, la ele por un uno— usando el
dígito verificador como confirmación. Si aun así no cuadra, el campo se omite en
vez de devolverse mal.

## Resultados

| Entrada | Exactitud por campo | Documentos perfectos |
|---|---|---|
| Texto nativo | 100,0% | 100,0% |
| Escaneo limpio (Tesseract) | 94,4% | 46,7% |
| Escaneo medio (Tesseract) | 80,7% | 0,0% |
| Escaneo degradado (Tesseract) | 31,1% | 0,0% |

Document AI no tiene fila porque medirlo requiere una cuenta con facturación
activa. La construcción de su petición sí se ejercita contra la biblioteca real en
las pruebas; lo que no está cubierto es la llamada de red. Ver la sección
correspondiente en el [README principal](../README.md#los-dos-motores-de-ocr).
