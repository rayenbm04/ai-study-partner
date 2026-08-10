"""Opaque, single-use tokens backing email verification and password reset —
same shape/reasoning as RefreshToken (only a SHA-256 hash is ever persisted,
so a stolen DB dump doesn't hand out usable tokens): a raw token is generated,
handed to the (stubbed, for now) email sender, and only its hash is stored."""
from dataclasses import dataclass
from datetime import datetime
from typing import Literal

TokenPurpose = Literal["email_verify", "password_reset"]


@dataclass(frozen=True, slots=True)
class VerificationToken:
    id: str
    user_id: str
    token_hash: str
    purpose: TokenPurpose
    expires_at: datetime
    used_at: datetime | None
    created_at: datetime

    @property
    def is_active(self) -> bool:
        return self.used_at is None
