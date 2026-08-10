"""Password hashing and token handling.

Access tokens are short-lived JWTs. Refresh tokens are opaque random strings —
only their SHA-256 hash is ever persisted, so a stolen database dump does not
hand out usable refresh tokens, and revocation is a simple row update instead
of needing a JWT blacklist.
"""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from jose import JWTError, jwt

from app.core.config import settings

_BCRYPT_MAX_BYTES = 72  # bcrypt silently ignores bytes beyond this

# Not an exhaustive breach-list (that'd need an external API, e.g.
# Have I Been Pwned's range search) — just the handful of passwords anyone
# would guess in three tries, in both languages this app's students use.
_COMMON_PASSWORDS = {
    "password", "password1", "12345678", "123456789", "1234567890",
    "qwertyui", "azertyui", "motdepasse", "motdepasse1", "azerty123",
    "admin1234", "letmein12", "iloveyou1", "welcome12", "changeme1",
    "00000000", "11111111", "abcd1234", "abc12345", "student12",
}


class TokenError(Exception):
    """Raised when an access token is missing, malformed, expired, or of the wrong type."""


def weak_password_reason(password: str, *, pseudo: str | None = None, email: str | None = None) -> str | None:
    """Returns a human-readable reason the password is too weak, or None if
    it clears this (deliberately light — length is already enforced by
    RegisterRequest) bar: not one of the handful of passwords everyone
    guesses first, not all-digits, and not just the student's own pseudo or
    email handle with the case changed."""
    lowered = password.lower()
    if lowered in _COMMON_PASSWORDS:
        return "that's one of the most commonly used passwords."
    if password.isdigit():
        return "use more than just numbers."
    if pseudo and lowered == pseudo.lower():
        return "it can't be the same as your pseudo."
    if email:
        local_part = email.split("@", 1)[0].lower()
        if local_part and lowered == local_part:
            return "it can't be the same as your email address."
    return None


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, hashed_password: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8")[:_BCRYPT_MAX_BYTES], hashed_password.encode("utf-8"))
    except ValueError:
        return False


def create_access_token(subject: str, extra_claims: dict | None = None) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)
    payload: dict = {"sub": subject, "exp": expire, "type": "access"}
    if extra_claims:
        payload.update(extra_claims)
    return jwt.encode(payload, settings.secret_key, algorithm="HS256")


def decode_access_token(token: str) -> dict:
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=["HS256"])
    except JWTError as exc:
        raise TokenError("Invalid or expired access token") from exc
    if payload.get("type") != "access":
        raise TokenError("Token is not an access token")
    return payload


def create_refresh_token() -> str:
    return secrets.token_urlsafe(48)


def create_verification_token() -> str:
    """Opaque token backing email verification / password reset links — same
    generation + only-the-hash-is-stored approach as refresh tokens."""
    return secrets.token_urlsafe(32)


def hash_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def refresh_token_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(days=settings.refresh_token_expire_days)
