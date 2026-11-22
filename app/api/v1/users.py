from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.schemas import UserResponse

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "/me",
    response_model=UserResponse,
    summary="Get current user profile",
)
async def get_current_user_profile(current_user: CurrentUser) -> UserResponse:
    """
    Get the profile of the currently authenticated user.

    Requires a valid JWT access token in the Authorization header.
    """
    return UserResponse.model_validate(current_user)
