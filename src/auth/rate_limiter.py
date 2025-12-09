# src/auth/rate_limiter.py
from datetime import datetime, timedelta
from sqlalchemy import select, update, insert, delete
from src.database import engine
from src.models import PasswordResetAttempt
from src.config import settings

MAX_FAILED_ATTEMPTS = 3
LOCKOUT_DURATIONS = [1, 5, 1440]

async def is_password_reset_allowed(email: str) -> int | None:
    """
    Возвращает:
      - None → если разрешено,
      - секунды до разблокировки → если заблокировано.
    """
    if settings.ENVIRONMENT in ("TEST", "LOCAL"):
        return None

    now = datetime.utcnow()
    async with engine.begin() as conn:
        cutoff = now - timedelta(days=2)
        await conn.execute(
            delete(PasswordResetAttempt).where(PasswordResetAttempt.last_attempt_at < cutoff)
        )

        result = await conn.execute(
            select(PasswordResetAttempt).where(PasswordResetAttempt.email == email)
        )
        attempt = result.fetchone()

        if not attempt:
            # Первая попытка — разрешаем
            await conn.execute(
                insert(PasswordResetAttempt).values(
                    email=email,
                    failed_attempts=1,
                    last_attempt_at=now
                )
            )
            return None

        if now - attempt.last_attempt_at > timedelta(days=1):
            await conn.execute(
                update(PasswordResetAttempt)
                .where(PasswordResetAttempt.email == email)
                .values(failed_attempts=1, last_attempt_at=now)
            )
            return None

        if attempt.failed_attempts >= MAX_FAILED_ATTEMPTS:
            lock_duration = LOCKOUT_DURATIONS[-1]
        else:
            lock_duration = LOCKOUT_DURATIONS[attempt.failed_attempts - 1]

        unlock_time = attempt.last_attempt_at + timedelta(minutes=lock_duration)
        if now < unlock_time:
            return int((unlock_time - now).total_seconds())

        await conn.execute(
            update(PasswordResetAttempt)
            .where(PasswordResetAttempt.email == email)
            .values(failed_attempts=attempt.failed_attempts + 1, last_attempt_at=now)
        )
        return None

async def reset_failed_attempts(email: str) -> None:
    async with engine.begin() as conn:
        await conn.execute(
            update(PasswordResetAttempt)
            .where(PasswordResetAttempt.email == email)
            .values(failed_attempts=0, last_attempt_at=datetime.utcnow())
        )