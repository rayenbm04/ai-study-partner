from abc import ABC, abstractmethod


class StoragePort(ABC):
    """Where uploaded document bytes live. Local disk in development; an S3
    (or compatible) implementation of the same interface is a drop-in swap
    for production — nothing above this layer knows or cares which one is
    active."""

    @abstractmethod
    async def save(self, *, subject_id: str, document_id: str, filename: str, content: bytes) -> str:
        """Persists `content` and returns an opaque storage path to pass back
        into read()/delete() later. Callers must not assume anything about
        the path's structure."""
        ...

    @abstractmethod
    async def read(self, storage_path: str) -> bytes: ...

    @abstractmethod
    async def delete(self, storage_path: str) -> None: ...
