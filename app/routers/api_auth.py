from fastapi import HTTPException, status
from sqlalchemy.exc import IntegrityError

from app.dependencies.session import SessionDep
from app.repositories.user import UserRepository
from app.schemas.auth import ApiSigninRequest, ApiSignupRequest
from app.services.auth_service import AuthService

from . import api_router


@api_router.post("/signup", status_code=status.HTTP_201_CREATED)
def signup(payload: ApiSignupRequest, db: SessionDep):
    service = AuthService(UserRepository(db))
    try:
        service.register_user(
            username=payload.username,
            email=payload.email,
            password=payload.password,
            full_name=payload.fullName,
            number=payload.number,
        )
    except IntegrityError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="username or email already taken",
        ) from None
    return {"message": "account created"}


@api_router.post("/auth")
def authenticate(payload: ApiSigninRequest, db: SessionDep):
    service = AuthService(UserRepository(db))
    token = service.authenticate_user(payload.username, payload.password)
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="invalid credentials",
        )
    return {"token": token}
