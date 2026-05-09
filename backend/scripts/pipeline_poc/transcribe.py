"""
PoC: extracción estructurada de un examen manuscrito con qwen3-vl:8b (Ollama).

Salida por secciones:
  - exame      → nombre
  - metadata   → nombre, curso, fecha
  - questions  → lista de preguntas con número y puntuación
  - answers    → respuesta escrita por el alumno para cada pregunta
"""

import base64
import json
import re
from pathlib import Path

import ollama

IMAGE_PATH = Path(__file__).parent / "examen_prueba.jpeg"
MODEL = "qwen3-vl:8b"

PROMPT = """\
Analiza este examen manuscrito y devuelve un JSON con exactamente estas tres claves:

{
  "exam": "<nombre del examen>",
  "metadata": {
    "nombre": "<nombre del alumno>",
    "curso": "<curso>",
    "fecha": "<fecha>"
  },
  "questions": [
    { "numero": 1, "enunciado": "<texto de la pregunta>", "puntuacion": "<puntuación, ej: 3>" },
    ...
  ],
  "answers": [
    { "numero": 1, "respuesta": "<texto completo de la respuesta del alumno>" },
    ...
  ]
}

Transcribe el texto manuscrito tal como aparece, sin corregir ni interpretar. Ten en cuenta que el
alumno puede haberse equivocado y haber tachado alguna o algunas palabras. En ese caso habrá escrito
cerca de esa corrección lo que realmente quería poner.

/no_think
Devuelve únicamente el JSON, sin texto adicional ni bloques de razonamiento.
"""


def load_image_b64(path: Path) -> str:
    return base64.b64encode(path.read_bytes()).decode()


def extract_json(text: str) -> dict:
    # Elimina bloques <think>...</think> que Qwen3 puede incluir igualmente
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Extrae el primer objeto JSON del texto
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"No se encontró JSON en la respuesta:\n{text!r}")
    return json.loads(match.group())


def main() -> None:
    print(f"Imagen: {IMAGE_PATH.name}")
    print(f"Modelo: {MODEL}\n")

    # La imagen la codificamos en base64
    image_b64 = load_image_b64(IMAGE_PATH)

    response = ollama.chat(
        model=MODEL,
        messages=[
            {
                "role": "user",
                "content": PROMPT,
                "images": [image_b64],
            }
        ],
    )

    raw = response.message.content
    data = extract_json(raw)

    print("=== EXAMEN ===")
    print(f"  {data['exam']}")

    print("=== METADATOS ===")
    for key, value in data["metadata"].items():
        print(f"  {key}: {value}")

    print("\n=== PREGUNTAS ===")
    for q in data["questions"]:
        print(f"  P{q['numero']} [{q['puntuacion']}p] — {q['enunciado']}")

    print("\n=== RESPUESTAS ===")
    for a in data["answers"]:
        print(f"\n  Pregunta {a['numero']}:")
        print(f"  {a['respuesta']}")


if __name__ == "__main__":
    main()
