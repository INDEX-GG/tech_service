import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import (
    Boolean,
    Column,
    CursorResult,
    DateTime,
    ForeignKey,
    Identity,
    Insert,
    Integer,
    Select,
    String,
    Table,
    Update,
    func,
    Enum as EnumSQL
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from src.database import Base, engine
from enum import Enum


from zoneinfo import ZoneInfo

from fastapi.encoders import jsonable_encoder
from pydantic import BaseModel, ConfigDict, model_validator


def convert_datetime_to_gmt(dt: datetime) -> str:
    if not dt.tzinfo:
        dt = dt.replace(tzinfo=ZoneInfo("UTC"))

    return dt.strftime("%Y-%m-%dT%H:%M:%S%z")


class CustomModel(BaseModel):
    model_config = ConfigDict(
        json_encoders={datetime: convert_datetime_to_gmt},
        populate_by_name=True,
    )

    @model_validator(mode="before")
    # @classmethod
    # def set_null_microseconds(cls, data: dict[str, Any]) -> dict[str, Any]:
    #     if data is not None:
    #         datetime_fields = {
    #             k: v.replace(microsecond=0)
    #             for k, v in data.items()
    #             if isinstance(k, datetime)
    #         }
    #
    #         return {**data, **datetime_fields}
    #     return data
    def serializable_dict(self, **kwargs):
        """Return a dict which contains only serializable fields."""
        # default_dict = self.model_dump()

        return jsonable_encoder(self)


class ServiceStatus(Enum):
    NEW = "Новая"
    WORKING = "В работе"
    VERIFYING = "Контроль качества"
    CLOSED = "Закрыта"
    CUSTOM = "Заказная позиция"


class FileTypes(Enum):
    IMAGE = "Изображение"
    VIDEO = "Видео"


class OwnerTypes(Enum):
    CUSTOMER = "Заказчик"
    EXECUTOR = "Исполнитель"


class Service(Base):
    """Модель заявок"""
    __tablename__ = "services"
    __table_args__ = {"schema": "public"}
    id = Column("id", UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    customer_id = Column("customer_id", Integer, ForeignKey("public.users.id"), nullable=False, index=True)
    executor_id = Column("executor_id", Integer, ForeignKey("public.users.id"), index=True)
    title = Column("title", String, nullable=False)
    description = Column("description", String)
    material_availability = Column("material_availability", Boolean, server_default="false", nullable=False)
    emergency = Column("emergency", Boolean, server_default="false", nullable=False)
    created_at = Column("created_at", DateTime, server_default=func.now(), nullable=False)
    updated_at = Column("updated_at", DateTime, onupdate=func.now())
    deadline_at = Column("deadline_at", DateTime, server_default=func.now(), nullable=False)

    comment = Column("comment", String)
    status = Column("status", EnumSQL(ServiceStatus), nullable=False, default=ServiceStatus.NEW)
    media_files = relationship("MediaFiles", back_populates="service", cascade="all, delete-orphan")

    customer = relationship("User", foreign_keys=[customer_id], back_populates="customer_services", single_parent=True, uselist=False)
    executor = relationship("User", foreign_keys=[executor_id], back_populates="executor_services", single_parent=True, uselist=False)


class User(Base):
    """Модель пользователей"""
    __tablename__ = "users"
    __table_args__ = {"schema": "public"}
    id = Column("id", Integer, primary_key=True, index=True, autoincrement=True, unique=True, nullable=False)
    username = Column("username", String, unique=True, index=True)
    password = Column("password", String)
    is_active = Column("is_active", Boolean, server_default="false", nullable=False)
    is_admin = Column("is_admin", Boolean, server_default="false", nullable=False)
    is_customer = Column("is_customer", Boolean, server_default="false", nullable=False)
    is_executor = Column("is_executor", Boolean, server_default="false", nullable=False)
    name = Column("name", String, nullable=True)
    phone = Column("phone", String, nullable=True)
    created_at = Column("created_at", DateTime, server_default=func.now(), nullable=False)
    updated_at = Column("updated_at", DateTime, onupdate=func.now())
    customer_company = relationship("Company", back_populates="customer", cascade="all, delete-orphan", uselist=False)
    customer_services = relationship("Service", foreign_keys=[Service.customer_id], back_populates="customer", cascade="all, delete-orphan")
    executor_services = relationship("Service", foreign_keys=[Service.executor_id], back_populates="executor", cascade="all, delete-orphan")


class RefreshTokens(Base):
    """Модель пользователей"""
    __tablename__ = "auth_refresh_token"
    __table_args__ = {"schema": "public"}
    uuid = Column("uuid", UUID, primary_key=True)
    user_id = Column("user_id", Integer, ForeignKey("public.users.id"))
    refresh_token = Column("refresh_token", String, nullable=False)
    expires_at = Column("expires_at", DateTime, nullable=False)
    created_at = Column("created_at", DateTime, server_default=func.now(), nullable=False)
    updated_at = Column("updated_at", DateTime, onupdate=func.now())


class MediaFiles(Base):
    """Модель заявок"""
    __tablename__ = "media_files"
    __table_args__ = {"schema": "public"}
    id = Column("id", UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    service_id = Column("service_id", UUID(as_uuid=True), ForeignKey("public.services.id"), nullable=False, index=True)
    file_type = Column("file_type", EnumSQL(FileTypes), nullable=False)
    owner_type = Column("owner_type", EnumSQL(OwnerTypes), nullable=False)
    url = Column("url", String, nullable=False)
    service = relationship("Service", back_populates="media_files")


class Company(Base):
    """Модель заявок"""
    __tablename__ = "company"
    __table_args__ = {"schema": "public"}
    id = Column("id", UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    user_id = Column("user_id", Integer, ForeignKey("public.users.id"), nullable=False, index=True)
    name = Column("name", String, nullable=False)
    address = Column("address", String, nullable=True)
    opening_time = Column("opening_time", String, nullable=True)
    closing_time = Column("closing_time", String, nullable=True)
    only_weekdays = Column("only_weekdays", Boolean, server_default="false", nullable=False)
    contacts = relationship("CompanyContacts", back_populates="company")
    customer = relationship("User", back_populates="customer_company", single_parent=True)


class CompanyContacts(Base):
    """Модель заявок"""
    __tablename__ = "company_contacts"
    __table_args__ = {"schema": "public"}
    id = Column("id", UUID(as_uuid=True), primary_key=True, index=True, default=uuid.uuid4)
    company_id = Column("company_id", UUID(as_uuid=True), ForeignKey("public.company.id"), nullable=False, index=True)
    phone = Column("phone", String, nullable=False)
    person = Column("person", String, nullable=True)
    company = relationship("Company", back_populates="contacts")


async def fetch_one(select_query: Select | Insert | Update) -> dict[str, Any] | None:
    async with engine.begin() as conn:
        cursor: CursorResult = await conn.execute(select_query)
        return cursor.first()._asdict() if cursor.rowcount > 0 else None


async def fetch_all(select_query: Select | Insert | Update) -> list[dict[str, Any]]:
    async with engine.begin() as conn:
        cursor: CursorResult = await conn.execute(select_query)
        return [r._asdict() for r in cursor.all()]


async def execute(select_query: Insert | Update) -> None:
    async with engine.begin() as conn:
        await conn.execute(select_query)
