from typing import Any

from fastapi import APIRouter, Depends, status, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import validate_admin_access, validate_customer_access, parse_jwt_user_data
from src.database import get_async_session
from src.models import User
from src.services.schemas import ServiceResponse, ServiceCreateInput, ServiceCreateByAdminInput, ServiceAssignInput
from src.services import service as services

router = APIRouter()


@router.post("/create_by_admin", status_code=status.HTTP_201_CREATED, response_model=ServiceResponse,
             dependencies=[Depends(validate_admin_access)])
async def create_new_service_by_admin(
        service_data: ServiceCreateByAdminInput,
        session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:
    new_service = await services.create_new_service_by_admin(service_data.customer_id, service_data, session)

    if not new_service:
        raise HTTPException(status_code=400, detail="Ошибка создания заявки")

    return new_service


@router.post("/create", status_code=status.HTTP_201_CREATED, response_model=ServiceResponse,
             dependencies=[Depends(validate_customer_access)])
async def create_new_service(
        service_data: ServiceCreateInput,
        session: AsyncSession = Depends(get_async_session),
        current_user: User = Depends(parse_jwt_user_data)
) -> dict[str, Any]:

    customer_id = int(current_user.user_id)
    new_service = await services.create_new_service_by_customer(customer_id, service_data, session)

    if not new_service:
        raise HTTPException(status_code=400, detail="Ошибка создания заявки")

    return new_service


@router.post("/assign", status_code=status.HTTP_200_OK, response_model=ServiceResponse,
             dependencies=[Depends(validate_admin_access)])
async def assign_executor(
        assign_data: ServiceAssignInput,
        session: AsyncSession = Depends(get_async_session)
) -> dict[str, Any]:

    attached_service = await services.assign_executor_to_service(assign_data, session)

    if not attached_service:
        raise HTTPException(status_code=400, detail="Ошибка выдачи заявки")

    return attached_service
