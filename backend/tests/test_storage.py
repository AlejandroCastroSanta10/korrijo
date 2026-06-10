import uuid
from pathlib import Path

import pytest

from app.services.storage import FileStorage, InvalidKey, LocalFileStorage


@pytest.fixture
def storage(tmp_path: Path) -> LocalFileStorage:
    # storage_root apunta a un subdirectorio que aún no existe: debe crearse solo.
    return LocalFileStorage(tmp_path / "storage")


@pytest.mark.asyncio
async def test_save_and_read_roundtrip(storage: LocalFileStorage):
    full_path = await storage.save(b"contenido", "user-1/session-1/test.pdf")

    assert Path(full_path).is_file()
    assert await storage.read("user-1/session-1/test.pdf") == b"contenido"


@pytest.mark.asyncio
async def test_save_creates_root_and_subdirs(tmp_path: Path):
    root = tmp_path / "no-existe-aun"
    storage = LocalFileStorage(root)
    assert not root.exists()

    await storage.save(b"x", "u/s/f.pdf")

    assert (root / "u" / "s" / "f.pdf").is_file()


@pytest.mark.asyncio
async def test_exists_reflects_save_and_delete(storage: LocalFileStorage):
    assert await storage.exists("u/s/f.pdf") is False

    await storage.save(b"x", "u/s/f.pdf")
    assert await storage.exists("u/s/f.pdf") is True

    await storage.delete("u/s/f.pdf")
    assert await storage.exists("u/s/f.pdf") is False


@pytest.mark.asyncio
async def test_delete_missing_key_is_noop(storage: LocalFileStorage):
    # Borrar algo que no existe no debe lanzar.
    await storage.delete("u/s/inexistente.pdf")


@pytest.mark.asyncio
async def test_save_rejects_path_traversal_key(storage: LocalFileStorage):
    with pytest.raises(InvalidKey):
        await storage.save(b"x", "u/s/../../../etc/passwd")


@pytest.mark.asyncio
async def test_read_rejects_absolute_key(storage: LocalFileStorage):
    with pytest.raises(InvalidKey):
        await storage.read("/etc/passwd")


def test_key_for_builds_consistent_key():
    uid = uuid.UUID("11111111-1111-1111-1111-111111111111")
    sid = uuid.UUID("22222222-2222-2222-2222-222222222222")

    assert FileStorage.key_for(uid, sid, "examen.pdf") == f"{uid}/{sid}/examen.pdf"


def test_key_for_strips_path_from_filename():
    uid, sid = uuid.uuid4(), uuid.uuid4()

    # Un filename con ruta se reduce a su basename: nada de traversal en la key.
    assert FileStorage.key_for(uid, sid, "../../etc/passwd") == f"{uid}/{sid}/passwd"


@pytest.mark.parametrize("bad_filename", ["", ".", "..", "../", "sub/.."])
def test_key_for_rejects_invalid_filename(bad_filename: str):
    with pytest.raises(InvalidKey):
        FileStorage.key_for(uuid.uuid4(), uuid.uuid4(), bad_filename)
