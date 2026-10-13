import hashlib
import io
import uuid
from pathlib import Path

from fastapi import UploadFile
from PIL import Image, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.core import storage
from src.models import Album, AlbumMember, Photo, User


class AlbumNotFoundError(Exception):
    def __init__(self, album_id: int) -> None:
        self.album_id = album_id
        super().__init__(f"Album {album_id} not found")


class InvalidImageError(Exception):
    def __init__(self, filename: str | None) -> None:
        super().__init__(f"File '{filename}' is not a valid image")


class PhotoUploadError(Exception):
    def __init__(self) -> None:
        super().__init__("Could not upload photos")


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _phash(data: bytes, filename: str | None) -> str:
    try:
        with Image.open(io.BytesIO(data)) as image:
            grey = image.convert("L").resize((8, 8))
            pixels = list(grey.getdata())
    except (UnidentifiedImageError, OSError) as exc:
        raise InvalidImageError(filename) from exc
    average = sum(pixels) / len(pixels)
    bits = "".join("1" if pixel >= average else "0" for pixel in pixels)
    return f"{int(bits, 2):016x}"


def _storage_key(album_id: int, filename: str | None) -> str:
    suffix = Path(filename).suffix.lower() if filename else ""
    return f"albums/{album_id}/{uuid.uuid4().hex}{suffix}"


def _cleanup(keys: list[str]) -> None:
    for key in keys:
        try:
            storage.delete_object(key)
        except Exception:
            pass


def _require_membership(db: Session, *, album_id: int, user: User) -> None:
    album = db.get(Album, album_id)
    membership = db.get(
        AlbumMember, {"user_id": user.id, "album_id": album_id}
    )
    if album is None or membership is None:
        raise AlbumNotFoundError(album_id)


def upload_photos(
    db: Session,
    *,
    album_id: int,
    files: list[UploadFile],
    uploader: User,
) -> list[Photo]:
    _require_membership(db, album_id=album_id, user=uploader)

    uploaded_keys: list[str] = []
    photos: list[Photo] = []
    try:
        for file in files:
            data = file.file.read()
            sha256 = _sha256(data)
            phash = _phash(data, file.filename)
            object_key = _storage_key(album_id, file.filename)
            storage.upload_bytes(object_key, data, file.content_type)
            uploaded_keys.append(object_key)
            photos.append(
                Photo(
                    album_id=album_id,
                    uploaded_by=uploader.id,
                    sha256=sha256,
                    phash=phash,
                    object_key=object_key,
                )
            )
        db.add_all(photos)
        db.commit()
    except InvalidImageError:
        db.rollback()
        _cleanup(uploaded_keys)
        raise
    except Exception as exc:
        db.rollback()
        _cleanup(uploaded_keys)
        raise PhotoUploadError from exc

    for photo in photos:
        db.refresh(photo)
    return photos


def list_photos(db: Session, *, album_id: int, user: User) -> list[Photo]:
    _require_membership(db, album_id=album_id, user=user)
    return list(
        db.scalars(
            select(Photo)
            .where(Photo.album_id == album_id)
            .order_by(Photo.created_at.desc(), Photo.id.desc())
        )
    )
