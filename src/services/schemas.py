from datetime import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import UploadFile, File
from pydantic import BaseModel

from src.models import CustomModel, ServiceStatus, FileTypes, OwnerTypes
from src.users.schemas import CustomerUserResponse, ExecutorUserResponse


class ServiceCreateByAdminInput(CustomModel):
    customer_id: int
    executor_id: int | None = None
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
    deadline_at: datetime | None


class MediaFilesResponse(BaseModel):
    id: UUID
    file_type: FileTypes
    owner_type: OwnerTypes


class ServiceResponse(CustomModel):
    id: UUID
    customer_id: int
    executor_id: int | None
    title: str
    description: str | None
    material_availability: bool | None
    emergency: bool | None
    custom_position: bool | None
    created_at: datetime
    deadline_at: datetime | None
    status: ServiceStatus
    comment: str | None
    customer: CustomerUserResponse
    executor: ExecutorUserResponse | None = None
    media_files: List[MediaFilesResponse] | None = None


class ServiceAssignInput(CustomModel):
    service_id: UUID
    executor_id: int
    deadline_at: datetime | None
    comment: str | None = None
    emergency: bool | None = None
    custom_position: bool | None = None


class VideoAndImageInput(BaseModel):
    video_file: Optional[UploadFile] = File(None)
    image_files: Optional[List[UploadFile]] = File(None)


class BadgeServicesResponse(CustomModel):
    mark: bool
    counter: int


class TabsServicesResponse(CustomModel):
    new: int
    working: int
    verifying: int
    closed: int


class CompaniesListedResponse(CustomModel):
    id: UUID
    name: str
    address: str
    badge: BadgeServicesResponse
    tabs: TabsServicesResponse


class CompaniesListPaginated(CustomModel):
    total: int
    items: List[CompaniesListedResponse]


class ExecutorModel(CustomModel):
    name: str | None


class ServiceListedResponse(CustomModel):
    id: UUID
    title: str
    emergency: bool
    custom_position: bool
    viewed_admin: bool
    viewed_customer: bool
    viewed_executor: bool
    status: ServiceStatus
    created_at: datetime
    # updated_at: datetime | None = None
    deadline_at: datetime | None = None
    # executor: ExecutorModel | None = None


class ServicesListPaginated(CustomModel):
    total: int
    counter: int
    items: List[ServiceListedResponse]


class CustomerServicesListPaginated(CustomModel):
    total: int
    counter: int
    items: List[ServiceListedResponse]


class ServiceUpdateInput(CustomModel):
    service_id: UUID
    executor_id: int | None
    title: str | None
    description: str | None
    material_availability: bool | None
    emergency: bool | None
    deadline_at: datetime | None
    custom_position: bool | None
    comment: str | None
