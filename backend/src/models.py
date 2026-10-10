from datetime import datetime

from sqlalchemy import CHAR, DateTime, ForeignKey, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.core.base import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )


class User(TimestampMixin, Base):
    __tablename__ = "user"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)

    albums: Mapped[list["Album"]] = relationship(back_populates="creator")
    photos: Mapped[list["Photo"]] = relationship(back_populates="uploader")
    album_memberships: Mapped[list["AlbumMember"]] = relationship(
        back_populates="user"
    )


class Album(TimestampMixin, Base):
    __tablename__ = "album"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String, nullable=False)
    created_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    join_code_hash: Mapped[str] = mapped_column(
        String(255), unique=True, nullable=False
    )

    creator: Mapped["User"] = relationship(back_populates="albums")
    photos: Mapped[list["Photo"]] = relationship(
        back_populates="album", cascade="all, delete-orphan"
    )
    members: Mapped[list["AlbumMember"]] = relationship(
        back_populates="album", cascade="all, delete-orphan"
    )


class AlbumMember(TimestampMixin, Base):
    __tablename__ = "album_members"

    user_id: Mapped[int] = mapped_column(ForeignKey("user.id"), primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("album.id"), primary_key=True)

    user: Mapped["User"] = relationship(back_populates="album_memberships")
    album: Mapped["Album"] = relationship(back_populates="members")


class Photo(TimestampMixin, Base):
    __tablename__ = "photos"

    id: Mapped[int] = mapped_column(primary_key=True)
    album_id: Mapped[int] = mapped_column(ForeignKey("album.id"), nullable=False)
    uploaded_by: Mapped[int] = mapped_column(ForeignKey("user.id"), nullable=False)
    sha256: Mapped[str] = mapped_column(CHAR(64), nullable=False)
    phash: Mapped[str] = mapped_column(Text, nullable=False)

    album: Mapped["Album"] = relationship(back_populates="photos")
    uploader: Mapped["User"] = relationship(back_populates="photos")
