"""Auth routes для ролей."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter

from nutrition_tracking_api.api.schemas.auth import RoleOut
from nutrition_tracking_api.api.services.auth.role import RoleService
from nutrition_tracking_api.api.utils.routes import init_crud_routes
from nutrition_tracking_api.dependencies import (
    RequestStateDependency,
    RulesDependency,
    SessionDependency,
    UserDependency,
)

router = APIRouter(tags=["role"], prefix="/roles")

init_crud_routes(router, RoleService)


@router.patch(
    "/{role_id}/add-policy/{policy_id}",
    summary="Добавление политики",
    status_code=200,
    response_model=RoleOut,
)
def add_role_policy(  # noqa: PLR0913
    role_id: UUID,
    policy_id: UUID,
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    return RoleService(session, rules, user, request_state).add_policy(role_id, policy_id)


@router.delete(
    "/{role_id}/remove-policy/{policy_id}",
    summary="Удаление политики",
    status_code=200,
    response_model=RoleOut,
)
def remove_role_policy(  # noqa: PLR0913
    role_id: UUID,
    policy_id: UUID,
    session: SessionDependency,
    rules: RulesDependency,
    user: UserDependency,
    request_state: RequestStateDependency,
) -> Any:
    return RoleService(session, rules, user, request_state).remove_policy(role_id, policy_id)
