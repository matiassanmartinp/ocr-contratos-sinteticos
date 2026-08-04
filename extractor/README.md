# extractor/ — pendiente

Módulo de extracción de campos. Todavía no implementado.

## Contrato de interfaz

El extractor consume los artefactos que produce `generador/` y devuelve los
mismos campos definidos en [`esquema_contrato.py`](../esquema_contrato.py), en su
forma **canónica**:

| Campo | Forma canónica esperada |
|---|---|
| `ppu` | `BCDF12` — sin separador, aunque el PDF imprima `BCDF·12` o `BCDF-12` |
| `rut_empresa`, `rut_representante` | `99.123.456-7` — con puntos y guion |
| `fecha_inicio`, `fecha_termino` | ISO `YYYY-MM-DD`, sea cual sea el formato impreso |
| `valor_cuota` | entero de pesos, sin puntos ni símbolo |
| `ano`, `plazo_meses` | enteros |
| resto | texto tal cual aparece |

Es decir: la normalización es responsabilidad del extractor, no de la evaluación.

## Dificultades que el generador ya introduce a propósito

1. **Tres layouts distintos** (prosa corrida, tabla, formulario a dos columnas),
   así que no se puede depender de coordenadas fijas.
2. **Formatos variables** del mismo dato: la fecha aparece como
   `12 de marzo de 2024`, `12/03/2024` o `12-03-2024`; el monto como
   `$450.000`, `$450.000.-` o escrito en palabras.
3. **Etiquetas variables**: el RUT del representante se rotula
   `cédula de identidad N°`, `C.I. N°` o `RUT:` según la plantilla.
4. **Una contraparte fija que NO se debe extraer**: todos los contratos incluyen
   a la arrendadora `Flota Meridiano SpA` con su propio RUT y su propio
   representante legal. Extraer sus datos en lugar de los del arrendatario es el
   error más probable, y es exactamente el mismo problema que aparece en los
   contratos reales.
5. **Degradación de escaneo** en tres niveles (`limpio`, `medio`, `degradado`).

## Cómo medirse

Cada documento tiene su ground truth en `salidas/ground_truth/<id>.json`, y el
lote completo en `salidas/ground_truth/manifiesto.jsonl`. El JSON registra
además qué plantilla, qué perfil de escaneo y qué variantes de formato se usaron,
para poder desglosar el error por condición.
