"""Auth routes для пользователей."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from nutrition_tracking_api.api.schemas.auth.user import UserOut, UserProfileUpdate
from nutrition_tracking_api.api.services.auth.users import UserService
from nutrition_tracking_api.api.utils.routes import init_crud_routes
from nutrition_tracking_api.dependencies import (
    RequestStateDependency,
    RulesDependency,
    SessionDependency,
    UserDependency,
)

router = APIRouter(tags=["user"], prefix="/users")

init_crud_routes(router, UserService)


@router.patch(
    "/{user_id}/add-role/{role_id}",
    summary="Добавление роли пользователю",
    status_code=200,
    response_model=UserOut,
)
def add_user_role(  # noqa: PLR0913
    user_id: UUID,
    role_id: UUID,
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    return UserService(session, rules, user, request_state).add_roles(user_id, [role_id])


@router.delete(
    "/{user_id}/remove-role/{role_id}",
    summary="Удаление роли у пользователя",
    status_code=200,
    response_model=UserOut,
)
def remove_user_role(  # noqa: PLR0913
    user_id: UUID,
    role_id: UUID,
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    return UserService(session, rules, user, request_state).remove_roles(user_id, [role_id])


@router.get(
    "/me/",
    summary="Текущий пользователь",
    status_code=200,
    response_model=UserOut,
)
def get_me(
    session: SessionDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    return UserService(session, user=user, request_state=request_state).get_me(user)  # type: ignore[arg-type]


@router.patch(
    "/me/",
    summary="Обновить профиль текущего пользователя",
    status_code=200,
    response_model=UserOut,
)
def update_my_profile(
    profile_data: UserProfileUpdate,
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    return UserService(session, rules, user, request_state).update_profile(user.id, profile_data)  # type: ignore[union-attr]
