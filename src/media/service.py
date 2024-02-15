import io
import math
import os
import uuid
from pathlib import Path
from typing import List

import aiofiles
from fastapi import UploadFile

from PIL import Image
from pillow_heif import register_heif_opener

from src.database import engine
from src.models import OwnerTypes
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.models import FileTypes, MediaFiles

DEFAULT_CHUNK_SIZE = 1024 * 1024 * 20  # 20 megabytes


async def get_media_path_by_key(key: UUID, media_type: FileTypes, session: AsyncSession):
    select_query = select(MediaFiles).where(MediaFiles.id == key, MediaFiles.file_type == media_type)
    model = await session.execute(select_query)
    media_file = model.scalar_one_or_none()
    path_type = "videos" if media_type == FileTypes.VIDEO else "images"
    url = f"./static/{path_type}/{media_file.url}"
    return url


async def save_video(video_file: UploadFile, service_id: uuid.UUID, owner_type: OwnerTypes):
    filename, file_extension = os.path.splitext(video_file.filename)
    file_name = str(uuid.uuid4()) + str(file_extension)
    road = service_id

    url = f"{road}/{file_name}"  # Относительный Путь для записи в БД

    Path(f"./static/videos/{road}").mkdir(parents=True, exist_ok=True)
    file_path = f"./static/videos/{url}"  # Полный путь до файла, для сохранения на сервере

    saved_to_folder = await save_video_to_folder(video_file, file_path)
    if not saved_to_folder:
        raise

    # SAVE FILE TO DATABASE
    saved_to_db = await save_video_to_db(url, service_id, owner_type)

    return saved_to_db


async def save_video_to_folder(video_file: UploadFile, file_path: str) -> bool:
    async with aiofiles.open(file_path, "wb") as f:
        while chunk := await video_file.read(DEFAULT_CHUNK_SIZE):
            await f.write(chunk)

    return True


async def save_video_to_db(url: str, service_id: uuid.UUID, owner_type: OwnerTypes):
    async with AsyncSession(engine) as session:
        video_object = MediaFiles(
            id=uuid.uuid4(),
            service_id=service_id,
            file_type=FileTypes.VIDEO,
            owner_type=owner_type,
            url=url
        )
        session.add(video_object)
        await session.commit()
        await session.refresh(video_object)
        return True


async def save_images(image_files, service_id, owner_type):
    try:
        road = service_id

        for image in image_files:
            image_content = image.file.read()

            # Register opener for HEIF/HEIC format
            register_heif_opener()

            orientation_value = get_image_orientation(image_content)

            im = Image.open(io.BytesIO(image_content))
            # Convert to RGB if needed
            im = im.convert("RGB")

            if orientation_value == 3:
                im = im.rotate(180, expand=True)
            elif orientation_value == 6:
                im = im.rotate(-90, expand=True)
            elif orientation_value == 8:
                im = im.rotate(90, expand=True)

            file_name = uuid.uuid4()

            await save_image_to_folder(im, road, file_name)

            url = f"{road}/{file_name}.webp"
            await save_image_to_db(url, service_id, owner_type)

        return True
    except Exception as e:
        print('error', str(e))
        return False


def get_image_orientation(image_content):
    orientation_value = 1  # Default orientation (normal)
    with io.BytesIO(image_content) as f:
        im = Image.open(f)
        if hasattr(im, '_getexif'):
            exif = im._getexif()
            if exif is not None:
                orientation_tag = 274  # EXIF tag for orientation
                orientation_value = exif.get(orientation_tag, 1)
    return orientation_value


async def make_image_resize(image):
    width, height = image.size
    aspect_ratio = height / width
    if aspect_ratio > 0.75:
        new_height = 960
        new_width = math.ceil(new_height / aspect_ratio)
    elif aspect_ratio < 0.75:
        new_width = 1280
        new_height = math.ceil(new_width * aspect_ratio)
    else:
        new_width = 1280
        new_height = 960
    im1 = image.resize((new_width, new_height))
    return im1


async def save_image_to_folder(image, road, file_name):
    im1 = await make_image_resize(image)
    Path(f"./static/images/{road}").mkdir(parents=True, exist_ok=True)
    im1.save(f"./static/images/{road}/{file_name}.webp", format="webp")


async def save_image_to_db(url: str, service_id: uuid.UUID, owner_type: OwnerTypes):
    async with AsyncSession(engine) as session:
        image_object = MediaFiles(
            id=uuid.uuid4(),
            service_id=service_id,
            file_type=FileTypes.IMAGE,
            owner_type=owner_type,
            url=url
        )
        session.add(image_object)
        await session.commit()
        await session.refresh(image_object)
        return True


async def remove_unused_media_files(service_id: UUID, old_files: List[str], session: AsyncSession):
    select_query = select(MediaFiles).where(MediaFiles.service_id == service_id, MediaFiles.owner_type == OwnerTypes.CUSTOMER)
    model = await session.execute(select_query)
    media_files = model.scalars().all()

    media_files_in_db = []
    video_counter = 0
    image_counter = 0
    deleted_counter = 0

    for media_file in media_files:
        media_obj = {
            "id": str(media_file.id),
            "file_type": media_file.file_type,
        }
        media_files_in_db.append(media_obj)

        if str(media_file.id) not in old_files:
            # print('delete file', str(media_file.id))
            # DELETE MEDIA FILE with ID = media_file.id
            await session.delete(media_file)

            path_type = "videos" if media_file.file_type == FileTypes.VIDEO else "images"
            file_path = f"./static/{path_type}/{media_file.url}"
            if os.path.exists(file_path):
                os.remove(file_path)

            deleted_counter += 1
        else:
            video_counter += 1 if media_file.file_type == FileTypes.VIDEO else 0
            image_counter += 1 if media_file.file_type == FileTypes.IMAGE else 0

    if deleted_counter > 0:
        await session.commit()

    # print('old_files:', old_files)
    # print('media_files_in_db:', media_files_in_db)

    return video_counter, image_counter
