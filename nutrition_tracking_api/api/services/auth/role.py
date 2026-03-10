"""Role service."""

from uuid import UUID

from nutrition_tracking_api.api.crud.auth.role import RoleCRUD
from nutrition_tracking_api.api.exceptions import ObjectNotFoundError
from nutrition_tracking_api.api.schemas.auth.roles import RoleCreate, RoleFilters, RoleOut, RoleUpdate
from nutrition_tracking_api.api.services.base import BaseCRUDService
from nutrition_tracking_api.api.utils.utils import dump_model


class RoleService(
    BaseCRUDService[
        RoleCRUD,
        RoleCreate,
        RoleUpdate,
        RoleOut,
        RoleOut,
        RoleFilters,
    ]
):
    """Сервис для управления ролями."""

    create_model = RoleCreate
    update_model = RoleUpdate
    out_model = RoleOut
    out_model_multi = RoleOut
    resource_crud_class = RoleCRUD
    filter_model = RoleFilters

    track_history = True

    def add_policy(self, role_id: UUID, policy_id: UUID) -> RoleOut:
        """Привязать политику к роли."""
        role = self.resource_crud.get(role_id, with_for_update=False)
        old_role_data = dump_model(role, include_fields=["policy_ids"])
        role.policy_ids.append(policy_id)
        self.resource_crud.session.flush()
        new_role_data = dump_model(role, include_fields=["policy_ids"])
        self.store_history(
            resource=role,
            old_obj=old_role_data,
            new_obj=new_role_data,
        )
        return self.out_model.model_validate(role)

    def remove_policy(self, role_id: UUID, policy_id: UUID) -> RoleOut:
        """Отвязать политику от роли."""
        role = self.resource_crud.get(role_id, with_for_update=False)
        if policy_id not in role.policy_ids:
            raise ObjectNotFoundError
        old_role_data = dump_model(role, include_fields=["policy_ids"])
        role.policy_ids.remove(policy_id)
        self.resource_crud.session.flush()
        new_role_data = dump_model(role, include_fields=["policy_ids"])
        self.store_history(
            resource=role,
            old_obj=old_role_data,
            new_obj=new_role_data,
        )
        return self.out_model.model_validate(role)
