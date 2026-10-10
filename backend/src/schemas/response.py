from typing import Generic, TypeVar

from pydantic import BaseModel

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    status: bool
    msg: str
    data: T | None = None

    @classmethod
    def ok(cls, data: T | None = None, msg: str = "success") -> "ApiResponse[T]":
        return cls(status=True, msg=msg, data=data)

    @classmethod
    def fail(cls, msg: str, data: T | None = None) -> "ApiResponse[T]":
        return cls(status=False, msg=msg, data=data)
