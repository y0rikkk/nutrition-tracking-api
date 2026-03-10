"""
Базовый CRUD класс для всех операций с БД.

Реализует стандартные CRUD операции с поддержкой:
- Фильтрации с операторами (__like, __ilike, __eq, __gte, __in, и т.д.)
- Пагинации и сортировки
- Soft delete
- Eager loading relationships
- Permission rules (PermissionRules → SQL WHERE условия)
"""

from abc import ABC
from collections.abc import Sequence
from copy import deepcopy
from typing import Any, Generic, TypeVar
from uuid import UUID

from sqlalchemy import ColumnClause, delete, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import InstrumentedAttribute, Session
from sqlalchemy.sql import (
    Delete,
    Select,
    Update,
    and_,
    func,
    literal,
    literal_column,
    or_,
)

from nutrition_tracking_api.api.schemas.auth.common import Condition, PermissionRules
from nutrition_tracking_api.orm.models.base import Base as OrmBase

OrmModelT = TypeVar("OrmModelT", bound=OrmBase)
StatementT = TypeVar("StatementT", Select, Delete, Update)

OPERATOR_CONDITION_MAPPING = {
    "like": lambda column, val: column.like(f"%{val}%"),
    "ilike": lambda column, val: column.ilike(f"%{val}%"),
    "eq": lambda column, val: column == val,
    "ne": lambda column, val: column != val,
    "gte": lambda column, val: column >= val,
    "lte": lambda column, val: column <= val,
    "gt": lambda column, val: column > val,
    "lt": lambda column, val: column < val,
    "isnull": lambda column, val: (column.is_(None) if val is True else column.is_not(None)),
    "in": lambda column, val: column.in_(val if isinstance(val, list) else [val]),
    "not_in": lambda column, val: column.not_in(val),
    # for jsonb
    "contains_jsonb": lambda column, val: column.op("?")(val),
}


class BaseSyncCRUDOperations(ABC, Generic[OrmModelT]):
    """
    Базовый класс для CRUD операций с БД.

    Generic параметры:
        OrmModelT: Тип ORM модели

    Attributes
    ----------
        orm_model: Класс ORM модели
        session: SQLAlchemy сессия
        rule_clauses: SQL WHERE условия из PermissionRules

    """

    orm_model: type[OrmModelT]

    def __init__(self, session: Session, rules: list[PermissionRules] | None = None) -> None:
        """
        Инициализация CRUD.

        Args:
        ----
            session: SQLAlchemy database session
            rules: Список PermissionRules из request.state (конвертируются в SQL WHERE)

        """
        self.session = session
        self.rule_clauses = self._get_rule_clauses(rules)

    def _get_rule_clauses(self, rules: list[PermissionRules] | None) -> list[Any] | None:
        """
        Конвертировать PermissionRules в список SQL WHERE условий.

        Логика:
        - OR между политиками
        - AND внутри одной политики
        - Policy без matchers → None (полный доступ)
        - Policy с options → literal("false") (только Service проверяет)

        Args:
        ----
            rules: Список PermissionRules

        Returns:
        -------
            Список SQL clauses или None (полный доступ)

        """
        if not rules:
            return None

        or_clauses: list[Any] = []

        for rule in rules:
            # Если есть options — эта политика проверяется в Service, не в CRUD
            if rule.options:
                or_clauses.append(literal("false"))
                continue

            # Если нет matchers — полный доступ (нет ограничений по данным)
            if rule.matchers is None:
                return None

            # Собираем AND условия для одной политики
            and_clauses = []
            for matcher in rule.matchers:
                column = self._get_filtered_column(matcher.field)
                condition = matcher.condition or Condition.EQUAL
                clause = OPERATOR_CONDITION_MAPPING[condition](column, matcher.value)
                and_clauses.append(clause)

            if and_clauses:
                or_clauses.append(and_(*and_clauses))

        return or_clauses if or_clauses else None

    def _modify_query_by_rules(self, query: Select[tuple[OrmModelT]]) -> Select[tuple[OrmModelT]]:
        """
        Применить permission rules к запросу (WHERE OR(rule1, rule2, ...)).

        Args:
        ----
            query: Исходный запрос

        Returns:
        -------
            Запрос с примененными rules

        """
        if not self.rule_clauses:
            return query
        return query.where(or_(*self.rule_clauses))

    def create(self, details: dict[str, Any]) -> OrmModelT:
        """
        Создать новый объект.

        Args:
        ----
            details: Данные для создания

        Returns:
        -------
            Созданный объект

        """
        obj: OrmModelT = self.orm_model(**details)
        self.session.add(obj)
        self.session.flush([obj])
        self.session.refresh(obj)
        return obj

    def bulk_create(self, details_list: list[dict[str, Any]]) -> Sequence[OrmModelT]:
        """
        Массовое создание объектов.

        Args:
        ----
            details_list: Список данных для создания

        Returns:
        -------
            Список созданных объектов

        """
        insert_stmt = pg_insert(self.orm_model).values(details_list).on_conflict_do_nothing().returning(self.orm_model)
        objs = self.session.execute(insert_stmt)
        self.session.flush()
        return objs.scalars().all()

    def bulk_update(self, details_list: list[dict[str, Any]]) -> None:
        """
        Массовое обновление объектов.

        Args:
        ----
            details_list: Список данных для обновления (должны содержать id)

        """
        self.session.bulk_update_mappings(self.orm_model, details_list)  # type: ignore[arg-type]
        self.session.flush()

    def update(self, resource_id: UUID, details: dict[str, Any]) -> OrmModelT:
        """
        Обновить объект по ID.

        Намеренно НЕ применяет permission rules.
        Права проверяются через get() до вызова update().

        Args:
        ----
            resource_id: ID объекта
            details: Данные для обновления

        Returns:
        -------
            Обновленный объект

        Raises:
        ------
            NoResultFound: Если объект не найден

        """
        update_query = self._statement_update(resource_id, details)
        result = self.session.execute(update_query)
        resource: OrmModelT = result.scalars().one()
        self.session.flush([resource])
        self.session.refresh(resource)

        return resource

    def get(
        self,
        resource_id: UUID,
        with_for_update: bool,
    ) -> OrmModelT:
        """
        Получить объект по ID.

        Применяет permission rules.

        Args:
        ----
            resource_id: ID объекта
            with_for_update: Использовать SELECT FOR UPDATE (для транзакций)

        Returns:
        -------
            Объект

        Raises:
        ------
            NoResultFound: Если объект не найден или нет прав

        """
        query = self._statement_get(resource_id, with_for_update)
        result = self.session.execute(query)
        resource: OrmModelT = result.scalars().unique().one()

        return resource

    def get_one_or_none(
        self,
        resource_id: UUID,
        with_for_update: bool,
    ) -> OrmModelT | None:
        """
        Получить объект по ID или None.

        Args:
        ----
            resource_id: ID объекта
            with_for_update: Использовать SELECT FOR UPDATE

        Returns:
        -------
            Объект или None

        """
        query = self._statement_get(resource_id, with_for_update)
        result = self.session.execute(query)
        return result.scalars().unique().one_or_none()

    def _apply_joined_load(self, query: Select[tuple[OrmModelT]]) -> Select[tuple[OrmModelT]]:
        """
        Добавить joinedload() для eager loading relationships.

        Переопределить в наследниках для загрузки связанных объектов.

        Example:
        -------
            def _apply_joined_load(self, query):
                return query.options(joinedload(Order.items))

        Args:
        ----
            query: Исходный запрос

        Returns:
        -------
            Запрос с joinedload

        """
        return query

    def _statement_get(self, resource_id: UUID, with_for_update: bool) -> Select[tuple[OrmModelT]]:
        """
        Построить запрос для получения объекта по ID.

        Применяет permission rules.

        Args:
        ----
            resource_id: ID объекта
            with_for_update: Использовать SELECT FOR UPDATE

        Returns:
        -------
            SELECT запрос

        """
        query = select(self.orm_model).where(self.orm_model.id == resource_id)
        if with_for_update:
            query = query.with_for_update()
        query = self._apply_joined_load(query)
        return self._modify_query_by_rules(query)

    def _statement_update(self, resource_id: UUID, details: dict[str, Any]) -> Update:
        """
        Построить запрос для обновления объекта.

        Args:
        ----
            resource_id: ID объекта
            details: Данные для обновления

        Returns:
        -------
            UPDATE запрос

        """
        return update(self.orm_model).where(self.orm_model.id == resource_id).values(details).returning(self.orm_model)

    def _statement_delete(self, resource_id: UUID) -> Delete:
        """
        Построить запрос для удаления объекта.

        Args:
        ----
            resource_id: ID объекта

        Returns:
        -------
            DELETE запрос

        """
        return delete(self.orm_model).where(self.orm_model.id == resource_id)

    def _statement_get_multi(self, filters: dict[str, Any], with_for_update: bool) -> Select[tuple[OrmModelT]]:
        """
        Построить запрос для получения списка объектов с фильтрами.

        Применяет permission rules.

        Args:
        ----
            filters: Фильтры
            with_for_update: Использовать SELECT FOR UPDATE

        Returns:
        -------
            SELECT запрос

        """
        query = select(self.orm_model)
        if with_for_update:
            query = query.with_for_update()
        query = self._modify_query_by_filters(query, deepcopy(filters))
        return self._modify_query_by_rules(query)

    def _statement_get_count(self, filters: dict[str, Any]) -> Select[tuple[int]]:
        """
        Построить запрос для подсчета количества объектов.

        Args:
        ----
            filters: Фильтры

        Returns:
        -------
            SELECT COUNT запрос

        """
        query = self._statement_get_multi(filters, with_for_update=False)
        query = self._apply_joined_load(query)
        return select(func.count()).select_from(query.distinct().subquery())

    def _statement_get_multi_out(self, filters: dict[str, Any]) -> Select[tuple[OrmModelT]]:
        """
        Построить запрос для получения списка с пагинацией и сортировкой.

        Args:
        ----
            filters: Фильтры (включая limit, offset, order_by, desc)

        Returns:
        -------
            SELECT запрос

        """
        query = self._statement_get_multi(filters, with_for_update=False)
        query = self._apply_joined_load(query)
        query = self._apply_order_by(query, filters)
        return query.limit(filters.get("limit")).offset(filters.get("offset")).distinct()

    def get_multi_out(
        self,
        filters: dict[str, Any],
    ) -> Sequence[OrmModelT]:
        """
        Получить список объектов с пагинацией и сортировкой.

        Args:
        ----
            filters: Фильтры (включая limit, offset, order_by, desc)

        Returns:
        -------
            Список объектов

        """
        base_query = self._statement_get_multi_out(filters)
        results = self.session.execute(base_query)
        return results.scalars().unique().all()

    def get_multi(self, filters: dict[str, Any], with_for_update: bool) -> Sequence[OrmModelT]:
        """
        Получить список объектов по фильтрам без пагинации.

        Намеренно НЕ применяет permission rules — для внутренней валидации в сервисах.

        Args:
        ----
            filters: Фильтры
            with_for_update: Использовать SELECT FOR UPDATE

        Returns:
        -------
            Список объектов

        """
        base_query = self._statement_get_multi(filters, with_for_update)
        results = self.session.execute(base_query)
        return results.scalars().all()

    def get_count(
        self,
        filters: dict[str, Any],
    ) -> int:
        """
        Получить количество объектов по фильтрам.

        Args:
        ----
            filters: Фильтры

        Returns:
        -------
            Количество объектов

        """
        count_query = self._statement_get_count(filters)
        count = self.session.execute(count_query)
        return count.scalar() or 0

    def _get_filtered_column(self, field_name: str) -> InstrumentedAttribute[Any] | ColumnClause[Any]:
        """
        Получить колонку для фильтрации.

        Args:
        ----
            field_name: Название поля

        Returns:
        -------
            Колонка модели или literal_column

        """
        return getattr(self.orm_model, field_name, None) or literal_column(field_name)

    def _modify_query_by_filters(self, query: StatementT, filters: dict[str, Any]) -> StatementT:
        """
        Применить фильтры к запросу.

        Поддерживаемые операторы:
        - field__like: SQL LIKE %value%
        - field__ilike: Case-insensitive LIKE
        - field__eq: Равенство (или просто field)
        - field__ne: Неравенство
        - field__gte / field__lte: Больше/меньше или равно
        - field__in / field__not_in: IN / NOT IN
        - field__isnull: IS NULL / IS NOT NULL
        - field__contains_jsonb: JSONB оператор ?

        Args:
        ----
            query: Исходный запрос
            filters: Фильтры

        Returns:
        -------
            Запрос с примененными фильтрами

        """
        for key, val in {
            key: val for key, val in filters.items() if key not in ["limit", "offset", "order_by", "desc"]
        }.items():
            if "__" in key:
                field_name, op_name = key.split("__")
                filtered_column = self._get_filtered_column(field_name)
                query = query.where(
                    OPERATOR_CONDITION_MAPPING[op_name](filtered_column, val),
                )
            else:
                filtered_column = self._get_filtered_column(key)
                query = query.where(filtered_column == val)
        return query

    def delete_by_filter(self, filters: dict[str, Any]) -> None:
        """
        Удалить объекты по фильтрам.

        Args:
        ----
            filters: Фильтры для удаления

        """
        delete_query = delete(self.orm_model)
        delete_query = self._modify_query_by_filters(delete_query, deepcopy(filters))
        self.session.execute(delete_query)
        self.session.flush()

    def update_by_filter(self, filters: dict[str, Any], values: dict[str, Any]) -> None:
        """
        Обновить объекты по фильтрам.

        Args:
        ----
            filters: Фильтры для обновления
            values: Новые значения

        """
        update_query = update(self.orm_model).values(values)
        update_query = self._modify_query_by_filters(update_query, deepcopy(filters))
        self.session.execute(update_query)
        self.session.flush()

    def _get_ordered_column(self, field_name: str) -> InstrumentedAttribute[Any] | ColumnClause[Any]:
        """
        Получить колонку для сортировки.

        Args:
        ----
            field_name: Название поля

        Returns:
        -------
            Колонка модели или literal_column

        """
        return getattr(self.orm_model, field_name, None) or literal_column(field_name)

    def _apply_order_by(self, query: Select[tuple[OrmModelT]], filters: dict[str, Any]) -> Select[tuple[OrmModelT]]:
        """
        Применить сортировку к запросу.

        Args:
        ----
            query: Исходный запрос
            filters: Фильтры (содержат order_by и desc)

        Returns:
        -------
            Запрос с сортировкой

        """
        if order_by := filters.get("order_by"):
            ordered_column = self._get_ordered_column(order_by)
            desc = filters.get("desc", False)
            query = query.order_by(
                ordered_column.desc() if desc else ordered_column,
                self.orm_model.created_at,
            )
        else:
            query = query.order_by(self.orm_model.created_at)
        return query

    def delete(self, resource_id: UUID) -> None:
        """
        Удалить объект по ID.

        Намеренно НЕ применяет permission rules.
        Права проверяются через get() до вызова delete().

        Args:
        ----
            resource_id: ID объекта

        Raises:
        ------
            NoResultFound: Если объект не найден

        """
        res = self.session.execute(self._statement_delete(resource_id))
        self.session.flush()

        if res.rowcount == 0:  # type: ignore[attr-defined]
            raise NoResultFound

    def get_all_entities(self, with_for_update: bool) -> Sequence[OrmModelT]:
        """
        Получить все объекты без фильтров.

        Args:
        ----
            with_for_update: Использовать SELECT FOR UPDATE

        Returns:
        -------
            Список всех объектов

        """
        query = select(self.orm_model)
        if with_for_update:
            query = query.with_for_update()
        results = self.session.execute(query)
        return results.scalars().all()

    def _statement_get_by_filter(self, filters: dict[str, Any]) -> Select[tuple[OrmModelT]]:
        """
        Построить запрос для получения одного объекта по фильтрам.

        Args:
        ----
            filters: Фильтры

        Returns:
        -------
            SELECT запрос

        """
        query = select(self.orm_model)
        query = self._apply_order_by(query, filters)
        return self._modify_query_by_filters(query, deepcopy(filters)).limit(1)

    def get_one_by_filter(
        self,
        filters: dict[str, Any],
        with_for_update: bool,
    ) -> OrmModelT:
        """
        Получить один объект по фильтрам.

        Args:
        ----
            filters: Фильтры
            with_for_update: Использовать SELECT FOR UPDATE

        Returns:
        -------
            Объект

        Raises:
        ------
            NoResultFound: Если объект не найден

        """
        query = self._statement_get_by_filter(filters)
        if with_for_update:
            query = query.with_for_update()
        result = self.session.execute(query)
        resource: OrmModelT = result.scalars().one()

        return resource

    def _statement_exists(self, filters: dict[str, Any]) -> Select[tuple[bool]]:
        """
        Построить запрос для проверки существования объекта.

        Args:
        ----
            filters: Фильтры

        Returns:
        -------
            SELECT EXISTS запрос

        """
        query = self._statement_get_multi(filters, with_for_update=False)
        query = self._apply_joined_load(query)
        return select(query.exists())

    def exists(self, filters: dict[str, Any]) -> bool:
        """
        Проверить существование объекта по фильтрам.

        Args:
        ----
            filters: Фильтры

        Returns:
        -------
            True если объект существует

        """
        query = self._statement_exists(filters)
        result = self.session.execute(query)
        return result.scalar() is True

    def get_default_or_first(
        self, filters: dict[str, Any], default_field_name: str, with_for_update: bool
    ) -> OrmModelT:
        """
        Получить объект по фильтрам, если не найдено - убрать default_field_name и попробовать снова.

        Args:
        ----
            filters: Фильтры
            default_field_name: Поле для удаления из фильтров при fallback
            with_for_update: Использовать SELECT FOR UPDATE

        Returns:
        -------
            Объект

        Raises:
        ------
            NoResultFound: Если объект не найден даже после fallback

        """
        try:
            result = self.get_one_by_filter(filters, with_for_update)
        except NoResultFound:
            filters.pop(default_field_name)
            result = self.get_one_by_filter(filters, with_for_update)
        return result
