from typing import Any, List
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, update, func, and_, desc, exists, case, asc, delete, or_
from sqlalchemy.exc import NoResultFound
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from src.models import Service, ServiceStatus, User, Company, OwnerTypes, Roles
from src.services.schemas import ServiceCreateInput, ServiceCreateByAdminInput, ServiceUpdateInput
from src.users.service import get_user_profile_by_id, get_user_by_role, get_user_executor_default
from src.media import service as media_service


async def create_new_service_by_admin(
        customer_id: int,
        service_data: ServiceCreateByAdminInput,
        video_file: UploadFile,
        image_files: List[UploadFile],
        session: AsyncSession
) -> dict[str, Any] | None:
    try:
        if customer_id in [service_data.executor_default_id, service_data.executor_additional_id]:
            raise ValueError("Вы не можете назначить исполнение заявки заказчику")

        customer = await get_user_profile_by_id(customer_id, session)

        executor_default = customer.customer_company.executor_default_id
        executor_default_id = executor_default if service_data.executor_default_id is None else service_data.executor_default_id

        executor_additional = customer.customer_company.executor_additional_id
        executor_additional_id = executor_additional if service_data.executor_additional_id is None else service_data.executor_additional_id

        new_service = Service(
            customer_id=customer_id,
            executor_default_id=executor_default_id,
            executor_additional_id=executor_additional_id,
            company_id=customer.customer_company.id,
            title=service_data.title,
            description=service_data.description,
            material_availability=service_data.material_availability,
            emergency=service_data.emergency,
            custom_position=service_data.custom_position,
            viewed_admin=True,
            deadline_at=service_data.deadline_at,
            updated_at=func.now(),
            comment=service_data.comment,
            status=ServiceStatus.WORKING
        )

        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)

        new_service.customer = customer

        executor = await get_user_by_role(executor_default_id, "is_executor", session)
        new_service.executor_default = executor

        if executor_additional_id:
            executor = await get_user_by_role(executor_additional_id, "is_executor", session)
            new_service.executor_additional = executor

        owner_type = OwnerTypes.CUSTOMER

        if video_file:
            uploaded_video = await media_service.save_video(video_file=video_file, service_id=new_service.id,
                                                            owner_type=owner_type)
            if not uploaded_video:
                raise ValueError("Ошибка загрузки видео")

        if image_files:
            uploaded_image = await media_service.save_images(image_files=image_files, service_id=new_service.id,
                                                             owner_type=owner_type)
            if not uploaded_image:
                raise ValueError("Ошибка загрузки фото")

        media_files = await get_media_files_by_service_id(new_service.id, session)
        new_service.media_files = media_files

        return new_service

    except Exception as e:
        # Обработка ошибок
        print(f"Error creating service by admin: {e}")
        await session.rollback()
        raise HTTPException(status_code=400, detail=str(e))
    finally:
        # закрыть сессию после выполнения операций
        await session.close()


async def create_new_service_by_customer(
        customer_id: int,
        service_data: ServiceCreateInput,
        video_file: UploadFile,
        image_files: List[UploadFile],
        session: AsyncSession
) -> dict[str, Any] | None:
    try:
        customer = await get_user_profile_by_id(customer_id, session)
        executor_default_id = customer.customer_company.executor_default_id
        executor_additional_id = customer.customer_company.executor_additional_id

        new_service = Service(
            customer_id=customer_id,
            company_id=customer.customer_company.id,
            title=service_data.title,
            description=service_data.description,
            material_availability=service_data.material_availability,
            emergency=service_data.emergency,
            viewed_customer=True,
            deadline_at=service_data.deadline_at,
            executor_default_id=executor_default_id,
            executor_additional_id=executor_additional_id,
            updated_at=func.now(),
            status=ServiceStatus.WORKING
        )

        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)

        new_service.customer = customer

        executor = await get_user_by_role(executor_default_id, "is_executor", session)
        new_service.executor_default = executor

        if executor_additional_id:
            executor = await get_user_by_role(executor_additional_id, "is_executor", session)
            new_service.executor_additional = executor

        owner_type = OwnerTypes.CUSTOMER

        if video_file:
            uploaded_video = await media_service.save_video(video_file=video_file, service_id=new_service.id,
                                                            owner_type=owner_type)
            if not uploaded_video:
                raise ValueError("Ошибка загрузки видео")

        if image_files:
            uploaded_image = await media_service.save_images(image_files=image_files, service_id=new_service.id,
                                                             owner_type=owner_type)
            if not uploaded_image:
                raise ValueError("Ошибка загрузки фото")

        media_files = await get_media_files_by_service_id(new_service.id, session)
        new_service.media_files = media_files

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
                        .options(
            selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                        .options(
            selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.executor_default))
                        .options(selectinload(Service.customer).selectinload(User.customer_company).selectinload(
            Company.executor_additional))
                        .options(selectinload(Service.executor_additional))
                        .options(selectinload(Service.executor_default))
                        .options(selectinload(Service.media_files))
                        .where(Service.id == assign_data.service_id)
                        )
        model = await session.execute(select_query)
        service = model.scalar_one_or_none()

        if service.status not in [ServiceStatus.WORKING, ServiceStatus.VERIFYING]:
            raise HTTPException(status_code=400, detail="Возможно изменять заявки "
                                                        "находящиеся только в работа и контроле качества")

        if assign_data.executor_default_id not in [False, None]:
            service.executor_default_id = assign_data.executor_default_id
        if assign_data.executor_additional_id is not False:
            service.executor_additional_id = assign_data.executor_additional_id

        service.status = ServiceStatus.VERIFYING if assign_data.is_edit else ServiceStatus.WORKING
        if not service.viewed_admin:
            service.viewed_admin = True
        service.viewed_customer = False
        service.viewed_executor_default = False
        service.viewed_executor_additional = False

        service.deadline_at = assign_data.deadline_at.replace(tzinfo=None) if assign_data.deadline_at else None
        service.comment = assign_data.comment if assign_data.comment else None

        if assign_data.emergency is not None:
            service.emergency = assign_data.emergency
        if assign_data.custom_position is not None:
            service.custom_position = assign_data.custom_position

        await session.commit()
        session.expire(service)
        await session.refresh(service)

        return service

    except Exception as e:
        # Обработка ошибок
        print(f"Error assigning service to executor: {e}")
        await session.rollback()
        raise HTTPException(status_code=400, detail=f"Ошибка назначения заявки")
    finally:
        # закрыть сессию после выполнения операций
        await session.close()


async def get_media_files_by_service_id(service_id: UUID, session: AsyncSession):
    select_query = (
        select(Service).where(Service.id == service_id)
        .options(selectinload(Service.media_files))
    )
    model = await session.execute(select_query)
    service = model.scalar_one_or_none()
    media_files = service.media_files
    return media_files


async def get_service_executor_id(service_id: UUID, session: AsyncSession):
    select_query = select(Service).where(Service.id == service_id)
    model = await session.execute(select_query)
    service = model.scalar_one_or_none()
    service_executor_default_id = service.executor_default_id
    service_executor_additional_id = service.executor_additional_id
    service_status = service.status

    return service_executor_default_id, service_executor_additional_id, service_status


async def mark_service_verifying(service_id: UUID, default_executor_id,
                                 additional_executor_id, user_id, session: AsyncSession):
    try:
        # Update the Service status to VERIFYING
        update_query = (
            update(Service)
            .where(Service.id == service_id)
            .values(
                status=ServiceStatus.VERIFYING,
                viewed_admin=False,
                viewed_customer=False,
                viewed_executor_default=True if default_executor_id == user_id else False,
                viewed_executor_additional=True if additional_executor_id == user_id else False,
            )
        )
        await session.execute(update_query)

        # Commit the changes to the database
        await session.commit()

        return True
    except Exception as e:
        # Handle exceptions appropriately
        await session.rollback()
        print(f"Error marking service as verifying: {e}")
        return False

    finally:
        # Close the session
        await session.close()


async def get_service_card_by_id(service_id: UUID, role: Roles, user_id: int, session: AsyncSession):
    select_query = (select(Service)
                    .options(
        selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                    .options(
        selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.executor_default))
                    .options(
        selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.executor_additional))
                    .options(selectinload(Service.executor_default))
                    .options(selectinload(Service.executor_additional))
                    .options(selectinload(Service.media_files))
                    .where(Service.id == service_id)
                    )
    model = await session.execute(select_query)
    service = model.scalar_one_or_none()

    if role == Roles.ADMIN:
        if not service.viewed_admin:
            service.viewed_admin = True
            await session.commit()
            await session.refresh(service)
    elif role == Roles.CUSTOMER:
        if not service.viewed_customer:
            service.viewed_customer = True
            await session.commit()
            await session.refresh(service)
    elif role == Roles.EXECUTOR:
        if not service.viewed_executor_default and service.executor_default_id == user_id:
            service.viewed_executor_default = True
            await session.commit()
            await session.refresh(service)
        if not service.viewed_executor_additional and service.executor_additional_id == user_id:
            service.viewed_executor_additional = True
            await session.commit()
            await session.refresh(service)

    return service


async def make_service_closed(service_id: UUID, session: AsyncSession):
    try:
        select_query = (select(Service)
                        .options(
            selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                        .options(
            selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.executor_default))
                        .options(selectinload(Service.customer).selectinload(User.customer_company).selectinload(
            Company.executor_additional))
                        .options(selectinload(Service.executor_additional))
                        .options(selectinload(Service.executor_default))
                        .options(selectinload(Service.media_files))
                        .where(Service.id == service_id)
                        )
        model = await session.execute(select_query)
        service = model.scalar_one_or_none()

        service.status = ServiceStatus.CLOSED

        service.viewed_admin = True
        service.viewed_customer = False
        service.viewed_executor_default = False
        service.viewed_executor_additional = False

        await session.commit()
        await session.refresh(service)

        return service

    except Exception as e:
        # Обработка ошибок
        await session.rollback()
        raise HTTPException(status_code=400, detail="Ошибка закрытия заявки")
    finally:
        # закрыть сессию после выполнения операций
        await session.close()


async def make_service_refused(service_id: UUID, session: AsyncSession):
    try:
        select_query = (select(Service)
                        .options(
            selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                        .options(
            selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.executor_default))
                        .options(selectinload(Service.customer).selectinload(User.customer_company).selectinload(
            Company.executor_additional))
                        .options(selectinload(Service.executor_additional))
                        .options(selectinload(Service.executor_default))
                        .options(selectinload(Service.media_files))
                        .where(Service.id == service_id)
                        )
        model = await session.execute(select_query)
        service = model.scalar_one_or_none()

        if service.status not in [ServiceStatus.WORKING]:
            raise HTTPException(status_code=400, detail="Возможность отклонения заявки доступна "
                                                        "только для заявок, находящихся в работе")
        service.status = ServiceStatus.REFUSED

        service.viewed_admin = True
        service.viewed_customer = False
        service.viewed_executor_default = False
        service.viewed_executor_additional = False

        await session.commit()
        await session.refresh(service)

        return service

    except Exception as e:
        # Обработка ошибок
        await session.rollback()
        raise HTTPException(status_code=400, detail="Ошибка отклонения заявки")
    finally:
        # закрыть сессию после выполнения операций
        await session.close()


async def get_all_companies_with_services_info(page: int, limit: int, session: AsyncSession, executor_id: int = None):
    offset = (page - 1) * limit

    # получаем id компании у активных организаций
    active_customer_subquery = (
        select(Company.id)
        .join(Company.customer)
        .where(Company.customer.has(is_active=True))
        .distinct()
    )

    # Получаем количество заявок
    if executor_id:
        count_query = (
            select(func.count())
            .select_from(Company)
            .where(exists().where(
                and_(
                    Service.company_id == Company.id,
                    or_(Service.executor_default_id == executor_id, Service.executor_additional_id == executor_id),
                    Company.id.in_(active_customer_subquery)
                )
            ))
        )

        query = (
            select(
                Company,
                func.sum(case((and_(
                    Service.status == ServiceStatus.WORKING,
                    or_(
                        and_(
                            Service.executor_default_id == executor_id,
                            Service.viewed_executor_default == False
                        ),
                        and_(
                            Service.executor_additional_id == executor_id,
                            Service.viewed_executor_additional == False
                        ),
                    )
                ), 1), else_=0)).label("working"),

                func.sum(case((and_(
                    Service.status == ServiceStatus.VERIFYING,
                    or_(
                        and_(
                            Service.executor_default_id == executor_id,
                            Service.viewed_executor_default == False
                        ),
                        and_(
                            Service.executor_additional_id == executor_id,
                            Service.viewed_executor_additional == False
                        )
                    )
                ), 1), else_=0)).label("verifying"),

                func.sum(case((and_(
                    Service.status == ServiceStatus.CLOSED,
                    or_(
                        and_(
                            Service.executor_default_id == executor_id,
                            Service.viewed_executor_default == False
                        ),
                        and_(
                            Service.executor_additional_id == executor_id,
                            Service.viewed_executor_additional == False,
                        )
                    )
                ), 1), else_=0)).label("closed"),

                func.sum(case((and_(
                    Service.status == ServiceStatus.REFUSED,
                    or_(
                        and_(
                            Service.executor_default_id == executor_id,
                            Service.viewed_executor_default == False
                        ),
                        and_(
                            Service.executor_additional_id == executor_id,
                            Service.viewed_executor_additional == False,
                        )
                    )
                ), 1), else_=0)).label("refused"),

            )
            .join(Service)  # Внутреннее соединение, чтобы выбрать только компании с сервисами
            .where(and_(
                or_(Service.executor_default_id == executor_id, Service.executor_additional_id == executor_id),
                Company.id.in_(active_customer_subquery)
            ))
            .options(selectinload(Company.services))
            .group_by(Company.id)  # Группируем по компании
            .order_by(desc(func.max(Service.updated_at)))  # Сортируем по дате обновления первого сервиса
            .offset(offset)
            .limit(limit)
        )

    else:
        count_query = (
            select(func.count())
            .select_from(Company)
            .where(exists().where(
                and_(
                    Service.company_id == Company.id,
                    Company.id.in_(active_customer_subquery)
                ))
            )
        )

        query = (
            select(
                Company,
                func.sum(case((and_(Service.status == ServiceStatus.WORKING, Service.viewed_admin == False), 1),
                              else_=0)).label("working"),
                func.sum(case((and_(Service.status == ServiceStatus.VERIFYING, Service.viewed_admin == False), 1),
                              else_=0)).label("verifying"),
                func.sum(case((and_(Service.status == ServiceStatus.CLOSED, Service.viewed_admin == False), 1),
                              else_=0)).label("closed"),
                func.sum(case((and_(Service.status == ServiceStatus.REFUSED, Service.viewed_admin == False), 1),
                              else_=0)).label("refused")
            )
            .join(Service)  # Внутреннее соединение, чтобы выбрать только компании с сервисами
            .where(and_(
                Company.id.in_(active_customer_subquery)
            ))
            .options(selectinload(Company.services))
            .group_by(Company.id)  # Группируем по компании
            .order_by(desc(func.max(Service.updated_at)))  # Сортируем по дате обновления первого сервиса
            .offset(offset)
            .limit(limit)
        )

    #######################################################################
    total_records = await session.execute(count_query)
    total = total_records.scalar()

    # Выполняем запрос и Получаем все объекты Company из результата
    result = await session.execute(query)
    companies_with_tabs = result.all()

    response = []

    for company_with_tabs in companies_with_tabs:
        company = company_with_tabs[0]
        counter = company.new_services_count(executor_id)

        company_object = {
            "id": company.id,
            "name": company.name,
            "address": company.address,
            "badge": {
                "counter_working": counter['working'],
                "counter_verifying": counter['verifying']
            },
            "tabs": {
                "working": company_with_tabs.working,
                "verifying": company_with_tabs.verifying,
                "closed": company_with_tabs.closed,
                "refused": company_with_tabs.refused,
            }
        }
        response.append(company_object)

    # Close the session
    await session.close()
    return response, total


async def get_services_by_status(service_status: ServiceStatus, company_id: UUID, sort: str, page: int, limit: int,
                                 emergency: bool, custom_position: bool, session: AsyncSession,
                                 executor_id: int | None):
    offset = (page - 1) * limit

    if executor_id:
        unviewed_count_query = (
            select(func.count())
            .select_from(Service)
            .where(
                Service.company_id == company_id,
                Service.status == service_status,
                or_(and_(Service.executor_default_id == executor_id, Service.viewed_executor_default == False),
                    and_(Service.executor_additional_id == executor_id, Service.viewed_executor_additional == False)),
                or_(
                    and_(Service.emergency == True, emergency == True, custom_position == False),
                    and_(Service.custom_position == True, emergency == False, custom_position == True),
                    and_(
                        or_(Service.emergency == True, Service.custom_position == True),
                        emergency == True,
                        custom_position == True
                    ),
                    and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                         custom_position == False)
                )
            )
        )

        count_query = (
            select(func.count())
            .select_from(Service)
            .where(
                Service.company_id == company_id,
                Service.status == service_status,
                or_(Service.executor_default_id == executor_id, Service.executor_additional_id == executor_id),
                or_(
                    and_(Service.emergency == True, emergency == True, custom_position == False),
                    and_(Service.custom_position == True, emergency == False, custom_position == True),
                    and_(
                        or_(Service.emergency == True, Service.custom_position == True),
                        emergency == True,
                        custom_position == True
                    ),
                    and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                         custom_position == False)
                )
            )
        )

        query = (
            select(Service)
            .where(
                Service.company_id == company_id,
                Service.status == service_status,
                or_(Service.executor_default_id == executor_id, Service.executor_additional_id == executor_id),
                or_(
                    and_(Service.emergency == True, emergency == True, custom_position == False),
                    and_(Service.custom_position == True, emergency == False, custom_position == True),
                    and_(
                        or_(Service.emergency == True, Service.custom_position == True),
                        emergency == True,
                        custom_position == True
                    ),
                    and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                         custom_position == False)
                )
            )
            .order_by(
                asc(Service.updated_at) if sort == "date_asc" else desc(Service.updated_at)
            )  # Сортируем по дате
            .offset(offset)
            .limit(limit)
        )

    else:
        unviewed_count_query = (
            select(func.count())
            .select_from(Service)
            .where(
                Service.company_id == company_id,
                Service.status == service_status,
                Service.viewed_admin == False,
                or_(
                    and_(Service.emergency == True, emergency == True, custom_position == False),
                    and_(Service.custom_position == True, emergency == False, custom_position == True),
                    and_(
                        or_(Service.emergency == True, Service.custom_position == True),
                        emergency == True,
                        custom_position == True
                    ),
                    and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                         custom_position == False)
                )
            )
        )

        count_query = (
            select(func.count())
            .select_from(Service)
            .where(
                Service.company_id == company_id,
                Service.status == service_status,
                or_(
                    and_(Service.emergency == True, emergency == True, custom_position == False),
                    and_(Service.custom_position == True, emergency == False, custom_position == True),
                    and_(
                        or_(Service.emergency == True, Service.custom_position == True),
                        emergency == True,
                        custom_position == True
                    ),
                    and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                         custom_position == False)
                )
            )
        )

        query = (
            select(Service)
            .where(
                Service.company_id == company_id,
                Service.status == service_status,
                or_(
                    and_(Service.emergency == True, emergency == True, custom_position == False),
                    and_(Service.custom_position == True, emergency == False, custom_position == True),
                    and_(
                        or_(Service.emergency == True, Service.custom_position == True),
                        emergency == True,
                        custom_position == True
                    ),
                    and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                         custom_position == False),
                    and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                         custom_position == False)
                )
            )
            .order_by(
                asc(Service.updated_at) if sort == "date_asc" else desc(Service.updated_at)
            )  # Сортируем по дате
            .offset(offset)
            .limit(limit)
        )

    total_records_unviewed = await session.execute(unviewed_count_query)
    total_unviewed = total_records_unviewed.scalar()

    total_records = await session.execute(count_query)
    total = total_records.scalar()

    result = await session.execute(query)

    # Получаем все объекты Company из результата
    services = result.scalars().all()
    for service in services:
        service.viewed_executor = False
        if service.executor_default_id == executor_id:
            service.viewed_executor = service.viewed_executor_default
        if service.executor_additional_id == executor_id:
            service.viewed_executor = service.viewed_executor_additional

    return services, total, total_unviewed


async def get_company_id_by_customer(customer_id: int, session: AsyncSession):
    select_query = select(Company.id).where(Company.user_id == customer_id)
    model = await session.execute(select_query)
    company_id = model.scalar_one_or_none()
    return company_id


async def get_customer_services_by_status(service_status: ServiceStatus, company_id: UUID, sort: str, page: int,
                                          limit: int, emergency: bool, custom_position: bool, session: AsyncSession,
                                          customer_id: int):
    offset = (page - 1) * limit

    count_query = (
        select(func.count())
        .select_from(Service)
        .where(
            Service.company_id == company_id,
            Service.status == service_status,
            Service.customer_id == customer_id,
            or_(
                and_(Service.emergency == True, emergency == True, custom_position == False),
                and_(Service.custom_position == True, emergency == False, custom_position == True),
                and_(
                    or_(Service.emergency == True, Service.custom_position == True),
                    emergency == True,
                    custom_position == True
                ),
                and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                     custom_position == False)
            )
        )
    )

    unviewed_count_query = (
        select(func.count())
        .select_from(Service)
        .where(
            Service.company_id == company_id,
            Service.status == service_status,
            Service.customer_id == customer_id,
            Service.viewed_customer == False,
            or_(
                and_(Service.emergency == True, emergency == True, custom_position == False),
                and_(Service.custom_position == True, emergency == False, custom_position == True),
                and_(
                    or_(Service.emergency == True, Service.custom_position == True),
                    emergency == True,
                    custom_position == True
                ),
                and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                     custom_position == False)
            )
        )
    )

    query = (
        select(Service)
        # .options(joinedload(Service.executor))  # Загрузка данных связанной таблицы
        .where(
            Service.company_id == company_id,
            Service.status == service_status,
            Service.customer_id == customer_id,
            or_(
                and_(Service.emergency == True, emergency == True, custom_position == False),
                and_(Service.custom_position == True, emergency == False, custom_position == True),
                and_(
                    or_(Service.emergency == True, Service.custom_position == True),
                    emergency == True,
                    custom_position == True
                ),
                and_(Service.custom_position == False, Service.emergency == False, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == True, Service.emergency == False, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == False, Service.emergency == True, emergency == False,
                     custom_position == False),
                and_(Service.custom_position == True, Service.emergency == True, emergency == False,
                     custom_position == False)
            )
        )
        .order_by(
            asc(Service.updated_at) if sort == "date_asc" else desc(Service.updated_at)
        )  # Сортируем по дате
        .offset(offset)
        .limit(limit)
    )

    total_records = await session.execute(count_query)
    total = total_records.scalar()

    total_records_unviewed = await session.execute(unviewed_count_query)
    total_unviewed = total_records_unviewed.scalar()

    result = await session.execute(query)

    # Получаем все объекты Company из результата
    services = result.scalars().all()

    return services, total, total_unviewed


async def delete_service(service_id: UUID, session: AsyncSession):
    try:
        # Load the service with related media_files using selectinload
        service = await session.execute(
            select(Service).options(selectinload(Service.media_files)).where(Service.id == service_id)
        )
        service = service.scalar()

        if service is None:
            raise NoResultFound()

        # Delete associated media_files first
        for media_file in service.media_files:
            await session.delete(media_file)

        # Now, delete the service
        await session.delete(service)

        # Commit the changes
        await session.commit()

        print('Service and associated media files deleted successfully')

    except NoResultFound:
        raise HTTPException(status_code=404, detail="Заявка не найдена")

    except Exception as e:
        print(f"Error deleting service: {e}")
        await session.rollback()
        raise HTTPException(status_code=400, detail="Ошибка удаления заявки")

    finally:
        await session.close()


async def update_service_by_admin(customer_id: int, service_data: ServiceUpdateInput, old_files: list,
                                  video_file: UploadFile, image_files: List[UploadFile], session: AsyncSession):
    select_query = (select(Service)
                    .options(
        selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                    .options(
        selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.executor_default))
                    .options(
        selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.executor_additional))
                    .options(selectinload(Service.executor_additional))
                    .options(selectinload(Service.executor_default))
                    .options(selectinload(Service.media_files))
                    .where(Service.id == service_data.service_id)
                    )

    result = await session.execute(select_query)
    service = result.scalar_one_or_none()

    fields_to_update = ['executor_default_id', 'executor_additional_id', 'title', 'description', 'deadline_at',
                        'material_availability', 'emergency',
                        'custom_position', 'comment']

    if customer_id:
        if service.customer_id != customer_id:
            raise HTTPException(status_code=400, detail="Заказчик может изменять только свои заявки")
        else:
            if service.status not in [ServiceStatus.WORKING, ServiceStatus.VERIFYING]:
                # if service.status != ServiceStatus.NEW:
                raise HTTPException(status_code=400,
                                    detail="Заказчик может изменять заявки только со статусом 'В работе и Контроль качества'")
        fields_to_update.remove('executor_default_id')  # Убираем возможность изменять исполнителя для Заказчика
        fields_to_update.remove('executor_additional_id')
        service.viewed_admin = False  # Непросмотрено админом
    else:
        service.viewed_customer = False  # Непросмотрено заказчиком

    service.viewed_executor_default = False  # Непросмотрено исполнителем
    service.viewed_executor_additional = False

    print('fields_to_update', fields_to_update)
    if not service_data.description:
        service.description = None
    # counter = 0

    # Обновляем поля
    for field in fields_to_update:
        data_value = getattr(service_data, field, None)
        if data_value is not None:
            current_value = getattr(service, field)
            setattr(service, field, data_value) if current_value != data_value else setattr(service, field,
                                                                                            current_value)
            # if current_value != data_value:
            #   counter +=1

    # if counter > 0:
    #     service.viewed_executor = False  # Непросмотрено исполнителем
    #     if customer_id:
    #         service.viewed_admin = False  # Непросмотрено админом
    #     else:
    #         service.viewed_customer = False  # Непросмотрено заказчиком

    await session.commit()
    await session.refresh(service)
    return service
