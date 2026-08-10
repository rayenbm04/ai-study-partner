from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import settings
from app.core.exceptions import DomainError

engine = create_async_engine(
    settings.database_url,
    echo=False,
    pool_pre_ping=True,
)

AsyncSessionLocal = async_sessionmaker(bind=engine, expire_on_commit=False, class_=AsyncSession)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Request-scoped unit of work: commits on success, rolls back on error.

    Routes and services never call session.commit() themselves — this is the
    one place a transaction boundary is decided, which keeps services testable
    against fake in-memory repositories that don't have a session at all.

    A DomainError still commits: it's a business-rule 4xx response (bad
    password, duplicate email, ...), not a sign the transaction is corrupt —
    and some flows deliberately write *then* raise one in the same request
    (e.g. AuthService.authenticate records a failed-login attempt, then
    raises InvalidCredentialsError; that write must survive so the lockout
    counter actually accumulates). Anything else (a real bug, a DB error) is
    genuinely unsafe to keep, so those still roll back.
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
        except DomainError:
            await session.commit()
            raise
        except Exception:
            await session.rollback()
            raise
        else:
            await session.commit()
