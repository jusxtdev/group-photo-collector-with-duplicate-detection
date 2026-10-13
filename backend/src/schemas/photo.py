from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PhotoRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    album_id: int
    uploaded_by: int
    sha256: str
    phash: str
    object_key: str
    created_at: datetime
    updated_at: datetime


class PhotoListItem(PhotoRead):
    url: str
