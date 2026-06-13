"""Prompt para la estructuración de la rúbrica (LLM textual).

La rúbrica la redacta el profesor en texto libre (PDF, tabla, lista...). Para
poder comprobar que la suma de puntos cuadra con la puntuación máxima del examen
y para que el profesor la valide visualmente, se le pide al LLM que la convierta
en una lista de ítems con su puntuación máxima.

El diseño y la justificación están en docs/pipeline-prompts.md.
"""

RUBRIC_PARSE_PROMPT = """\
Eres un asistente que estructura rúbricas de corrección. Recibirás la RÚBRICA de
un profesor en texto libre (puede venir como lista, tabla con niveles, párrafos,
etc.) y debes convertirla en una lista de ítems puntuables.

Instrucciones:
- Identifica cada criterio/ítem puntuable de la rúbrica. Usa los nombres tal como
  aparecen en ella; no inventes ítems que no estén ni omitas ninguno.
- "max_score" de cada ítem es la puntuación MÁXIMA que la rúbrica asigna a ese
  ítem. Si el ítem define niveles (columnas con % o con puntos), "max_score" es el
  valor del nivel más alto.
- "description" resume brevemente qué evalúa el ítem o sus niveles. Cadena vacía
  si la rúbrica no aporta más detalle.
- No calcules ni inventes una puntuación total: solo la puntuación máxima por ítem.

Devuelve ÚNICAMENTE un objeto JSON con esta forma exacta, sin texto alrededor:

{
  "items": [
    {
      "name": "<nombre del ítem tal como aparece en la rúbrica>",
      "max_score": <número>,
      "description": "<qué evalúa el ítem>"
    }
  ]
}

Responde solo con el JSON, sin texto alrededor.
"""
