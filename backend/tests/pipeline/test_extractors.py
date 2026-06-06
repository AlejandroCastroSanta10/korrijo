from pathlib import Path

import pytest

from app.pipeline.extractors import (
    ScannedPDFNotSupportedError,
    UnsupportedFormatError,
    extract,
)
from app.pipeline.extractors.pdf import extract_pdf
from app.pipeline.extractors.text import extract_text
from app.pipeline.extractors.xlsx import extract_xlsx

FIXTURES = Path(__file__).parent / "fixtures"


def test_extract_pdf_nativo_devuelve_texto_con_separadores_de_pagina():
    text = extract_pdf(FIXTURES / "rubrica.pdf")

    assert text
    assert "--- Página 1 ---" in text
    assert "algoritmo" in text


def test_extract_pdf_escaneado_lanza_excepcion():
    with pytest.raises(ScannedPDFNotSupportedError):
        extract_pdf(FIXTURES / "escaneado.pdf")


def test_extract_xlsx_devuelve_tabla_markdown_like():
    text = extract_xlsx(FIXTURES / "rubrica.xlsx")

    assert "## Rubrica" in text
    assert "| Criterio | Mal (0 p) | Regular (0,5 p) | Bien (1 p) |" in text
    assert "Definicion completa" in text


def test_extract_text_lee_txt_tal_cual():
    text = extract_text(FIXTURES / "contexto.txt")

    assert "estructuras de datos" in text


def test_extract_text_lee_md():
    text = extract_text(FIXTURES / "apuntes.md")

    assert text.startswith("# Tema 3")
    assert "LIFO" in text


def test_extract_text_lee_csv():
    text = extract_text(FIXTURES / "criterios.csv")

    assert "criterio,peso" in text
    assert "claridad,0.4" in text


def test_router_extract_delega_segun_extension(tmp_path):
    assert "algoritmo" in extract(FIXTURES / "rubrica.pdf")
    assert "Rubrica" in extract(FIXTURES / "rubrica.xlsx")
    assert "estructuras" in extract(FIXTURES / "contexto.txt")
    assert "Tema 3" in extract(FIXTURES / "apuntes.md")
    assert "claridad" in extract(FIXTURES / "criterios.csv")


def test_router_extract_acepta_extension_en_mayusculas(tmp_path):
    copia = tmp_path / "RUBRICA.PDF"
    copia.write_bytes((FIXTURES / "rubrica.pdf").read_bytes())

    assert "algoritmo" in extract(copia)


def test_router_extract_propaga_scanned_pdf_error():
    with pytest.raises(ScannedPDFNotSupportedError):
        extract(FIXTURES / "escaneado.pdf")


def test_router_extract_lanza_unsupported_para_imagen(tmp_path):
    imagen = tmp_path / "examen.jpg"
    imagen.write_bytes(b"\xff\xd8\xff")

    with pytest.raises(UnsupportedFormatError):
        extract(imagen)


def test_router_extract_lanza_unsupported_para_extension_desconocida(tmp_path):
    fichero = tmp_path / "documento.docx"
    fichero.write_bytes(b"PK\x03\x04")

    with pytest.raises(UnsupportedFormatError):
        extract(fichero)
