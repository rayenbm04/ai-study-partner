import asyncio
import re
from pathlib import Path

from app.infrastructure.storage.base import StoragePort

_UNSAFE_CHARS = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_filename(filename: str) -> str:
    """Strips path separators and anything else that isn't a plain filename
    character, so a crafted upload name can't escape the subject/document
    directory it belongs in."""
    name = Path(filename).name  # drop any directory components
    name = _UNSAFE_CHARS.sub("_", name)
    return name or "file"


class LocalStorage(StoragePort):
    def __init__(self, root_dir: str):
        self._root = Path(root_dir)

    def _path_for(self, subject_id: str, document_id: str, filename: str) -> Path:
        return self._root / subject_id / document_id / _safe_filename(filename)

    async def save(self, *, subject_id: str, document_id: str, filename: str, content: bytes) -> str:
        path = self._path_for(subject_id, document_id, filename)
        await asyncio.to_thread(self._write, path, content)
        return str(path.relative_to(self._root))

    def _write(self, path: Path, content: bytes) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)

    async def read(self, storage_path: str) -> bytes:
        path = self._root / storage_path
        return await asyncio.to_thread(path.read_bytes)

    async def delete(self, storage_path: str) -> None:
        path = self._root / storage_path
        await asyncio.to_thread(path.unlink, missing_ok=True)
