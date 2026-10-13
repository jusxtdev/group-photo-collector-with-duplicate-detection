from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import decode_access_token
from src.models import User

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login/token")

# used as dependency to extract the current user's access token from the incoming request
def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    subject = decode_access_token(token)
    try:
        user_id = int(subject) if subject is not None else None
    except ValueError:
        user_id = None
    user = db.get(User, user_id) if user_id is not None else None
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return user
