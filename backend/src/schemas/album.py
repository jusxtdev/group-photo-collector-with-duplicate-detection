from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from src.models import AlbumRole


class AlbumCreate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class AlbumUpdate(BaseModel):
    title: str = Field(min_length=1, max_length=255)


class AlbumJoin(BaseModel):
    join_code: str = Field(min_length=1, max_length=64)


class AlbumRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    title: str
    created_by: int
    created_at: datetime
    updated_at: datetime


class AlbumCreated(AlbumRead):
    join_code: str


class AlbumWithRole(AlbumRead):
    role: AlbumRole


class AlbumDetail(AlbumRead):
    role: AlbumRole
    photo_count: int
    member_count: int
    owner_count: int


class AlbumMemberRead(BaseModel):
    user_id: int
    name: str
    role: AlbumRole
    joined_at: datetime


class AlbumMemberRoleUpdate(BaseModel):
    role: AlbumRole
