from abc import ABC, abstractmethod
from pathlib import PurePosixPath
from uuid import UUID


class StorageError(Exception):
    """Fallo en la capa de almacenamiento de ficheros (E/S, permisos, espacio...)."""


class InvalidKey(StorageError):
    """La key del fichero no es válida: vacía, '.'/'..' o path traversal."""


class FileStorage(ABC):
    """Capa de abstracción del almacenamiento de ficheros.

    El resto del código trabaja siempre con 'keys' (rutas relativas y opacas);
    cada implementación decide dónde y cómo persistirlas. Así se puede sustituir
    el filesystem local por S3 u otro backend sin tocar a quien la usa.
    """

    @abstractmethod
    async def save(self, content: bytes, key: str) -> str:
        """Guarda content bajo key y devuelve la ruta/identificador completo."""
        ...

    @abstractmethod
    async def read(self, key: str) -> bytes:
        """Devuelve el contenido del fichero guardado en key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Borra el fichero de key (no falla si no existe)."""
        ...

    @abstractmethod
    async def exists(self, key: str) -> bool:
        """Indica si hay un fichero guardado en key."""
        ...

    @staticmethod
    def key_for(user_id: UUID, session_id: UUID, filename: str) -> str:
        """Construye una key consistente: '{user_id}/{session_id}/{filename}'.

        El filename se reduce a su basename (se descarta cualquier componente de
        ruta) para que un nombre original malicioso no introduzca path traversal
        en la key. Lanza InvalidKey si no queda un nombre utilizable.
        """
        safe_name = PurePosixPath(filename.replace("\\", "/")).name
        if not safe_name or safe_name in {".", ".."} or "\x00" in safe_name:
            raise InvalidKey(f"nombre de fichero inválido: {filename!r}")
        return f"{user_id}/{session_id}/{safe_name}"
