from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class Embedding:
    id: str
    chunk_id: str
    model_name: str
    dimension: int
