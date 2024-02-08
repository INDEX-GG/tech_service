import datetime
from typing import Any

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Service, ServiceStatus, User, Company
from src.services.schemas import ServiceCreateInput, ServiceCreateByAdminInput
from src.users.service import get_user_profile_by_id, get_user_by_role


async def create_new_service_by_admin(customer_id: int, service_data: ServiceCreateByAdminInput, session: AsyncSession) -> dict[str, Any] | None:
    try:
        if customer_id == service_data.executor_id:
            raise ValueError("Вы не можете назначить исполнение заявки заказчику")

        new_service = Service(
            customer_id=customer_id,
            executor_id=service_data.executor_id,
            title=service_data.title,
            description=service_data.description,
            material_availability=service_data.material_availability,
            emergency=service_data.emergency,
            custom_position=service_data.custom_position,
            deadline_at=service_data.deadline_at,
            comment=service_data.comment,
            status=ServiceStatus.NEW,
            # media_files=,
        )

        # customer = await session.execute(select(User).filter(User.id == customer_id))
        # customer = await customer.scalar_one_or_none()
        # new_service.customer = customer

        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)

        customer = await get_user_profile_by_id(customer_id, session)
        new_service.customer = customer

        if service_data.executor_id:
            executor = await get_user_by_role(service_data.executor_id, "is_executor", session)
            new_service.executor = executor

        # TODO: JOIN MEDIA_FILES TO RESPONSE

        return new_service

    except Exception as e:
        # Обработка ошибок
        print(f"Error creating service by admin: {e}")
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # закрыть сессию после выполнения операций
        await session.close()


async def create_new_service_by_customer(customer_id: int, service_data: ServiceCreateInput, session: AsyncSession) -> dict[str, Any] | None:
    try:
        new_service = Service(
            customer_id=customer_id,
            title=service_data.title,
            description=service_data.description,
            material_availability=service_data.material_availability,
            emergency=service_data.emergency,
            deadline_at=service_data.deadline_at,
            status=ServiceStatus.NEW,
            # media_files=,
        )

        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)

        customer = await get_user_profile_by_id(customer_id, session)
        new_service.customer = customer

        # TODO: JOIN MEDIA_FILES TO RESPONSE

        return new_service

    except Exception as e:
        # Обработка ошибок
        print(f"Error creating service by customer: {e}")
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка создания заявки")
    finally:
        # закрыть сессию после выполнения операций
        await session.close()


async def assign_executor_to_service(assign_data, session: AsyncSession):
    try:
        select_query = (select(Service)
                        .options(selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                        .options(selectinload(Service.executor))
                        .where(Service.id == assign_data.service_id)
                        )
        model = await session.execute(select_query)
        service = model.scalar_one_or_none()

        service.executor_id = assign_data.executor_id
        service.status = ServiceStatus.WORKING
        await session.commit()
        await session.refresh(service)

        # TODO: JOIN MEDIA_FILES TO RESPONSE

        return service

    except Exception as e:
        # Обработка ошибок
        print(f"Error assigning service to executor: {e}")
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка назначения заявки")
    finally:
        # закрыть сессию после выполнения операций
        await session.close()


