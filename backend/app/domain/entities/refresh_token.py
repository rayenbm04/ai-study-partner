from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True, slots=True)
class RefreshToken:
    id: str
    user_id: str
    token_hash: str
    expires_at: datetime
    revoked_at: datetime | None
    created_at: datetime

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None
