from datetime import datetime
from typing import NamedTuple

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from src.core.security import generate_join_code, hash_join_code
from src.models import Album, AlbumMember, AlbumRole, Photo, User

_MAX_JOIN_CODE_ATTEMPTS = 5


class AlbumCreationError(Exception):
    def __init__(self) -> None:
        super().__init__("Could not generate a unique join code for the album")


class AlbumNotFoundError(Exception):
    def __init__(self, album_id: int) -> None:
        self.album_id = album_id
        super().__init__(f"Album {album_id} not found")


class InvalidJoinCodeError(Exception):
    def __init__(self) -> None:
        super().__init__("Invalid join code")


class AlreadyMemberError(Exception):
    def __init__(self) -> None:
        super().__init__("User is already a member of this album")


class NotAlbumOwnerError(Exception):
    def __init__(self) -> None:
        super().__init__("Only album owners can change member roles")


class NotMainOwnerError(Exception):
    def __init__(self) -> None:
        super().__init__("Only the album owner can demote members")


class MemberNotFoundError(Exception):
    def __init__(self) -> None:
        super().__init__("User is not a member of this album")


class NotAnOwnerError(Exception):
    def __init__(self) -> None:
        super().__init__("User is not an owner of this album")


class CannotDemoteMainOwnerError(Exception):
    def __init__(self) -> None:
        super().__init__("The album owner cannot be demoted")


class AlreadyOwnerError(Exception):
    def __init__(self) -> None:
        super().__init__("User is already an owner of this album")


class CannotRemoveMemberError(Exception):
    def __init__(self) -> None:
        super().__init__("Only album owners can remove members")


class CannotRemoveOtherOwnerError(Exception):
    def __init__(self) -> None:
        super().__init__("Only the album creator can remove other owners")


class CannotRemoveCreatorError(Exception):
    def __init__(self) -> None:
        super().__init__("The album creator cannot be removed")


class AlbumEditForbiddenError(Exception):
    def __init__(self) -> None:
        super().__init__("Only album owners can edit the album")


class CannotDeleteAlbumError(Exception):
    def __init__(self) -> None:
        super().__init__("Only the album creator can delete the album")


class AlbumCounts(NamedTuple):
    photo_count: int
    member_count: int
    owner_count: int


class AlbumDeletion(NamedTuple):
    id: int
    title: str
    created_by: int
    created_at: datetime
    updated_at: datetime


def create_album(db: Session, *, title: str, creator: User) -> tuple[Album, str]:
    for _ in range(_MAX_JOIN_CODE_ATTEMPTS):
        join_code = generate_join_code()
        album = Album(
            title=title,
            created_by=creator.id,
            join_code_hash=hash_join_code(join_code),
            members=[AlbumMember(user_id=creator.id, role=AlbumRole.OWNER)],
        )
        db.add(album)
        try:
            db.commit()
        except IntegrityError:
            # if the join_code is not unique, try again with a new join_code
            db.rollback()
            continue
        db.refresh(album)
        return album, join_code
    raise AlbumCreationError


def list_albums_for_user(
    db: Session, *, user: User
) -> list[tuple[Album, AlbumRole]]:
    rows = db.execute(
        select(Album, AlbumMember.role)
        .join(AlbumMember, AlbumMember.album_id == Album.id)
        .where(AlbumMember.user_id == user.id)
        .order_by(Album.created_at.desc(), Album.id.desc())
    ).all()
    return [(album, role) for album, role in rows]


def get_album_detail(
    db: Session, *, album_id: int, user: User
) -> tuple[Album, AlbumRole, AlbumCounts]:
    role = db.scalar(
        select(AlbumMember.role).where(
            AlbumMember.album_id == album_id,
            AlbumMember.user_id == user.id,
        )
    )
    if role is None:
        raise AlbumNotFoundError(album_id)
    album = db.get(Album, album_id)
    if album is None:
        raise AlbumNotFoundError(album_id)
    counts = AlbumCounts(
        photo_count=db.scalar(
            select(func.count()).select_from(Photo).where(Photo.album_id == album_id)
        )
        or 0,
        member_count=db.scalar(
            select(func.count())
            .select_from(AlbumMember)
            .where(AlbumMember.album_id == album_id)
        )
        or 0,
        owner_count=db.scalar(
            select(func.count())
            .select_from(AlbumMember)
            .where(
                AlbumMember.album_id == album_id,
                AlbumMember.role == AlbumRole.OWNER,
            )
        )
        or 0,
    )
    return album, role, counts


def join_album(
    db: Session, *, join_code: str, user: User
) -> tuple[Album, AlbumRole]:
    album = db.scalar(
        select(Album).where(
            Album.join_code_hash == hash_join_code(join_code.strip())
        )
    )
    if album is None:
        raise InvalidJoinCodeError
    existing = db.get(AlbumMember, {"user_id": user.id, "album_id": album.id})
    if existing is not None:
        raise AlreadyMemberError
    db.add(
        AlbumMember(user_id=user.id, album_id=album.id, role=AlbumRole.MEMBER)
    )
    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        raise AlreadyMemberError from exc
    return album, AlbumRole.MEMBER


def list_album_members(
    db: Session, *, album_id: int, user: User
) -> list[tuple[User, AlbumMember]]:
    requester = db.get(AlbumMember, {"user_id": user.id, "album_id": album_id})
    if requester is None:
        raise AlbumNotFoundError(album_id)
    rows = db.execute(
        select(User, AlbumMember)
        .join(AlbumMember, AlbumMember.user_id == User.id)
        .where(AlbumMember.album_id == album_id)
        .order_by(AlbumMember.created_at.asc(), User.id.asc())
    ).all()
    return [(member_user, membership) for member_user, membership in rows]


def update_member_role(
    db: Session,
    *,
    album_id: int,
    target_user_id: int,
    new_role: AlbumRole,
    actor: User,
) -> tuple[User, AlbumMember]:
    requester = db.get(AlbumMember, {"user_id": actor.id, "album_id": album_id})
    if requester is None:
        raise AlbumNotFoundError(album_id)

    album = db.get(Album, album_id)

    if new_role is AlbumRole.OWNER:
        if requester.role is not AlbumRole.OWNER:
            raise NotAlbumOwnerError
    elif album is None or album.created_by != actor.id:
        raise NotMainOwnerError

    membership = db.get(
        AlbumMember, {"user_id": target_user_id, "album_id": album_id}
    )
    if membership is None:
        raise MemberNotFoundError

    if new_role is AlbumRole.OWNER:
        if membership.role is AlbumRole.OWNER:
            raise AlreadyOwnerError
        membership.role = AlbumRole.OWNER
    else:
        if album is not None and target_user_id == album.created_by:
            raise CannotDemoteMainOwnerError
        if membership.role is not AlbumRole.OWNER:
            raise NotAnOwnerError
        membership.role = AlbumRole.MEMBER

    target_user = db.get(User, target_user_id)
    db.commit()
    return target_user, membership


def remove_member(
    db: Session, *, album_id: int, target_user_id: int, actor: User
) -> tuple[User, AlbumRole, datetime]:
    requester = db.get(AlbumMember, {"user_id": actor.id, "album_id": album_id})
    if requester is None:
        raise AlbumNotFoundError(album_id)

    membership = db.get(
        AlbumMember, {"user_id": target_user_id, "album_id": album_id}
    )
    if membership is None:
        raise MemberNotFoundError

    album = db.get(Album, album_id)
    if album is None:
        raise AlbumNotFoundError(album_id)

    if target_user_id != actor.id:
        if requester.role is not AlbumRole.OWNER:
            raise CannotRemoveMemberError
        if (
            membership.role is AlbumRole.OWNER
            and album.created_by != actor.id
        ):
            raise CannotRemoveOtherOwnerError

    if target_user_id == album.created_by:
        raise CannotRemoveCreatorError

    target_user = db.get(User, target_user_id)
    role = membership.role
    joined_at = membership.created_at
    db.delete(membership)
    db.commit()
    return target_user, role, joined_at


def update_album_title(
    db: Session, *, album_id: int, title: str, actor: User
) -> Album:
    membership = db.get(
        AlbumMember, {"user_id": actor.id, "album_id": album_id}
    )
    if membership is None:
        raise AlbumNotFoundError(album_id)
    if membership.role is not AlbumRole.OWNER:
        raise AlbumEditForbiddenError

    album = db.get(Album, album_id)
    if album is None:
        raise AlbumNotFoundError(album_id)

    album.title = title
    db.commit()
    db.refresh(album)
    return album


def delete_album(
    db: Session, *, album_id: int, actor: User
) -> AlbumDeletion:
    membership = db.get(
        AlbumMember, {"user_id": actor.id, "album_id": album_id}
    )
    if membership is None:
        raise AlbumNotFoundError(album_id)

    album = db.get(Album, album_id)
    if album is None:
        raise AlbumNotFoundError(album_id)

    if album.created_by != actor.id:
        raise CannotDeleteAlbumError

    snapshot = AlbumDeletion(
        id=album.id,
        title=album.title,
        created_by=album.created_by,
        created_at=album.created_at,
        updated_at=album.updated_at,
    )
    db.delete(album)
    db.commit()
    return snapshot
