from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth import jwt, service
from src.auth.dependencies import (
    valid_refresh_token,
    valid_refresh_token_user,
    valid_user_create,
)
from src.auth.email import send_password_reset_email
from src.auth.exceptions import InvalidCredentials
from src.auth.rate_limiter import is_password_reset_allowed
from src.auth.schemas import AccessTokenResponse, AuthUser, RegisterUserResponse, ForgotPasswordRequest, \
    ResetPasswordRequest
from src.database import get_async_session
from src.utils import generate_random_alphanum

router = APIRouter()


@router.post("/register", status_code=status.HTTP_201_CREATED, response_model=RegisterUserResponse)
async def register_user(
       auth_data: AuthUser = Depends(valid_user_create),
) -> dict[str, str]:
   user = await service.create_user(auth_data)
   return {
       "username": user["username"],
   }


@router.post("/tokens", response_model=AccessTokenResponse)
async def auth_user(
        form_data: OAuth2PasswordRequestForm = Depends(),
        session: AsyncSession = Depends(get_async_session)
) -> AccessTokenResponse:
    user = await service.authenticate_user(form_data, session)
    refresh_token_value = await service.create_refresh_token(user_id=user.id)

    return AccessTokenResponse(
        access_token=jwt.create_access_token(user=user),
        refresh_token=refresh_token_value,
    )


@router.put("/tokens", response_model=AccessTokenResponse)
async def refresh_tokens(
        worker: BackgroundTasks,
        refresh_token: dict[str, Any] = Depends(valid_refresh_token),
        user: dict[str, Any] = Depends(valid_refresh_token_user),
) -> AccessTokenResponse:
    refresh_token_value = await service.create_refresh_token(
        user_id=refresh_token["user_id"]
    )

    worker.add_task(service.expire_refresh_token, refresh_token["uuid"])
    return AccessTokenResponse(
        access_token=jwt.create_access_token(user=user),
        refresh_token=refresh_token_value,
    )


@router.delete("/tokens")
async def logout_user(
        refresh_token: dict[str, Any] = Depends(valid_refresh_token),
) -> None:
    await service.expire_refresh_token(refresh_token["uuid"])

@router.post("/forgot-password", status_code=202)
async def forgot_password(
    request: ForgotPasswordRequest,
    background_tasks: BackgroundTasks,
    session: AsyncSession = Depends(get_async_session),
):
    user = await service.get_user_by_username(request.username, session)
    if not user:
        return {"msg": "Если пользователь существует, ссылка будет отправлена."}

    if not is_password_reset_allowed(user.username):
        return {"msg": "Подождите 5 минут до следующей попытки ."}

    token = await service.generate_unique_code()
    await service.create_password_reset_token(user.id, token)

    background_tasks.add_task(
        send_password_reset_email,
        to_email=user.username,
        token=token,
    )

    return {"msg": "Если пользователь существует, ссылка будет отправлена."}

@router.post("/reset-password")
async def reset_password(
    request: ResetPasswordRequest,
    session: AsyncSession = Depends(get_async_session),
):
    token_data = await service.get_password_reset_token(request.token)
    if not token_data:
        raise InvalidCredentials()

    await service.update_user_password(token_data["user_id"], request.new_password, session)

    await service.expire_password_reset_token(request.token)

    return {"msg": "Пароль успешно обновлен."}