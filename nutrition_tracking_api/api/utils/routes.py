"""
Утилиты для автоматической генерации CRUD routes.

Основная функция: init_crud_routes() - создает стандартные endpoints для CRUD операций.
"""

from enum import StrEnum
from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import PlainTextResponse

from nutrition_tracking_api.api.schemas.filters import DeleteParameter
from nutrition_tracking_api.api.schemas.pagination import Page
from nutrition_tracking_api.api.services.base import BaseCRUDService
from nutrition_tracking_api.dependencies import (
    RequestStateDependency,
    RulesDependency,
    SessionDependency,
    UserDependency,
)


class ExcludeRoutersEnum(StrEnum):
    """
    Enum для исключения роутов.

    Используем значения отсюда для указания какой роут не создаем.
    """

    CREATE = "create"
    UPDATE = "update"
    DELETE = "delete"
    GET_ONE = "get_one"
    GET_MULTI = "get_multi"


def init_crud_routes(  # noqa: C901
    router: APIRouter,
    crud_service_class: type[BaseCRUDService[Any, Any, Any, Any, Any, Any]],
    exclude_routes: set[ExcludeRoutersEnum] | None = None,
) -> None:
    """
    Автоматически создать стандартные CRUD endpoints для router.

    Создаваемые endpoints:
    - GET / - Список объектов с фильтрацией и пагинацией
    - GET /{object_id} - Получить объект по ID
    - POST / - Создать новый объект
    - PATCH /{object_id} - Обновить объект
    - DELETE /{object_id} - Удалить объект

    Args:
    ----
        router: FastAPI router
        crud_service_class: Класс сервиса (наследник BaseCRUDService)
        exclude_routes: Множество роутов которые не нужно создавать

    Example:
    -------
        router = APIRouter(tags=["orders"])
        init_crud_routes(router, OrderService)

        # Исключить DELETE endpoint:
        init_crud_routes(
            router,
            OrderService,
            exclude_routes={ExcludeRoutersEnum.DELETE}
        )

    """
    if exclude_routes is None:
        exclude_routes = set()

    # GET / - Список объектов
    if ExcludeRoutersEnum.GET_MULTI not in exclude_routes:

        def get_multi(
            filters: Annotated[crud_service_class.filter_model, Depends()],  # type: ignore[name-defined]
            session: SessionDependency,
            request_state: RequestStateDependency,
            rules: RulesDependency,
            user: UserDependency,
        ) -> Any:
            items, count = crud_service_class(session, rules=rules, user=user, request_state=request_state).get_multi(
                filters
            )
            return Page(items=items, count=count)

        router.add_api_route(
            "/",
            summary="Получение объектов с учетом заданных фильтров",
            endpoint=get_multi,
            methods=["GET"],
            status_code=HTTPStatus.OK,
            response_model=Page[crud_service_class.out_model_multi],  # type: ignore[name-defined]
        )

    # GET /{object_id} - Получить объект по ID
    if ExcludeRoutersEnum.GET_ONE not in exclude_routes:

        def get_one(
            object_id: UUID,
            session: SessionDependency,
            request_state: RequestStateDependency,
            rules: RulesDependency,
            user: UserDependency,
        ) -> Any:
            return crud_service_class(session, rules=rules, user=user, request_state=request_state).get(object_id)

        router.add_api_route(
            "/{object_id}",
            summary="Получение объекта по id",
            endpoint=get_one,
            methods=["GET"],
            status_code=HTTPStatus.OK,
            response_model=crud_service_class.out_model,
        )

    # POST / - Создать новый объект
    if ExcludeRoutersEnum.CREATE not in exclude_routes:

        def create(
            create_data: crud_service_class.create_model,  # type: ignore[name-defined]
            session: SessionDependency,
            request_state: RequestStateDependency,
            rules: RulesDependency,
            user: UserDependency,
        ) -> Any:
            return crud_service_class(session, rules=rules, user=user, request_state=request_state).create(create_data)

        router.add_api_route(
            "/",
            summary="Создание нового объекта",
            endpoint=create,
            methods=["POST"],
            status_code=HTTPStatus.CREATED,
            response_model=crud_service_class.out_model,
        )

    # PATCH /{object_id} - Обновить объект
    if ExcludeRoutersEnum.UPDATE not in exclude_routes:

        def update(  # noqa: PLR0913
            object_id: UUID,
            obj_in: crud_service_class.update_model,  # type: ignore[name-defined]
            session: SessionDependency,
            request_state: RequestStateDependency,
            rules: RulesDependency,
            user: UserDependency,
        ) -> Any:
            return crud_service_class(session, rules=rules, user=user, request_state=request_state).update(
                object_id, obj_in
            )

        router.add_api_route(
            "/{object_id}",
            summary="Обновление объекта по id",
            endpoint=update,
            methods=["PATCH"],
            status_code=HTTPStatus.OK,
            response_model=crud_service_class.out_model,
        )

    # DELETE /{object_id} - Удалить объект
    if ExcludeRoutersEnum.DELETE not in exclude_routes:

        def delete(  # noqa: PLR0913
            object_id: UUID,
            session: SessionDependency,
            request_state: RequestStateDependency,
            rules: RulesDependency,
            user: UserDependency,
            force: bool = Query(
                default=False,
                description="Принудительное удаление (физическое удаление вместо soft delete)",
            ),
        ) -> Any:
            parameters = DeleteParameter(force=force)
            crud_service_class(session, rules=rules, user=user, request_state=request_state).delete(
                object_id, parameters
            )
            return PlainTextResponse("resource deleted successfully")

        router.add_api_route(
            "/{object_id}",
            summary="Удаление объекта по id",
            endpoint=delete,
            methods=["DELETE"],
            status_code=HTTPStatus.OK,
            response_class=PlainTextResponse,
        )
