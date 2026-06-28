"""Prompt de la fase de transcripción (VLM / modelo de OCR).

Se busca que sirva tanto a modelos de visión capaces de OCR como a modelos de
OCR puro (que pueden ignorar el prompt y limitarse a volcar texto). Por eso es
corto y solo pide transcribir: la estructuración la hace después el LLM textual.
Se envía una imagen (una página) por llamada.
"""

TRANSCRIPTION_PROMPT = """\
Eres un sistema de OCR. Transcribe TODO el texto que aparece en esta imagen de un
examen, respetando el orden de lectura.

- Incluye absolutamente todo lo que veas: la cabecera con los datos del alumno,
  los enunciados impresos de las preguntas y las respuestas escritas a mano por
  el alumno.
- Copia el texto literalmente: no corrijas las faltas de ortografía, no traduzcas,
  no resumas y no añadas nada que no esté escrito.
- Transcribe con precisión los números, símbolos, unidades y fórmulas.
- Si una palabra es difícil de leer, escribe tu mejor interpretación; no dejes
  huecos ni pongas "[ilegible]".
- Devuelve únicamente el texto transcrito, sin comentarios ni explicaciones.
"""
