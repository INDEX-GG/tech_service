from pathlib import Path
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession

from src.auth.jwt import validate_users_access
from src.database import get_async_session
from src.media import service as media_services
from src.media.service import DEFAULT_CHUNK_SIZE
from src.models import FileTypes

router = APIRouter()


# @router.get("/video/{key}", response_class=StreamingResponse, dependencies=[Depends(validate_users_access)])
@router.get("/video/{key}", response_class=StreamingResponse)
async def get_video(
        key: UUID,
        session: AsyncSession = Depends(get_async_session)
) -> StreamingResponse:

    media_type = FileTypes.VIDEO
    file_path = await media_services.get_media_path_by_key(key, media_type, session)

    if not Path(file_path).is_file():
        raise HTTPException(status_code=404, detail="Видео не найдено")

    async def stream_file():
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(DEFAULT_CHUNK_SIZE):
                yield chunk

    return StreamingResponse(stream_file(), media_type="video/mp4")


# @router.get("/image/{key}", response_class=FileResponse, dependencies=[Depends(validate_users_access)])
@router.get("/image/{key}", response_class=FileResponse)
async def get_image(
        key: UUID,
        session: AsyncSession = Depends(get_async_session)
) -> FileResponse:

    media_type = FileTypes.IMAGE
    file_path = await media_services.get_media_path_by_key(key, media_type, session)

    if not Path(file_path).is_file():
        raise HTTPException(status_code=404, detail="Изображение не найдено")

    # return FileResponse(path=file_path, media_type="image/webp")
    return FileResponse(path=file_path)
