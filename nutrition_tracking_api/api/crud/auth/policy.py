"""Policy CRUD operations."""

from typing import Any

from sqlalchemy import String, cast

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations
from nutrition_tracking_api.orm.models.auth import Policy


class PolicyCRUD(BaseSyncCRUDOperations[Policy]):
    """CRUD операции для политик."""

    orm_model = Policy

    def _modify_query_by_filters(self, query: Any, filters: dict[str, Any]) -> Any:
        """Поиск по JSONB полям (targets, actions, options)."""
        if "target__ilike" in filters:
            value = filters.pop("target__ilike")
            query = query.filter(cast(Policy.targets, String).ilike(f"%{value}%"))

        if "action__ilike" in filters:
            value = filters.pop("action__ilike")
            query = query.filter(cast(Policy.actions, String).ilike(f"%{value}%"))

        if "option__ilike" in filters:
            value = filters.pop("option__ilike")
            query = query.filter(
                Policy.options.isnot(None),
                cast(Policy.options, String).ilike(f"%{value}%"),
            )

        return super()._modify_query_by_filters(query, filters)
