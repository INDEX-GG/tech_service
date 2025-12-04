import uuid
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi.security import OAuth2PasswordRequestForm
from pydantic import UUID4
from sqlalchemy import insert, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from src import utils
from src.auth.config import auth_config
from src.auth.exceptions import InvalidCredentials
from src.auth.schemas import AuthUser
from src.auth.security import check_password, hash_password
from src.models import RefreshTokens, User, execute, fetch_one, Roles, PasswordResetToken


async def create_user(user: AuthUser) -> dict[str, Any] | None:
    insert_query = (
        insert(User)
        .values(
            username=user.username,
            password=hash_password(user.password),
            is_executor=True,
            role=Roles.EXECUTOR,
            is_active=True,
            created_at=datetime.utcnow(),
        )
        .returning(User)
    )
    return await fetch_one(insert_query)


async def get_user_by_id(user_id: int) -> dict[str, Any] | None:
    select_query = select(User).where(User.id == user_id)
    return await fetch_one(select_query)


async def get_user_by_username(username: str, session: AsyncSession) -> dict[str, Any] | None:
    select_query = select(User).where(User.username == username)
    query = await session.execute(select_query)
    user = query.scalar_one_or_none()
    return user


async def create_refresh_token(
    *, user_id: int, refresh_token: str | None = None
) -> str:
    if not refresh_token:
        refresh_token = utils.generate_random_alphanum(64)

    insert_query = insert(RefreshTokens).values(
        uuid=uuid.uuid4(),
        refresh_token=refresh_token,
        expires_at=datetime.utcnow() + timedelta(seconds=auth_config.REFRESH_TOKEN_EXP),
        user_id=user_id,
    )
    await execute(insert_query)

    return refresh_token


async def get_refresh_token(refresh_token: str) -> dict[str, Any] | None:
    select_query = select(RefreshTokens).where(
        RefreshTokens.refresh_token == refresh_token
    )

    return await fetch_one(select_query)


async def expire_refresh_token(refresh_token_uuid: UUID4) -> None:
    update_query = (
        update(RefreshTokens)
        .values(expires_at=datetime.utcnow() - timedelta(days=1))
        .where(RefreshTokens.uuid == refresh_token_uuid)
    )

    await execute(update_query)


async def authenticate_user(auth_data: OAuth2PasswordRequestForm, session: AsyncSession) -> dict[str, Any]:
    user = await get_user_by_username(auth_data.username, session)
    if not user:
        raise InvalidCredentials()

    if not check_password(auth_data.password, user.password):
        raise InvalidCredentials()

    return user


async def create_password_reset_token(user_id: int, token: str) -> None:
    expires_at = datetime.utcnow() + timedelta(minutes=30)
    await execute(
        insert(PasswordResetToken).values(
            token=token,
            user_id=user_id,
            expires_at=expires_at,
        )
    )

async def get_password_reset_token(token: str) -> dict[str, Any] | None:
    return await fetch_one(
        select(PasswordResetToken).where(
            PasswordResetToken.token == token,
            PasswordResetToken.expires_at > datetime.utcnow(),
        )
    )

async def expire_password_reset_token(token: str) -> None:
    from sqlalchemy import delete
    from src.database import engine
    async with engine.begin() as conn:
        await conn.execute(
            delete(PasswordResetToken.__table__).where(PasswordResetToken.token == token)
        )

async def update_user_password(user_id: int, new_password: str, session: AsyncSession) -> None:
    from sqlalchemy import update
    from .security import hash_password
    await session.execute(
        update(User)
        .where(User.id == user_id)
        .values(password=hash_password(new_password))
    )
    await session.commit()
