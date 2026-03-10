"""
Базовый Service класс для всей бизнес-логики.

Реализует паттерн Service layer с:
- Lifecycle hooks (pre/post create/update/delete)
- Validation hooks
- Каскадное удаление
- Интеграцию с CRUD layer
- Поддержку Permission Rules
- History tracking (track_history=True для включения)
"""

from abc import ABC
from collections.abc import Sequence
from typing import Any, Generic, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from nutrition_tracking_api.api.crud.base import BaseSyncCRUDOperations, OrmModelT
from nutrition_tracking_api.api.crud.core.history import HistoryCRUD
from nutrition_tracking_api.api.exceptions import (
    AccessDeniedError,
    CannotAddByDeletedResourceError,
    CannotChangeDeletedResourceError,
)
from nutrition_tracking_api.api.schemas.auth.common import PermissionRules
from nutrition_tracking_api.api.schemas.auth.user import UserOut
from nutrition_tracking_api.api.schemas.core.history import HistoryCreate, HistoryDiff
from nutrition_tracking_api.api.schemas.filters import BasePaginationFilter, DeleteParameter
from nutrition_tracking_api.api.utils.utils import dump_model
from nutrition_tracking_api.app_schemas import RequestState
from nutrition_tracking_api.orm.models.base import Base

ResourceCRUD = TypeVar("ResourceCRUD", bound=BaseSyncCRUDOperations[Any])
PydanticModelCreate = TypeVar("PydanticModelCreate", bound=BaseModel)
PydanticModelUpdate = TypeVar("PydanticModelUpdate", bound=BaseModel)
PydanticModelOut = TypeVar("PydanticModelOut", bound=BaseModel)
PydanticModelOutMulti = TypeVar("PydanticModelOutMulti", bound=BaseModel)
PydanticFiltersModel = TypeVar("PydanticFiltersModel", bound=BasePaginationFilter)
SqlAlchemyModel = TypeVar("SqlAlchemyModel", bound=Base)


class BaseCRUDService(
    ABC,
    Generic[
        ResourceCRUD,
        PydanticModelCreate,
        PydanticModelUpdate,
        PydanticModelOut,
        PydanticModelOutMulti,
        PydanticFiltersModel,
    ],
):
    """
    Базовый класс для сервисов с CRUD операциями.

    Generic параметры:
        ResourceCRUD: Класс CRUD
        PydanticModelCreate: Create schema
        PydanticModelUpdate: Update schema
        PydanticModelOut: Out schema (single)
        PydanticModelOutMulti: Out schema (list) - обычно = Out
        PydanticFiltersModel: Filter schema

    Attributes (обязательные для наследников):
        create_model: Класс Create схемы
        update_model: Класс Update схемы
        out_model: Класс Out схемы
        out_model_multi: Класс Out схемы для списка
        filter_model: Класс Filter схемы
        resource_crud_class: Класс CRUD
        track_history: Включить запись истории изменений (default: False)
    """

    create_model: type[PydanticModelCreate]
    update_model: type[PydanticModelUpdate]
    out_model: type[PydanticModelOut]
    out_model_multi: type[PydanticModelOutMulti]
    filter_model: type[PydanticFiltersModel]
    resource_crud_class: type[ResourceCRUD]

    track_history: bool = False

    def __init__(
        self,
        session: Session,
        rules: list[PermissionRules] | None = None,
        user: UserOut | None = None,
        request_state: RequestState | None = None,
    ) -> None:
        """
        Инициализация сервиса.

        Args:
        ----
            session: SQLAlchemy database session
            rules: Permission rules из request.state (передаются в CRUD)
            user: Текущий пользователь из request.state
            request_state: Состояние запроса (для request_id)

        """
        self.resource_crud = self.resource_crud_class(session, rules)
        self.history_repo = HistoryCRUD(session)
        self.request_id = request_state.request_id if request_state else None
        self.rules = rules
        self.user = user
        self.user_id = user.id if user else None

    def get(self, resource_id: UUID) -> PydanticModelOut:
        """
        Получить объект по ID.

        Args:
        ----
            resource_id: ID объекта

        Returns:
        -------
            Pydantic схема объекта

        Raises:
        ------
            NoResultFound: Если объект не найден

        """
        resource = self.resource_crud.get(resource_id, with_for_update=False)
        return self.out_model.model_validate(resource)

    def get_multi(
        self,
        filters: PydanticFiltersModel,
    ) -> tuple[list[PydanticModelOutMulti], int]:
        """
        Получить список объектов с пагинацией.

        Args:
        ----
            filters: Фильтры (включая limit, offset, order_by, desc)

        Returns:
        -------
            Tuple из (список объектов, общее количество)

        """
        filters_dict = filters.model_dump()
        resources = self.resource_crud.get_multi_out(filters_dict)
        return [self.out_model_multi.model_validate(resource) for resource in resources], self.resource_crud.get_count(
            filters_dict
        )

    # -------------------------------------------------------------------------
    # CREATE hooks
    # -------------------------------------------------------------------------

    def _handle_pre_create(self, create_data: PydanticModelCreate) -> None:
        """
        Пред-обработка создания сущности.

        Используется для выполнения связанных операций до создания сущности.
        Переопределить в наследниках при необходимости.

        Args:
        ----
            create_data: Данные создания

        Example:
        -------
            def _handle_pre_create(self, create_data: OrderCreate) -> None:
                # Проверка перед созданием
                if self.resource_crud.exists({"number": create_data.number}):
                    raise ValueError("Order with this number already exists")

        """

    def _validate_create_deleted_resource(self, resource: OrmModelT) -> bool:
        if resource.is_soft_deletable and resource.is_archive:  # type: ignore[attr-defined]
            return True
        return self._validate_on_archived_related_resources(resource)

    def _handle_post_create(
        self,
        resource: OrmModelT,
        create_data: PydanticModelCreate,  # noqa: ARG002
    ) -> None:
        """
        Пост-обработка создания сущности.

        Используется для выполнения связанных операций после создания сущности.
        Переопределить в наследниках при необходимости.

        Args:
        ----
            resource: Созданная сущность
            create_data: Данные создания

        Example:
        -------
            def _handle_post_create(self, resource: Order, create_data: OrderCreate) -> None:
                # Отправка уведомления
                send_notification(f"Order {resource.number} created")

        """
        if not self._validate_create_deleted_resource(resource):
            raise CannotAddByDeletedResourceError
        if self.track_history:
            self.store_history(resource, new_obj=dump_model(resource))

    def create(self, create_data: PydanticModelCreate) -> PydanticModelOut:
        """
        Создать новый объект.

        Args:
        ----
            create_data: Данные для создания

        Returns:
        -------
            Pydantic схема созданного объекта

        Raises:
        ------
            AccessDeniedError: Если нет доступа к созданному объекту

        """
        self._handle_pre_create(create_data)
        create_details = create_data.model_dump()
        if self.resource_crud.orm_model.add_actions_author and self.user_id is not None:
            create_details["creator_id"] = self.user_id
            create_details["modifier_id"] = self.user_id
        created_resource = self.resource_crud.create(create_details)
        self._handle_post_create(created_resource, create_data)
        try:
            resource = self.get(created_resource.id)
        except NoResultFound as e:
            raise AccessDeniedError from e
        return resource

    # -------------------------------------------------------------------------
    # UPDATE hooks
    # -------------------------------------------------------------------------

    def _get_resource_for_pre_update(self, resource_id: UUID) -> Any:
        """
        Получить сущность по идентификатору для контекста обновления.

        Переопределить в наследниках если нужна специальная логика получения.

        Args:
        ----
            resource_id: ID сущности

        Returns:
        -------
            Сущность

        """
        return self.resource_crud.get(resource_id, with_for_update=False)

    def _validate_on_archived_related_resources(
        self,
        resource: OrmModelT,  # noqa: ARG002
    ) -> bool:
        """
        Валидация сущности на наличие удаленных связанных сущностей.

        Переопределить в наследниках для проверки связанных объектов.

        Args:
        ----
            resource: Сущность для проверки

        Returns:
        -------
            True если сущность валидна

        Example:
        -------
            def _validate_on_deleted_related_resources(self, resource: Order) -> bool:
                # Проверить что customer не удален
                if resource.customer and resource.customer.is_archive:
                    return False
                return True

        """
        return True

    def _validate_update_deleted_resource(self, resource: OrmModelT, update_data: PydanticModelUpdate) -> bool:
        """
        Валидация обновления сущности.

        Проверяет можно ли обновить сущность с учетом soft delete.

        Args:
        ----
            resource: Сущность
            update_data: Данные обновления

        Returns:
        -------
            True если можно обновить

        Правила:
            - Можно обновить если модель не поддерживает soft delete
            - Можно обновить если is_archive=False
            - Можно "восстановить" архивированную сущность (update_data.is_archive=False)
            - Связанные сущности также не должны быть архивированы

        """
        return (
            # Или не поддерживает мягкое удаление
            not resource.is_soft_deletable
            # Или не удалена
            or resource.is_archive is False  # type: ignore[attr-defined]
            # Или восстанавливается
            or (hasattr(update_data, "is_archive") and update_data.is_archive is False)
        ) and (
            # Валидация по связанным сущностям
            self._validate_on_archived_related_resources(resource)
        )

    def _handle_pre_update(
        self,
        resource_id: UUID,
        update_data: PydanticModelUpdate,
    ) -> dict[str, Any]:
        """
        Пред-обработка обновления сущности.

        Используется для выполнения связанных операций до обновления сущности.
        Переопределить в наследниках при необходимости.

        Args:
        ----
            resource_id: ID сущности
            update_data: Данные обновления

        Returns:
        -------
            Контекст обновления (передается в _handle_post_update)

        Example:
        -------
            def _handle_pre_update(self, resource_id: UUID, update_data: OrderUpdate) -> dict:
                resource = self._get_resource_for_pre_update(resource_id)
                context = super()._handle_pre_update(resource_id, update_data)
                # Сохранить старый статус для логики
                context["old_status"] = resource.status
                return context

        """
        resource = self._get_resource_for_pre_update(resource_id)
        pre_update_context: dict[str, Any] = {"resource": resource}

        # Валидация обновления удаленного ресурса
        if not self._validate_update_deleted_resource(resource, update_data):
            raise CannotChangeDeletedResourceError

        if self.track_history:
            pre_update_context["resource_history"] = dump_model(resource)

        return pre_update_context

    def _handle_post_update(
        self,
        resource: OrmModelT,
        update_data: PydanticModelUpdate,  # noqa: ARG002
        pre_update_context: dict[str, Any],
    ) -> None:
        """
        Пост-обработка обновления сущности.

        Используется для выполнения связанных операций после обновления сущности.
        Переопределить в наследниках при необходимости.

        Args:
        ----
            resource: Обновленная сущность
            update_data: Данные обновления
            pre_update_context: Собранный до обновления контекст

        Example:
        -------
            def _handle_post_update(self, resource: Order, update_data: OrderUpdate, ctx: dict) -> None:
                super()._handle_post_update(resource, update_data, ctx)
                # Проверить изменение статуса
                if ctx.get("old_status") != resource.status:
                    send_notification(f"Order {resource.number} status changed")

        """
        if pre_update_context.get("resource_history"):
            self.store_history(
                resource,
                new_obj=dump_model(resource),
                old_obj=pre_update_context["resource_history"],
            )

    def update(
        self,
        resource_id: UUID,
        update_data: PydanticModelUpdate,
    ) -> PydanticModelOut:
        """
        Обновить объект.

        Args:
        ----
            resource_id: ID объекта
            update_data: Данные для обновления

        Returns:
        -------
            Pydantic схема обновленного объекта

        """
        pre_update_context = self._handle_pre_update(resource_id, update_data)
        update_details = update_data.model_dump(exclude_unset=True)
        if self.resource_crud.orm_model.add_actions_author and self.user_id is not None:
            update_details["modifier_id"] = self.user_id
        resource = self.resource_crud.update(resource_id, update_details)
        self._handle_post_update(resource, update_data, pre_update_context)
        return self.out_model.model_validate(resource)

    # -------------------------------------------------------------------------
    # DELETE hooks
    # -------------------------------------------------------------------------

    def _handle_cascade_delete(self, resources: Sequence[OrmModelT], parameters: DeleteParameter) -> None:
        """
        Каскадная обработка удаления сущностей.

        Переопределить в наследниках для удаления связанных объектов.

        Args:
        ----
            resources: Сущности которые будут удалены
            parameters: Параметры удаления

        Example:
        -------
            def _handle_cascade_delete(self, resources: list[Order], parameters: DeleteParameter) -> None:
                # Удалить все позиции заказов
                for order in resources:
                    self.resource_crud.session.query(OrderItem).filter_by(
                        order_id=order.id
                    ).delete()

        """

    def _handle_pre_delete(
        self,
        resource_id: UUID,
        parameters: DeleteParameter,
    ) -> dict[str, Any]:
        """
        Пред-обработка удаления сущности.

        Используется для выполнения связанных операций до удаления сущности.

        Args:
        ----
            resource_id: ID сущности
            parameters: Параметры удаления

        Returns:
        -------
            Контекст удаления (передается в _handle_post_delete)

        """
        resource = self.resource_crud.get(resource_id, with_for_update=False)
        pre_delete_context: dict[str, Any] = {"resource": resource}
        # Сохранение контекста для истории
        pre_delete_context.update(resource_history=dump_model(resource))
        self._handle_cascade_delete([resource], parameters)
        return pre_delete_context

    def _handle_post_delete(
        self,
        pre_delete_context: dict[str, Any],
        parameters: DeleteParameter,
    ) -> None:
        """
        Пост-обработка удаления сущности.

        Используется для выполнения связанных операций после удаления сущности.

        Args:
        ----
            pre_delete_context: Собранный до удаления контекст
            parameters: Параметры удаления

        """
        if not self.track_history:
            return
        if self.resource_crud.orm_model.is_soft_deletable and parameters.force is False:
            new_obj = pre_delete_context["resource_history"].copy()
            # Время архивирования и id пользователя в историю не попадают
            new_obj["is_archive"] = True
        else:
            new_obj = None
        self.store_history(
            pre_delete_context["resource"],
            old_obj=pre_delete_context["resource_history"],
            new_obj=new_obj,
        )

    def delete(
        self,
        resource_id: UUID,
        parameters: DeleteParameter,
    ) -> None:
        """
        Удалить объект.

        Args:
        ----
            resource_id: ID объекта
            parameters: Параметры удаления (force flag)

        """
        pre_delete_context = self._handle_pre_delete(resource_id, parameters)
        if parameters.force is False and self.resource_crud.orm_model.is_soft_deletable:
            self.resource_crud.update(
                resource_id,
                {
                    "is_archive": True,
                    "archived_at": func.now(),
                    "archiver_id": self.user_id,
                },
            )
        else:
            self.resource_crud.delete(resource_id)
        self._handle_post_delete(pre_delete_context, parameters)

    def _handle_pre_delete_multi_cascade(
        self,
        filters: dict[str, Any],
        parameters: DeleteParameter,
    ) -> dict[str, Any]:
        """
        Пред-обработка каскадного удаления сущностей по фильтрам.

        Args:
        ----
            filters: Фильтры для удаления
            parameters: Параметры удаления

        Returns:
        -------
            Контекст удаления

        """
        resources = self.resource_crud.get_multi(filters, with_for_update=False)
        pre_delete_context: dict[str, Any] = {"resources": resources}
        # Сохранение контекста для истории
        pre_delete_context["resources_history"] = [dump_model(r) for r in resources]
        self._handle_cascade_delete(resources, parameters)
        return pre_delete_context

    def _handle_post_delete_multi_cascade(
        self,
        pre_delete_context: dict[str, Any],
        parameters: DeleteParameter,
    ) -> None:
        """
        Пост-обработка каскадного удаления сущностей.

        Args:
        ----
            pre_delete_context: Собранный до удаления контекст
            parameters: Параметры удаления

        """
        if not self.track_history:
            return
        is_soft = self.resource_crud.orm_model.is_soft_deletable and parameters.force is False
        data = []
        for snapshot, resource in zip(
            pre_delete_context["resources_history"],
            pre_delete_context["resources"],
            strict=True,
        ):
            if is_soft:
                new_obj = snapshot.copy()
                new_obj["is_archive"] = True
            else:
                new_obj = None
            data.append((snapshot, new_obj, resource))
        self.store_history_multi(data=data)

    def delete_multi_cascade(
        self,
        filters: dict[str, Any],
        parameters: DeleteParameter,
    ) -> None:
        """
        Каскадное удаление нескольких сущностей по фильтрам.

        Args:
        ----
            filters: Фильтры для удаления
            parameters: Параметры удаления

        """
        pre_delete_context = self._handle_pre_delete_multi_cascade(filters, parameters)
        if parameters.force is False and self.resource_crud.orm_model.is_soft_deletable:
            self.resource_crud.update_by_filter(
                filters,
                {
                    "is_archive": True,
                    "archived_at": func.now(),
                    "archiver_id": self.user_id,
                },
            )
            self._handle_post_delete_multi_cascade(pre_delete_context, parameters)
            return
        self.resource_crud.delete_by_filter(filters)
        self._handle_post_delete_multi_cascade(pre_delete_context, parameters)

    # -------------------------------------------------------------------------
    # History tracking
    # -------------------------------------------------------------------------

    def _get_history_parent(self, resource: OrmModelT) -> tuple[UUID, str]:
        """
        Возвращает (parent_id, parent_type) для записи истории.

        По умолчанию возвращает id и имя класса самого объекта.
        Переопределить в конкретном сервисе, если нужна связь с родителем.

        Example:
        -------
            def _get_history_parent(self, resource: ConfigurationItem):
                return resource.configuration_id, "Configuration"

        """
        return resource.id, resource.__class__.__name__

    def _deserialize_history(  # noqa: PLR0913
        self,
        old_obj: dict[str, Any] | None,
        new_obj: dict[str, Any] | None,
        resource: OrmModelT,
        user_id: UUID | None = None,
        object_type: str | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> HistoryCreate | None:
        """
        Создать объект HistoryCreate из diff.

        Args:
        ----
            old_obj: Состояние до изменения
            new_obj: Состояние после изменения
            resource: ORM объект (для получения parent_id, parent_type)
            user_id: ID пользователя (если отличается от текущего)
            object_type: Тип объекта (если отличается от orm_model.__name__)
            extra_payload: Дополнительные данные в payload

        Returns:
        -------
            HistoryCreate или None если нет изменений

        """
        if old_obj == new_obj:
            return None

        parent_id, parent_type = self._get_history_parent(resource)

        return HistoryCreate(
            user_id=user_id or self.user_id,
            parent_id=parent_id,
            parent_type=parent_type,
            payload=HistoryDiff(old_obj=old_obj, new_obj=new_obj, extra_fields=extra_payload),
            object_type=object_type or self.resource_crud.orm_model.__name__,
            object_id=old_obj.get("id") if old_obj else new_obj.get("id"),  # type: ignore[union-attr]
        )

    def store_history(  # noqa: PLR0913
        self,
        resource: OrmModelT,
        old_obj: dict[str, Any] | None = None,
        new_obj: dict[str, Any] | None = None,
        user_id: UUID | None = None,
        object_type: str | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Сохранить запись в таблицу History.

        Args:
        ----
            resource: ORM объект (для получения parent_id, parent_type)
            old_obj: Состояние объекта до изменения
            new_obj: Состояние объекта после изменения
            user_id: ID пользователя (если отличается от текущего)
            object_type: Тип объекта (если отличается от orm_model.__name__)
            extra_payload: Дополнительные данные в payload

        """
        history = self._deserialize_history(old_obj, new_obj, resource, user_id, object_type, extra_payload)
        if not history:
            return
        history.request_id = UUID(self.request_id) if self.request_id else None
        self.history_repo.create(history.model_dump())

    def store_history_multi(
        self,
        data: list[tuple[dict[str, Any] | None, dict[str, Any] | None, OrmModelT]],
        user_id: UUID | None = None,
        object_type: str | None = None,
        extra_payload: dict[str, Any] | None = None,
    ) -> None:
        """
        Сохранить несколько записей в таблицу History (bulk insert).

        Args:
        ----
            data: Список кортежей (old_obj, new_obj, resource)
            user_id: ID пользователя (если отличается от текущего)
            object_type: Тип объекта (если отличается от orm_model.__name__)
            extra_payload: Дополнительные данные в payload

        """
        histories = []
        for old_obj, new_obj, resource in data:
            history = self._deserialize_history(old_obj, new_obj, resource, user_id, object_type, extra_payload)
            if history:
                history.request_id = UUID(self.request_id) if self.request_id else None
                histories.append(history.model_dump())
        if histories:
            self.history_repo.bulk_create(histories)
