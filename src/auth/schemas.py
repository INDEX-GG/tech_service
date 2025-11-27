import re
from pydantic import EmailStr, Field, field_validator
from src.models import CustomModel, Roles

# Разрешённые спецсимволы — можно настроить
SPECIAL_CHARS = "!@#$%^&*()_+-=[]{}|;:,.<>?"


class AuthUser(CustomModel):
    username: EmailStr = Field(min_length=3, max_length=128)
    password: str = Field(min_length=8, max_length=30)

    @field_validator("password", mode="after")
    @classmethod
    def valid_password(cls, v: str) -> str:
        escaped = re.escape(SPECIAL_CHARS)

        if not re.fullmatch(rf"[a-zA-Z0-9{escaped}]+", v):
            raise ValueError(f"Разрешены только английские буквы, цифры и следующие спецсимволы: {SPECIAL_CHARS}")

        if not re.search(r"[a-zA-Z]", v):
            raise ValueError("Пароль должен содержать хотя бы одну английскую букву.")

        if not re.search(r"[0-9]", v):
            raise ValueError("Пароль должен содержать хотя бы одну цифру.")

        if not re.search(rf"[{escaped}]", v):
            raise ValueError(f"Пароль должен содержать хотя бы один из следующих спецсимволов: {SPECIAL_CHARS}")

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