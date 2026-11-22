from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm

from app.api.deps import DbSession
from app.core.security import create_access_token
from app.schemas import LoginRequest, Token, UserCreate, UserResponse
from app.services import authenticate_user, create_user, get_user_by_email

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user",
    responses={
        400: {"description": "Email already registered"},
    },
)
async def register(user_in: UserCreate, db: DbSession) -> UserResponse:
    """
    Register a new user account.

    - **email**: Valid email address (must be unique)
    - **password**: At least 8 characters
    - **full_name**: Optional display name
    """
    existing_user = await get_user_by_email(db, user_in.email)
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )

    user = await create_user(db, user_in)
    return UserResponse.model_validate(user)


@router.post(
    "/login",
    response_model=Token,
    summary="Login and get access token",
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login(form_data: Annotated[OAuth2PasswordRequestForm, Depends()], db: DbSession) -> Token:
    """
    OAuth2 compatible login endpoint.

    Returns a JWT access token for authenticated requests.
    Use the token in the Authorization header: `Bearer <token>`
    """
    user = await authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)


@router.post(
    "/login/json",
    response_model=Token,
    summary="Login with JSON body",
    responses={
        401: {"description": "Invalid credentials"},
    },
)
async def login_json(credentials: LoginRequest, db: DbSession) -> Token:
    """
    Alternative login endpoint accepting JSON body.

    Useful for API clients that prefer JSON over form data.
    """
    user = await authenticate_user(db, credentials.email, credentials.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(subject=str(user.id))
    return Token(access_token=access_token)
