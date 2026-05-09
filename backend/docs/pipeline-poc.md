# Documentación de la experiencia (Test a qwen3-vl:8b)

He probado el modelo de visión contra un pequeño examen hecho totalmente a mano por mí. He intentado que tenga cosas
que los exámenes que Korrijo procesará tendrán (nombre de examen, metadatos, preguntas junto con puntuaciones y respuestas).

Tanto la imagen del examen que se ha procesado como el script de Python para utilizar el modelo están en scripts/pipeline_poc.

La verdad es que los resultados han sido bastante buenos.

## Puntos positivos

- Prácticamente todo el texto identificado claramente, menos alguna palabrita suelta.
- Rayitas a final de línea se contemplan (el modelo las quita y las junta con la palabra de la siguiente línea).
- Letra grande y pequeña.
- Torceduras.
- Tachones

## Puntos negativos

- Una correción tachada con línea horizontal no se ha contemplado. En lugar de la palabra corregida se ha tenido en cuenta
la palabra tachada.