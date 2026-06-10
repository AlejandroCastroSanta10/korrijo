import asyncio
from pathlib import Path

from app.services.storage.base import FileStorage, InvalidKey, StorageError


class LocalFileStorage(FileStorage):
    """Almacenamiento en el filesystem local bajo un directorio raíz."""

    def __init__(self, storage_root: Path | str) -> None:
        self._root = Path(storage_root).resolve()

    def _resolve(self, key: str) -> Path:
        """Resuelve key a una ruta absoluta dentro de storage_root."""
        candidate = (self._root / key).resolve()
        if candidate != self._root and not candidate.is_relative_to(self._root):
            raise InvalidKey(f"la key escapa del almacenamiento: {key!r}")
        return candidate

    async def save(self, content: bytes, key: str) -> str:
        path = self._resolve(key)

        def _write() -> None:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)

        try:
            await asyncio.to_thread(_write)
        except OSError as exc:
            raise StorageError(f"no se pudo guardar '{key}': {exc}") from exc
        return str(path)

    async def read(self, key: str) -> bytes:
        path = self._resolve(key)
        try:
            return await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            raise StorageError(f"no se pudo leer '{key}': {exc}") from exc

    async def delete(self, key: str) -> None:
        path = self._resolve(key)
        try:
            await asyncio.to_thread(path.unlink, missing_ok=True)
        except OSError as exc:
            raise StorageError(f"no se pudo borrar '{key}': {exc}") from exc

    async def exists(self, key: str) -> bool:
        path = self._resolve(key)
        return await asyncio.to_thread(path.is_file)
