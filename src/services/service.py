import datetime
from typing import Any, List
from uuid import UUID

from fastapi import HTTPException, UploadFile
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.models import Service, ServiceStatus, User, Company, OwnerTypes, MediaFiles
from src.services.schemas import ServiceCreateInput, ServiceCreateByAdminInput
from src.users.service import get_user_profile_by_id, get_user_by_role
from src.services import utils as service_utils


async def create_new_service_by_admin(
        customer_id: int,
        service_data: ServiceCreateByAdminInput,
        video_file: UploadFile,
        image_files: List[UploadFile],
        session: AsyncSession
) -> dict[str, Any] | None:

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
            status=ServiceStatus.NEW
        )

        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)

        customer = await get_user_profile_by_id(customer_id, session)
        new_service.customer = customer

        if service_data.executor_id:
            executor = await get_user_by_role(service_data.executor_id, "is_executor", session)
            new_service.executor = executor

        owner_type = OwnerTypes.CUSTOMER

        if video_file:
            uploaded_video = await service_utils.save_video(video_file=video_file, service_id=new_service.id, owner_type=owner_type)
            if not uploaded_video:
                raise ValueError("Ошибка загрузки видео")

        if image_files:
            uploaded_image = await service_utils.save_images(image_files=image_files, service_id=new_service.id, owner_type=owner_type)
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
        new_service = Service(
            customer_id=customer_id,
            title=service_data.title,
            description=service_data.description,
            material_availability=service_data.material_availability,
            emergency=service_data.emergency,
            deadline_at=service_data.deadline_at,
            status=ServiceStatus.NEW
        )

        session.add(new_service)
        await session.commit()
        await session.refresh(new_service)

        customer = await get_user_profile_by_id(customer_id, session)
        new_service.customer = customer

        owner_type = OwnerTypes.CUSTOMER

        if video_file:
            uploaded_video = await service_utils.save_video(video_file=video_file, service_id=new_service.id,
                                                            owner_type=owner_type)
            if not uploaded_video:
                raise ValueError("Ошибка загрузки видео")

        if image_files:
            uploaded_image = await service_utils.save_images(image_files=image_files, service_id=new_service.id,
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
                        .options(selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                        .options(selectinload(Service.executor))
                        .options(selectinload(Service.media_files))
                        .where(Service.id == assign_data.service_id)
                        )
        model = await session.execute(select_query)
        service = model.scalar_one_or_none()

        service.executor_id = assign_data.executor_id
        service.status = ServiceStatus.WORKING
        await session.commit()
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
    service_executor_id = service.executor_id
    service_status = service.status

    return service_executor_id, service_status


async def mark_service_verifying(service_id: UUID, session: AsyncSession):
    try:
        # Update the Service status to VERIFYING
        update_query = update(Service).where(Service.id == service_id).values(status=ServiceStatus.VERIFYING)
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


async def get_service_card_by_id(service_id: UUID, session: AsyncSession):
    select_query = (select(Service)
                    .options(
                    selectinload(Service.customer).selectinload(User.customer_company).selectinload(Company.contacts))
                    .options(selectinload(Service.executor))
                    .options(selectinload(Service.media_files))
                    .where(Service.id == service_id)
                    )
    model = await session.execute(select_query)
    service = model.scalar_one_or_none()
    return service

# async def upload_video_and_image(
#         service_id: uuid.UUID = Form(...),
#         video_file: UploadFile = File(None),
#         image_files: List[UploadFile] = File(None),
#         current_user: User = Depends(parse_jwt_user_data)
# ):
#     if not video_file and not image_files:
#         raise HTTPException(status_code=400, detail="You must upload at least one file")
#
#     count_images = len(image_files) if image_files else 0
#     count_videos = 1 if video_file else 0
#
#     # Проверка общего числа файлов
#     total_files = count_images + count_videos
#     if total_files > 3:
#         raise HTTPException(status_code=400, detail="Total files cannot exceed 3")
#
#     # Проверка на количество видео файлов
#     if video_file and count_images > 2:
#         raise HTTPException(status_code=400, detail="If there is a video, there can be at most 2 images")
#
#     # Проверка на количество фото файлов
#     if not video_file and count_images > 3:
#         raise HTTPException(status_code=400, detail="If there is no video, there can be at most 3 images")
#
#     owner_type = None
#     if current_user.is_admin or current_user.is_customer:
#         owner_type = OwnerTypes.CUSTOMER
#
#     if current_user.is_executor:
#         owner_type = OwnerTypes.EXECUTOR
#
#     print(owner_type)
#
#     if video_file:
#         # background_tasks.add_task(save_video, video_file=video_file, service_id=service_id, owner_type=owner_type)
#         await service_utils.save_video(video_file=video_file, service_id=service_id, owner_type=owner_type)
#
#     if image_files:
#         # background_tasks.add_task(service_utils.save_images, image_files=image_files, service_id=service_id, owner_type=owner_type)
#         await service_utils.save_images(image_files=image_files, service_id=service_id, owner_type=owner_type)
#
#     print("SUCCESS")
#     return True