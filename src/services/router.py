import uuid
from typing import Any, List
import aiofiles
from fastapi import APIRouter, Depends, status, HTTPException, UploadFile, File, Form, BackgroundTasks
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import validate_admin_access, validate_customer_access, parse_jwt_user_data
from src.database import get_async_session
from src.models import User, OwnerTypes
from src.services.schemas import ServiceResponse, ServiceCreateInput, ServiceCreateByAdminInput, ServiceAssignInput
from src.services import service as services
from src.services import utils as service_utils

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


@router.post("/upload_video_and_image")
async def upload_video_and_image(
        background_tasks: BackgroundTasks,
        service_id: uuid.UUID = Form(...),
        video_file: UploadFile = File(None),
        image_files: List[UploadFile] = File(None),
        current_user: User = Depends(parse_jwt_user_data)
):
    if not video_file and not image_files:
        raise HTTPException(status_code=400, detail="You must upload at least one file")

    count_images = len(image_files) if image_files else 0
    count_videos = 1 if video_file else 0

    # Проверка общего числа файлов
    total_files = count_images + count_videos
    if total_files > 3:
        raise HTTPException(status_code=400, detail="Total files cannot exceed 3")

    # Проверка на количество видео файлов
    if video_file and count_images > 2:
        raise HTTPException(status_code=400, detail="If there is a video, there can be at most 2 images")

    # Проверка на количество фото файлов
    if not video_file and count_images > 3:
        raise HTTPException(status_code=400, detail="If there is no video, there can be at most 3 images")

    owner_type = None
    if current_user.is_admin or current_user.is_customer:
        owner_type = OwnerTypes.CUSTOMER

    if current_user.is_executor:
        owner_type = OwnerTypes.EXECUTOR

    print(owner_type)

    if video_file:
        # background_tasks.add_task(save_video, video_file=video_file, service_id=service_id, owner_type=owner_type)
        await service_utils.save_video(video_file=video_file, service_id=service_id, owner_type=owner_type)

    if image_files:
        await service_utils.save_images(image_files=image_files, service_id=service_id, owner_type=owner_type)
        # background_tasks.add_task(service_utils.save_images, image_files=image_files, service_id=service_id, owner_type=owner_type)
        # background_tasks.add_task(save_image, image_files=image_files, service_id=service_id, owner=owner_type)

    print("SUCCESS")
    return True


# @router.get("/get_video")
# async def get_video():
#     file_path = "./static/name1.mp4"
#
#     async def stream_file():
#         async with aiofiles.open(file_path, "rb") as f:
#             while chunk := await f.read(DEFAULT_CHUNK_SIZE):
#                 yield chunk
#
#     return StreamingResponse(stream_file(), media_type="video/mp4")


# async def save_file_in_folder(image, road, resolution):
#     Path(f"./files/{road}").mkdir(parents=True, exist_ok=True)
#     image.save(f"./files/{road}/{resolution}.webp", format="webp")


# async def write_image_road(db: Session, post_id: uuid, image_road: str, order: int):
#     image_road_object = AdPhotos(url=image_road, ad_id=post_id, id=uuid.uuid4(), order=order)
#     db.add(image_road_object)
#     db.commit()
#     return True

