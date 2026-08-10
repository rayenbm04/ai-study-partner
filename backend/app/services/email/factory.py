from app.core.config import Settings
from app.services.email.base import EmailSender
from app.services.email.logging_sender import LoggingEmailSender


def build_email_sender(settings: Settings) -> EmailSender:
    """Only "logging" exists today (see LoggingEmailSender's docstring for
    why) — this factory is the single place a real provider gets wired in
    later, same shape as services/llm/factory.py."""
    return LoggingEmailSender()
