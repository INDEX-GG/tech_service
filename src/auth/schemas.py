import re
from fastapi import HTTPException, status
from pydantic import BaseModel, Field, field_validator
from src.models import CustomModel, Roles


SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


class AuthUser(CustomModel):
    username: str
    password: str

    @field_validator("username")
    @classmethod
    def validate_email(cls, v: str) -> str:
        if not re.match(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$", v):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Некорректный адрес электронной почты."
            )
        return v

    @field_validator("password", mode="after")
    @classmethod
    def valid_password(cls, v: str) -> str:
        if len(v) < 8:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Пароль должен содержать не менее 8 символов."
            )
        if len(v) > 30:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Пароль должен содержать не более 30 символов."
            )

        escaped = re.escape(SPECIAL_CHARS)

        if not re.fullmatch(rf"[a-zA-Z0-9{escaped}]+", v):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Разрешены только английские буквы, цифры и следующие спецсимволы: {SPECIAL_CHARS}"
            )

        if not re.search(r"[a-zA-Z]", v):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Пароль должен содержать хотя бы одну английскую букву."
            )

        if not re.search(r"[0-9]", v):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Пароль должен содержать хотя бы одну цифру."
            )

        if not re.search(rf"[{escaped}]", v):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=f"Пароль должен содержать хотя бы один из следующих спецсимволов: {SPECIAL_CHARS}"
            )

        return v


class JWTData(CustomModel):
    user_id: int = Field(alias="sub")
    is_active: bool = False
    is_admin: bool = False
    is_executor: bool = False
    is_customer: bool = False
    role: Roles | None


class AccessTokenResponse(CustomModel):
    access_token: str
    refresh_token: str


class RegisterUserResponse(CustomModel):
    username: str