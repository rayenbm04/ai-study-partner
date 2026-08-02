from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class User:
    id: str
    email: str
    firstname: str
    lastname: str
    hashed_password: str
    role: str
    created_at: datetime
