"""Genera los ficheros de prueba usados por los tests del módulo pipeline.

Los fixtures se commitean ya generados al repo; este script existe solo
para documentar cómo se construyeron y permitir regenerarlos si cambia el
contrato esperado.

Uso:
    cd backend
    .venv/bin/python tests/pipeline/fixtures/_generate.py
"""

from pathlib import Path

from openpyxl import Workbook
from pypdf import PdfWriter

FIXTURES_DIR = Path(__file__).parent


def make_native_pdf(text: str, output_path: Path) -> None:
    """Construye un PDF v1.4 mínimo con una sola página que muestra `text`."""
    lines = text.split("\n")
    stream_parts = ["BT", "/F1 12 Tf", "50 750 Td"]
    for i, line in enumerate(lines):
        if i > 0:
            stream_parts.append("0 -16 Td")
        escaped = line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        stream_parts.append(f"({escaped}) Tj")
    stream_parts.append("ET")
    content = "\n".join(stream_parts).encode("latin-1")

    objects: list[bytes] = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        (
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Contents 4 0 R /Resources << /Font << /F1 5 0 R >> >> >>"
        ),
        b"<< /Length " + str(len(content)).encode() + b" >>\nstream\n" + content + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]

    out = bytearray(b"%PDF-1.4\n%\xff\xff\xff\xff\n")
    offsets: list[int] = []
    for i, obj in enumerate(objects, start=1):
        offsets.append(len(out))
        out += f"{i} 0 obj\n".encode() + obj + b"\nendobj\n"

    xref_offset = len(out)
    out += f"xref\n0 {len(objects) + 1}\n".encode()
    out += b"0000000000 65535 f \n"
    for off in offsets:
        out += f"{off:010d} 00000 n \n".encode()
    out += (
        f"trailer\n<< /Size {len(objects) + 1} /Root 1 0 R >>\n"
        f"startxref\n{xref_offset}\n%%EOF\n"
    ).encode()

    output_path.write_bytes(bytes(out))


def make_scanned_pdf(output_path: Path) -> None:
    """Crea un PDF con una página en blanco (sin texto extraíble).

    Simula un PDF escaneado para el extractor: `pypdf.extract_text` devuelve
    cadena vacía y el extractor debe lanzar `ScannedPDFNotSupportedError`.
    """
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    with output_path.open("wb") as fh:
        writer.write(fh)


def make_rubric_xlsx(output_path: Path) -> None:
    """Crea un .xlsx con una rúbrica de ejemplo en una sola hoja."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Rubrica"

    sheet.append(["Criterio", "Mal (0 p)", "Regular (0,5 p)", "Bien (1 p)"])
    sheet.append(["Pregunta 1 - Definicion", "No responde", "Definicion parcial", "Definicion completa"])
    sheet.append(["Pregunta 2 - Ejemplo", "No aporta ejemplo", "Ejemplo erroneo", "Ejemplo correcto"])

    workbook.save(output_path)


def main() -> None:
    make_native_pdf(
        "Rubrica de correccion\n"
        "Pregunta 1: definir el concepto de algoritmo. Hasta 2 puntos.\n"
        "Pregunta 2: poner un ejemplo de algoritmo cotidiano. Hasta 1 punto.",
        FIXTURES_DIR / "rubrica.pdf",
    )
    make_scanned_pdf(FIXTURES_DIR / "escaneado.pdf")
    make_rubric_xlsx(FIXTURES_DIR / "rubrica.xlsx")

    (FIXTURES_DIR / "contexto.txt").write_text(
        "Tema 3: estructuras de datos lineales.\n"
        "Conceptos clave: pila, cola, lista enlazada.\n",
        encoding="utf-8",
    )
    (FIXTURES_DIR / "apuntes.md").write_text(
        "# Tema 3\n\n- Pila (LIFO)\n- Cola (FIFO)\n- Lista enlazada\n",
        encoding="utf-8",
    )
    (FIXTURES_DIR / "criterios.csv").write_text(
        "criterio,peso\nclaridad,0.4\ncompletitud,0.6\n",
        encoding="utf-8",
    )

    print(f"Fixtures regenerados en {FIXTURES_DIR}")


if __name__ == "__main__":
    main()
