from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models import User
from src.schemas.album import (
    AlbumCreate,
    AlbumCreated,
    AlbumDetail,
    AlbumJoin,
    AlbumRead,
    AlbumWithRole,
)
from src.schemas.response import ApiResponse
from src.services import album as album_service

router = APIRouter(tags=["albums"])


@router.post(
    "/album",
    response_model=ApiResponse[AlbumCreated],
    status_code=status.HTTP_201_CREATED,
)
def create_album(
    payload: AlbumCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumCreated]:
    try:
        album, join_code = album_service.create_album(
            db, title=payload.title, creator=current_user
        )
    except album_service.AlbumCreationError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(exc),
        ) from exc
    data = AlbumCreated(
        **AlbumRead.model_validate(album).model_dump(),
        join_code=join_code,
    )
    return ApiResponse.ok(data=data, msg="Album created")


@router.get("/album", response_model=ApiResponse[list[AlbumWithRole]])
def list_albums(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[AlbumWithRole]]:
    albums = album_service.list_albums_for_user(db, user=current_user)
    data = [
        AlbumWithRole(
            **AlbumRead.model_validate(album).model_dump(),
            role=role,
        )
        for album, role in albums
    ]
    return ApiResponse.ok(data=data, msg="Albums retrieved")


@router.get(
    "/album/{album_id}", response_model=ApiResponse[AlbumDetail]
)
def get_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumDetail]:
    try:
        album, role, counts = album_service.get_album_detail(
            db, album_id=album_id, user=current_user
        )
    except album_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    data = AlbumDetail(
        **AlbumRead.model_validate(album).model_dump(),
        role=role,
        photo_count=counts.photo_count,
        member_count=counts.member_count,
        owner_count=counts.owner_count,
    )
    return ApiResponse.ok(data=data, msg="Album retrieved")


@router.post(
    "/albums/join",
    response_model=ApiResponse[AlbumWithRole],
    status_code=status.HTTP_201_CREATED,
)
def join_album(
    payload: AlbumJoin,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumWithRole]:
    try:
        album, role = album_service.join_album(
            db, join_code=payload.join_code, user=current_user
        )
    except album_service.InvalidJoinCodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invalid join code",
        ) from exc
    except album_service.AlreadyMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Already a member of this album",
        ) from exc
    data = AlbumWithRole(
        **AlbumRead.model_validate(album).model_dump(),
        role=role,
    )
    return ApiResponse.ok(data=data, msg="Joined album")
