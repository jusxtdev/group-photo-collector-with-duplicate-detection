from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import create_access_token
from src.schemas.response import ApiResponse
from src.schemas.user import Token, UserCreate, UserLogin, UserRead
from src.services import user as user_service

router = APIRouter(tags=["auth"])


@router.post(
    "/signup",
    response_model=ApiResponse[UserRead],
    status_code=status.HTTP_201_CREATED,
)
def signup(
    payload: UserCreate, db: Session = Depends(get_db)
) -> ApiResponse[UserRead]:
    try:
        user = user_service.create_user(
            db,
            name=payload.name,
            email=payload.email,
            password=payload.password,
        )
    except user_service.EmailAlreadyExistsError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc
    return ApiResponse.ok(data=user, msg="User created")


@router.post("/login", response_model=ApiResponse[Token])
def login(payload: UserLogin, db: Session = Depends(get_db)) -> ApiResponse[Token]:
    user = user_service.authenticate_user(
        db,
        email=payload.email,
        password=payload.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )
    token = Token(access_token=create_access_token(str(user.id)))
    return ApiResponse.ok(data=token, msg="Login successful")


@router.post("/login/token", response_model=Token)
def login_token(
    form: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db),
) -> Token:
    user = user_service.authenticate_user(
        db,
        email=form.username,
        password=form.password,
    )
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return Token(access_token=create_access_token(str(user.id)))
