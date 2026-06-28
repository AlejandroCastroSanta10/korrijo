"""Prompt de la fase de estructuración (LLM textual).

Toma la transcripción en bruto que devuelve el modelo de OCR y la reorganiza en
la estructura de datos (metadatos + respuestas por pregunta) que consume la
corrección.
"""

STRUCTURING_PROMPT = """\
Vas a recibir la transcripción en bruto de un examen manuscrito, tal como la ha
extraído un modelo de OCR. Contiene, mezclados y en orden de lectura, la cabecera
con los datos del alumno, los enunciados impresos de las preguntas y las
respuestas que el alumno escribió a mano. Puede arrastrar ruido o errores de
lectura del OCR.

Tu tarea es estructurar esa transcripción en JSON. No corrijas, no resumas y no
completes el contenido: reorganiza lo que ya está.

Si el texto trae marcas de página ("--- Página N ---"), úsalas solo como
referencia del orden de lectura; no las copies en las respuestas y une las
respuestas que continúen de una página a la siguiente.

Cabecera:
- Extrae los datos del alumno que encuentres: nombre, apellidos, grupo, fecha y
  DNI. Deja en null los que no aparezcan.

Respuestas:
- Asocia cada respuesta del alumno al número de su pregunta, usando los enunciados
  impresos como guía. Si las preguntas no están numeradas, numéralas de forma
  correlativa según el orden de lectura.
- En "answer_text" va SOLO lo que escribió el alumno, NO el enunciado impreso de
  la pregunta. Conserva su texto literal.
- Si una pregunta no tiene respuesta, deja "answer_text" vacío ("") y anótalo en
  "notes".
- Usa "notes" para señalar dudas (respuesta en blanco, lectura dudosa del OCR,
  etc.). null si no hay nada que señalar.

Devuelve ÚNICAMENTE un objeto JSON con esta forma exacta, sin texto alrededor:

{
  "metadata": {
    "nombre": "<o null>",
    "apellidos": "<o null>",
    "grupo": "<o null>",
    "fecha": "<o null>",
    "dni": "<o null>"
  },
  "answers": [
    { "question_number": 1, "answer_text": "<respuesta literal del alumno>", "notes": <texto o null> }
  ]
}
"""
