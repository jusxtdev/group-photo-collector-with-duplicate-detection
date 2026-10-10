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


class AlbumCounts(NamedTuple):
    photo_count: int
    member_count: int
    owner_count: int


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
