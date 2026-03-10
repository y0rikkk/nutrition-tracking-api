"""Сервис проверки прав доступа."""

import re
from typing import Any
from uuid import UUID

from fastapi import Request
from sqlalchemy.ext.associationproxy import _AssociationList

from nutrition_tracking_api.api.exceptions import BadPermissionsError
from nutrition_tracking_api.api.schemas.auth.common import MatcherRule, PermissionRules
from nutrition_tracking_api.orm.models.auth import Policy, User

UUID4REGEX = re.compile("[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")


class PermissionService:
    """Сервис для проверки прав доступа на основе политик."""

    def validate_path_permissions(self, user: User, path: str, method: str, request: Request) -> bool:
        """
        Проверить права доступа пользователя для заданного пути.

        Суперпользователь всегда имеет доступ.
        Иначе проверяет политики из всех ролей пользователя.

        Args:
        ----
            user: ORM объект пользователя
            path: URL путь запроса
            method: HTTP метод
            request: FastAPI Request объект

        Returns:
        -------
            True если доступ разрешен

        Raises:
        ------
            BadPermissionsError: Если нет подходящей политики

        """
        if user.is_superuser:
            return True

        permitted_policies = [
            policy for role in user.roles for policy in role.policies if self.match_policy(policy, path, method)
        ]

        if permitted_policies:
            self.store_permitted_rules_to_state(user=user, policies=permitted_policies, request=request)
            return True

        raise BadPermissionsError

    @staticmethod
    def store_permitted_rules_to_state(user: User, policies: list[Policy], request: Request) -> None:
        """
        Конвертировать Policy → PermissionRules и сохранить в request.state.rules.

        Args:
        ----
            user: ORM объект пользователя
            policies: Список подходящих политик
            request: FastAPI Request объект

        """
        rules = []
        for policy in policies:
            if policy.matchers:
                matchers = [
                    MatcherRule(
                        field=matcher["field"],
                        condition=matcher.get("condition"),
                        value=get_matcher_value(matcher, user),
                    )
                    for matcher in policy.matchers
                ]
            else:
                matchers = None
            rules.append(
                PermissionRules(
                    matchers=matchers,
                    options=policy.options,
                )
            )
        request.state.rules = rules

    @staticmethod
    def match_policy(policy: Policy, path: str, method: str) -> bool:
        """
        Сопоставить URL запроса с targets политики.

        UUID в пути заменяются на {object_id}.
        Пример: /orders/[UUID]/ → /orders/{object_id}/

        Args:
        ----
            policy: ORM объект политики
            path: URL путь запроса
            method: HTTP метод

        Returns:
        -------
            True если путь и метод совпадают с политикой

        """
        replaced_path = re.sub(UUID4REGEX, "{object_id}", path)
        replaced_path_with_slash = replaced_path if replaced_path.endswith("/") else f"{replaced_path}/"
        replaced_path_without_slash = replaced_path[:-1] if replaced_path.endswith("/") else replaced_path

        return (
            replaced_path_with_slash in policy.targets or replaced_path_without_slash in policy.targets
        ) and method in policy.actions


def get_matcher_value(matcher: dict[str, Any], user: User) -> str | list[str]:
    """
    Подставить значение из объекта User для динамических матчеров ($user.<field>).

    Поддерживаемые форматы:
    - "$user.id"        → str(user.id)
    - "$user.role_ids"  → ["uuid1", "uuid2"]
    - "static_value"    → "static_value"

    Args:
    ----
        matcher: Словарь с данными матчера
        user: ORM объект пользователя

    Returns:
    -------
        Строковое или список строковых значений

    """
    value: str | list[str]
    if isinstance(matcher["value"], str) and matcher["value"].startswith("$user."):
        raw_value = user.__getattribute__(matcher["value"].split(".")[1])
        if isinstance(raw_value, (list, _AssociationList)):
            value = (
                (
                    [str(v) for v in raw_value]
                    if raw_value and isinstance(raw_value[0], (UUID, int, str))
                    else [str(v.id) for v in raw_value]
                )
                if raw_value
                else []
            )
        else:
            value = str(raw_value)
    else:
        value = matcher["value"]
    return value
