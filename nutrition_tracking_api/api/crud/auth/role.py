"""Role CRUD operations."""

from typing import Any

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.auth import Role, RolePolicy


class RoleCRUD(BaseSyncCRUDOperations[Role]):
    """CRUD операции для ролей."""

    orm_model = Role

    def _modify_query_by_filters(self, query: Any, filters: dict[str, Any]) -> Any:
        """Переопределяем для обработки JOIN фильтров."""
        if "policy_id" in filters:
            policy_id = filters.pop("policy_id")
            query = query.join(RolePolicy).filter(RolePolicy.policy_id == policy_id)

        return super()._modify_query_by_filters(query, filters)
