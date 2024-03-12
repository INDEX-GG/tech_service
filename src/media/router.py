import os
from pathlib import Path
from typing import Tuple
from uuid import UUID

import aiofiles
from fastapi import APIRouter, Depends, HTTPException, Header
from fastapi.responses import StreamingResponse, FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import status

from src.auth.jwt import validate_users_access
from src.database import get_async_session
from src.media import service as media_services
from src.media.service import DEFAULT_CHUNK_SIZE
from src.models import FileTypes

router = APIRouter()


def parse_range_header(range_header: str, total_size: int) -> Tuple[int, int]:
    unit, ranges = range_header.split("=")
    start, end = ranges.split("-")
    start = int(start) if start else 0
    end = int(end) if end else total_size - 1
    return start, end


# @router.get("/video/{key}", response_class=StreamingResponse, dependencies=[Depends(validate_users_access)])
@router.get("/video/{key}", response_class=StreamingResponse)
async def get_video(
        key: UUID,
        range_header: str = Header(None),
        session: AsyncSession = Depends(get_async_session)
) -> StreamingResponse:

    media_type = FileTypes.VIDEO
    file_path = await media_services.get_media_path_by_key(key, media_type, session)

    if not Path(file_path).is_file():
        raise HTTPException(status_code=404, detail="Видео не найдено")

    file_size = os.path.getsize(file_path)
    headers = {
        "Accept-Ranges": "bytes",
        "Content-Type": "video/mp4",
        "Content-Length": str(file_size)
    }

    if range_header:
        start, end = parse_range_header(range_header, file_size)
        headers["Content-Range"] = f"bytes {start}-{end}/{file_size}"
        status_code = status.HTTP_206_PARTIAL_CONTENT
    else:
        status_code = status.HTTP_200_OK

    async def stream_file():
        async with aiofiles.open(file_path, "rb") as f:
            while chunk := await f.read(DEFAULT_CHUNK_SIZE):
                yield chunk

    return StreamingResponse(
        stream_file(),
        status_code=status_code,
        headers=headers,
        media_type="video/mp4"
    )


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

    return FileResponse(path=file_path, media_type="image/webp")
