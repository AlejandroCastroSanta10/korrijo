import pytest

from app.pipeline.utils import JSONParseError, parse_json_object


def test_parsea_objeto_limpio():
    assert parse_json_object('{"a": 1}') == {"a": 1}


def test_ignora_preambulo_y_epilogo():
    raw = "Claro, aquí tienes:\n{\"a\": 1}\nEspero que sirva."
    assert parse_json_object(raw) == {"a": 1}


def test_extrae_de_valla_de_codigo():
    assert parse_json_object('```json\n{"a": 1}\n```') == {"a": 1}


def test_elimina_bloque_think():
    assert parse_json_object('<think>mmm</think>{"a": 1}') == {"a": 1}


def test_repara_comas_finales_y_comillas_tipograficas():
    abre, cierra = chr(0x201C), chr(0x201D)
    raw = '{"a": ' + abre + "hola" + cierra + ",}"
    assert parse_json_object(raw) == {"a": "hola"}


def test_extrae_primer_objeto_balanceado_con_anidamiento():
    raw = '{"a": {"b": 2}} sobra'
    assert parse_json_object(raw) == {"a": {"b": 2}}


def test_respeta_llaves_dentro_de_strings():
    assert parse_json_object('{"a": "tiene } llave"}') == {"a": "tiene } llave"}


def test_vacio_lanza():
    with pytest.raises(JSONParseError):
        parse_json_object("   ")


def test_sin_objeto_lanza():
    with pytest.raises(JSONParseError):
        parse_json_object("aquí no hay json")


def test_no_objeto_json_lanza():
    with pytest.raises(JSONParseError):
        parse_json_object("[1, 2, 3]")
