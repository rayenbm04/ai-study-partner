import logging

from app.services.email.base import EmailSender

logger = logging.getLogger("app.email")


class LoggingEmailSender(EmailSender):
    """Stand-in for a real provider: no network call, just a clearly-marked
    log line with the full body (so a developer running the server locally
    can copy the verification/reset link straight out of the terminal).
    Swapping in a real provider (Resend, SendGrid, SES, ...) later is a new
    EmailSender implementation wired up in app/services/email/factory.py,
    not a change to AuthService."""

    async def send(self, *, to: str, subject: str, body: str) -> None:
        logger.info("EMAIL (not actually sent — no provider configured) to=%s subject=%s\n%s", to, subject, body)
