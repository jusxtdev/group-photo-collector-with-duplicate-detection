from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.deps import get_current_user
from src.models import AlbumRole, User
from src.schemas.album import (
    AlbumCreate,
    AlbumCreated,
    AlbumDetail,
    AlbumJoin,
    AlbumMemberRead,
    AlbumMemberRoleUpdate,
    AlbumRead,
    AlbumUpdate,
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


@router.get(
    "/albums/{album_id}/members",
    response_model=ApiResponse[list[AlbumMemberRead]],
)
def list_album_members(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[list[AlbumMemberRead]]:
    try:
        members = album_service.list_album_members(
            db, album_id=album_id, user=current_user
        )
    except album_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    data = [
        AlbumMemberRead(
            user_id=member_user.id,
            name=member_user.name,
            role=membership.role,
            joined_at=membership.created_at,
        )
        for member_user, membership in members
    ]
    return ApiResponse.ok(data=data, msg="Members retrieved")


@router.patch(
    "/albums/{album_id}/members/{user_id}/role",
    response_model=ApiResponse[AlbumMemberRead],
)
def update_member_role(
    album_id: int,
    user_id: int,
    payload: AlbumMemberRoleUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumMemberRead]:
    try:
        target_user, membership = album_service.update_member_role(
            db,
            album_id=album_id,
            target_user_id=user_id,
            new_role=payload.role,
            actor=current_user,
        )
    except album_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    except album_service.NotAlbumOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except album_service.NotMainOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except album_service.MemberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except album_service.AlreadyOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except album_service.NotAnOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    except album_service.CannotDemoteMainOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    data = AlbumMemberRead(
        user_id=target_user.id,
        name=target_user.name,
        role=membership.role,
        joined_at=membership.created_at,
    )
    msg = (
        "Member promoted to owner"
        if membership.role is AlbumRole.OWNER
        else "Owner demoted to member"
    )
    return ApiResponse.ok(data=data, msg=msg)


def _remove_membership(
    db: Session,
    *,
    album_id: int,
    target_user_id: int,
    actor: User,
    success_msg: str,
) -> ApiResponse[AlbumMemberRead]:
    try:
        target_user, role, joined_at = album_service.remove_member(
            db,
            album_id=album_id,
            target_user_id=target_user_id,
            actor=actor,
        )
    except album_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    except album_service.MemberNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc),
        ) from exc
    except album_service.CannotRemoveMemberError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except album_service.CannotRemoveOtherOwnerError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    except album_service.CannotRemoveCreatorError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    return ApiResponse.ok(
        data=AlbumMemberRead(
            user_id=target_user.id,
            name=target_user.name,
            role=role,
            joined_at=joined_at,
        ),
        msg=success_msg,
    )


@router.delete(
    "/albums/{album_id}/members/me",
    response_model=ApiResponse[AlbumMemberRead],
)
def leave_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumMemberRead]:
    return _remove_membership(
        db,
        album_id=album_id,
        target_user_id=current_user.id,
        actor=current_user,
        success_msg="Left album",
    )


@router.delete(
    "/albums/{album_id}/members/{user_id}",
    response_model=ApiResponse[AlbumMemberRead],
)
def remove_member(
    album_id: int,
    user_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumMemberRead]:
    return _remove_membership(
        db,
        album_id=album_id,
        target_user_id=user_id,
        actor=current_user,
        success_msg="Member removed",
    )


@router.patch(
    "/albums/{album_id}",
    response_model=ApiResponse[AlbumRead],
)
def update_album(
    album_id: int,
    payload: AlbumUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumRead]:
    try:
        album = album_service.update_album_title(
            db, album_id=album_id, title=payload.title, actor=current_user
        )
    except album_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    except album_service.AlbumEditForbiddenError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return ApiResponse.ok(
        data=AlbumRead.model_validate(album), msg="Album updated"
    )


@router.delete(
    "/albums/{album_id}",
    response_model=ApiResponse[AlbumRead],
)
def delete_album(
    album_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ApiResponse[AlbumRead]:
    try:
        deleted = album_service.delete_album(
            db, album_id=album_id, actor=current_user
        )
    except album_service.AlbumNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Album not found",
        ) from exc
    except album_service.CannotDeleteAlbumError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(exc),
        ) from exc
    return ApiResponse.ok(
        data=AlbumRead.model_validate(deleted), msg="Album deleted"
    )
