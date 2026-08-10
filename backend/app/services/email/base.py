from abc import ABC, abstractmethod


class EmailSender(ABC):
    """Outbound transactional email (verification, password reset). Every
    call in the app goes through this interface, never through a provider SDK
    directly — same reasoning as LLMProvider — so wiring up a real provider
    (Resend, SendGrid, SES, ...) later is a new implementation + a config
    change, not a rewrite of AuthService."""

    @abstractmethod
    async def send(self, *, to: str, subject: str, body: str) -> None: ...
