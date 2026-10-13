from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from src.core import storage
from src.core.database import get_db
from src.core.deps import get_current_user
from src.models import User
from src.schemas.photo import PhotoListItem, PhotoRead
from src.schemas.response import ApiResponse
from src.services import photo as photo_service

router = APIRouter(prefix="/photo", tags=["Photo"])


@router.post(
    "/albums/{album_id}/photos/batch",
    response_model=ApiResponse[list[PhotoRead]],
    status_code=status.HTTP_201_CREATED,
)
def upload_photos(
    album_id: int,
    files: list[UploadFile] = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[PhotoRead]]:
    try:
        photos = photo_service.upload_photos(
            db,
            album_id=album_id,
            files=files,
            uploader=current_user,
        )
    except photo_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    except photo_service.InvalidImageError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    except photo_service.PhotoUploadError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    data = [PhotoRead.model_validate(photo) for photo in photos]
    return ApiResponse.ok(data=data, msg="Photos uploaded")


@router.get(
    "/albums/{album_id}/photos",
    response_model=ApiResponse[list[PhotoListItem]],
)
def list_photos(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[PhotoListItem]]:
    try:
        photos = photo_service.list_photos(
            db, album_id=album_id, user=current_user
        )
    except photo_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    data = [
        PhotoListItem(
            **PhotoRead.model_validate(photo).model_dump(),
            url=storage.generate_presigned_url(photo.object_key),
        )
        for photo in photos
    ]
    return ApiResponse.ok(data=data, msg="Photos retrieved")
