"""Policy service."""

from nutrition_tracking_api.api.crud.auth.policy import PolicyCRUD
from nutrition_tracking_api.api.schemas.auth.policies import PolicyCreate, PolicyFilters, PolicyOut, PolicyUpdate
from nutrition_tracking_api.api.services.base import BaseCRUDService


class PolicyService(
    BaseCRUDService[
        PolicyCRUD,
        PolicyCreate,
        PolicyUpdate,
        PolicyOut,
        PolicyOut,
        PolicyFilters,
    ]
):
    """Сервис для управления политиками доступа."""

    create_model = PolicyCreate
    update_model = PolicyUpdate
    out_model = PolicyOut
    out_model_multi = PolicyOut
    resource_crud_class = PolicyCRUD
    filter_model = PolicyFilters

    track_history = True
