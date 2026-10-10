from fastapi import APIRouter

from src.schemas.response import ApiResponse

router = APIRouter()


@router.get("/health", response_model=ApiResponse[None])
def health() -> ApiResponse[None]:
    return ApiResponse.ok(msg="Service is healthy")
