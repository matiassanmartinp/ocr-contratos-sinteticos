# evaluacion/

Compara las predicciones del extractor contra el ground truth del generador.

```bash
python -m evaluacion
python -m evaluacion --json salidas/metricas.json --etiqueta "texto nativo"
```

## Tres desenlaces, no dos

Cada campo de cada documento cae en una de tres categorías:

- **correcto** — coincide con el valor canónico
- **omitido** — el extractor no devolvió nada
- **incorrecto** — devolvió algo distinto

La distinción entre los dos últimos es el punto. Un campo vacío y un campo con un
valor equivocado no cuestan lo mismo: el vacío salta a la vista en cualquier
revisión, el incorrecto se cuela hasta la planilla final sin que nadie lo note.
Contarlos juntos esconde justamente lo que hay que vigilar.

A los campos incorrectos se les calcula además la **similitud de caracteres**.
Solo es informativa cuando algo falla, y sirve para separar un error de una letra
—típico del OCR— de una lectura completamente equivocada, como haber tomado los
datos de la otra parte del contrato.

## Métricas

**Exactitud por campo.** La vista principal. Los quince campos no tienen la misma
dificultad y un promedio global esconde que, por ejemplo, todo funcione salvo la
fecha de término.

**Exactitud por documento.** Proporción de contratos con los quince campos
correctos. Es la métrica que importa si la salida se usa sin revisión humana: un
solo campo malo invalida la fila completa. Siempre es más baja que la anterior, y
la diferencia entre ambas dice cuán concentrados están los errores.

**Confusión con la propia arrendadora.** Cuántas veces se extrajeron los datos de
`Flota Meridiano SpA` en vez de los del arrendatario. Es un error de naturaleza
distinta a "leyó cualquier cosa": significa que el extractor identificó bien el
campo pero se equivocó de parte del contrato. Su causa y su arreglo son otros, así
que se cuenta aparte.

## Desgloses

Cada registro del ground truth guarda `plantilla`, `perfil_escaneo` y
`formatos_usados`, así que los resultados se pueden cortar por layout y por
calidad de escaneo. Ese corte es el que indica dónde trabajar: si `fecha_inicio`
solo falla en la plantilla formal, el problema es el parseo de fechas escritas en
palabras y no el OCR.

El informe termina con los peores campos y **ejemplos concretos** de cada fallo,
con el valor esperado y el obtenido lado a lado. En la práctica esos tres
ejemplos suelen bastar para ver la causa sin abrir un solo PDF.

## Un documento sin predicción cuenta como fallo

Si el extractor no procesó un documento, sus quince campos se cuentan como
omitidos y el informe lo avisa. No se descarta del promedio: un documento que ni
siquiera se pudo abrir es un fallo del sistema, no una fila que se pueda excluir
para que el número quede mejor.

## Salida en JSON

Con `--json` guarda todas las métricas más el detalle campo a campo. Sirve para
comparar corridas entre sí, que es como se ve si un cambio en el extractor mejoró
o solo movió los errores de lugar.
