import logging
import sys

from app.core.config import settings


def configure_logging() -> None:
    level = logging.DEBUG if settings.environment == "development" else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stdout,
    )
    # SQLAlchemy's engine logger is noisy at INFO; keep it at WARNING unless
    # someone explicitly wants query logs during local debugging.
    logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
