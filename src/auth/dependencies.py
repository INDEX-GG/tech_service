from datetime import datetime
from typing import Any

from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer

from src.auth import service
from src.auth.exceptions import UsernameTaken, RefreshTokenNotValid
from src.auth.schemas import AuthUser


oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/v2/auth/tokens", auto_error=False)


async def valid_user_create(user: AuthUser) -> AuthUser:
    if await service.get_user_by_username(user.username):
        raise UsernameTaken()

    return user


async def valid_refresh_token(
    # refresh_token: str = Cookie(..., alias="refreshToken"),
    refresh_token: str = Depends(oauth2_scheme)
) -> dict[str, Any]:
    db_refresh_token = await service.get_refresh_token(refresh_token)
    if not db_refresh_token:
        raise RefreshTokenNotValid()

    if not _is_valid_refresh_token(db_refresh_token):
        raise RefreshTokenNotValid()

    return db_refresh_token


async def valid_refresh_token_user(
    refresh_token: dict[str, Any] = Depends(valid_refresh_token),
) -> dict[str, Any]:
    user = await service.get_user_by_id(refresh_token["user_id"])
    if not user:
        raise RefreshTokenNotValid()

    return user


def _is_valid_refresh_token(db_refresh_token: dict[str, Any]) -> bool:
    return datetime.utcnow() <= db_refresh_token["expires_at"]
