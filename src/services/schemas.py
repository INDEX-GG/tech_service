from datetime import datetime
from typing import List
from uuid import UUID

from src.models import CustomModel, ServiceStatus


class ServiceCreateByAdminInput(CustomModel):
    customer_id: int
    executor_id: int = None
    title: str
    description: str | None
    material_availability: bool
    emergency: bool
    custom_position: bool
    deadline_at: datetime | None
    comment: str | None
    # media_files:


class ServiceCreateInput(CustomModel):
    title: str
    description: str | None
    material_availability: bool
    emergency: bool
    deadline_at: datetime
    # media_files:


class ServiceResponse(CustomModel):
    id: UUID
    customer_id: int
    executor_id: int | None
    title: str
    description: str | None
    material_availability: bool
    emergency: bool
    custom_position: bool
    created_at: datetime
    deadline_at: datetime | None
    status: ServiceStatus
    comment: str | None
    # media_files:
    # customer: CustomerUserResponse
    # executor: ExecutorUserResponse | None


class ServiceAssignInput(CustomModel):
    service_id: UUID
    executor_id: int
