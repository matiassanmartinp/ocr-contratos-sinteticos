# evaluacion/ — pendiente

Módulo de medición. Todavía no implementado.

## Qué debe medir

Comparar lo que devuelve `extractor/` contra el ground truth que produce
`generador/`, campo por campo, sobre los campos de
[`esquema_contrato.py`](../esquema_contrato.py).

Métricas mínimas:

- **Exactitud por campo** — porcentaje de documentos en que el campo se extrajo
  idéntico al valor canónico. Es la métrica principal: los 15 campos no tienen
  la misma dificultad y un promedio global la esconde.
- **Exactitud de documento completo** — porcentaje de contratos con los 15 campos
  correctos. Es la métrica que importa si la salida se usa sin revisión humana.
- **Tasa de omisión vs. tasa de error** — separar "no encontró el campo" de
  "encontró un valor equivocado". El segundo caso es mucho más costoso: un campo
  vacío se detecta a simple vista, uno incorrecto no.

## Desgloses que el ground truth ya permite

Cada registro guarda `plantilla`, `perfil_escaneo` y `formatos_usados`, así que
la evaluación puede cortar los resultados por:

- layout (`formal` / `tabular` / `compacta`),
- calidad del escaneo (`limpio` / `medio` / `degradado`),
- formato de fecha, de monto y de patente,
- etiqueta usada para el RUT de la persona natural.

Ese desglose es el que indica dónde vale la pena trabajar: si `fecha_inicio` solo
falla en la plantilla formal, el problema es el parseo de fechas en palabras, no
el OCR.

## Confusión a vigilar explícitamente

Todos los contratos incluyen a la arrendadora fija (`Flota Meridiano SpA`, RUT
`99.000.001-8`, representante `Andrés Vergara Solís`, RUT `50.000.001-5`), cuyos
datos **no** forman parte del ground truth. Conviene reportar aparte cuántas
veces el extractor devolvió los datos de la arrendadora en lugar de los del
arrendatario: es un error distinto de "extrajo cualquier cosa" y tiene una causa
distinta.
