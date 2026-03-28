"""User service."""

from collections import defaultdict
from typing import Any
from uuid import UUID

import loguru
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from nutrition_tracking_api.api.crud.auth.role import RoleCRUD
from nutrition_tracking_api.api.crud.auth.user import UserCRUD
from nutrition_tracking_api.api.exceptions import ObjectNotFoundError
from nutrition_tracking_api.api.schemas.auth.common import PermissionRules
from nutrition_tracking_api.api.schemas.auth.user import (
    UserCreate,
    UserFilters,
    UserOut,
    UserOutMulti,
    UserRoutePermissions,
    UserUpdate,
)
from nutrition_tracking_api.api.services.auth.permissions import get_matcher_value
from nutrition_tracking_api.api.services.base import BaseCRUDService
from nutrition_tracking_api.api.utils.auth import create_token, hash_password, verify_password
from nutrition_tracking_api.api.utils.utils import dump_model
from nutrition_tracking_api.app_schemas import RequestState
from nutrition_tracking_api.orm.models.auth import User


class UserService(
    BaseCRUDService[
        UserCRUD,
        UserCreate,
        UserUpdate,
        UserOut,
        UserOutMulti,
        UserFilters,
    ]
):
    """Сервис для управления пользователями."""

    create_model = UserCreate
    update_model = UserUpdate
    out_model = UserOut
    out_model_multi = UserOutMulti
    resource_crud_class = UserCRUD
    filter_model = UserFilters

    track_history = True

    def __init__(
        self,
        session: Session,
        rules: list[PermissionRules] | None = None,
        user: UserOut | None = None,
        request_state: RequestState | None = None,
    ) -> None:
        self.role_crud = RoleCRUD(session, rules)
        super().__init__(session, rules, user, request_state)

    def get_by_token(self, token: str) -> User:
        """
        Найти пользователя по access_token.

        Args:
        ----
            token: Access token

        Returns:
        -------
            ORM объект пользователя

        Raises:
        ------
            NoResultFound: Если пользователь не найден

        """
        return self.resource_crud.get_one_by_filter({"access_token": token}, with_for_update=False)

    def get_by_username(self, username: str) -> User:
        """
        Найти пользователя по username.

        Args:
        ----
            username: Имя пользователя

        Returns:
        -------
            ORM объект пользователя

        Raises:
        ------
            NoResultFound: Если пользователь не найден

        """
        return self.resource_crud.get_one_by_filter({"username": username}, with_for_update=False)

    def add_default_role(self, user_id: UUID) -> None:
        """
        Назначить роль по умолчанию новому пользователю.

        Args:
        ----
            user_id: ID пользователя

        """
        try:
            role = self.role_crud.get_one_by_filter({"is_default": True}, with_for_update=False)
            self.add_roles(user_id, [role.id])
        except NoResultFound:
            loguru.logger.warning(f"Default role not found for user {user_id}")

    def add_roles(self, user_id: UUID, role_ids: list[UUID]) -> UserOut:
        """
        Добавить роли пользователю.

        Args:
        ----
            user_id: ID пользователя
            role_ids: Список ID ролей для добавления

        Returns:
        -------
            UserOut схема обновлённого пользователя

        """
        user = self.resource_crud.get(user_id, with_for_update=False)
        old_user_data = dump_model(user, include_fields=["role_ids"])
        user.role_ids.extend(role_ids)
        self.resource_crud.session.flush()
        new_user_data = dump_model(user, include_fields=["role_ids"])
        self.store_history(
            resource=user,
            old_obj=old_user_data,
            new_obj=new_user_data,
        )
        return self.out_model.model_validate(user)

    def remove_roles(self, user_id: UUID, role_ids: list[UUID]) -> UserOut:
        """
        Удалить роли у пользователя.

        Args:
        ----
            user_id: ID пользователя
            role_ids: Список ID ролей для удаления

        Returns:
        -------
            UserOut схема обновлённого пользователя

        """
        user = self.resource_crud.get(user_id, with_for_update=False)
        old_user_data = dump_model(user, include_fields=["role_ids"])
        for role_id in role_ids:
            if role_id not in user.role_ids:
                raise ObjectNotFoundError
            user.role_ids.remove(role_id)
        self.resource_crud.session.flush()
        new_user_data = dump_model(user, include_fields=["role_ids"])
        self.store_history(
            resource=user,
            old_obj=old_user_data,
            new_obj=new_user_data,
        )
        return self.out_model.model_validate(user)

    def _handle_pre_create(self, create_data: UserCreate) -> None:
        """
        Для service users — генерировать токен, не устанавливать expires_at.
        Для обычных users — хешировать пароль если передан.

        Args:
        ----
            create_data: Данные создания пользователя

        """
        super()._handle_pre_create(create_data)
        if create_data.is_service_user:
            create_data.access_token = create_token(create_data.username)
            create_data.access_token_expires_at = None
        if create_data.password:
            create_data.password_hash = hash_password(create_data.password)
            create_data.password = None  # не хранить пароль в открытом виде

    def authenticate(self, username: str, password: str) -> User:
        """
        Проверить логин и пароль пользователя.

        Args:
        ----
            username: Имя пользователя
            password: Пароль в открытом виде

        Returns:
        -------
            ORM объект пользователя при успешной аутентификации

        Raises:
        ------
            AuthTokenValidateError: Если пользователь не найден или пароль неверный

        """
        from nutrition_tracking_api.api.exceptions import AuthTokenValidateError

        try:
            user = self.get_by_username(username)
        except Exception as e:
            raise AuthTokenValidateError from e

        if not user.password_hash or not verify_password(password, user.password_hash):
            raise AuthTokenValidateError

        return user

    def create_with_password(
        self, username: str, password: str, email: str | None = None, full_name: str | None = None
    ) -> User:
        """
        Создать нового пользователя с паролем (публичная регистрация).

        Args:
        ----
            username: Имя пользователя
            password: Пароль в открытом виде (будет захеширован)
            email: Email (опционально)
            full_name: Полное имя (опционально)

        Returns:
        -------
            ORM объект нового пользователя

        """
        db_user = self.resource_crud.create(
            {
                "username": username,
                "password_hash": hash_password(password),
                "email": email,
                "full_name": full_name,
                "is_superuser": False,
                "is_service_user": False,
            }
        )
        self.add_default_role(db_user.id)
        return self.resource_crud.get(db_user.id, with_for_update=False)

    def get_user_routes_permissions(self, user: User) -> UserRoutePermissions:
        results: dict[str, dict[str, list[Any]]] = defaultdict(dict)
        for role in user.roles:
            for policy in role.policies:
                result_matchers = {}
                if policy.matchers:
                    for matcher in policy.matchers:
                        result_matchers[matcher["field"]] = {
                            "value": get_matcher_value(matcher, user),
                            "condition": matcher["condition"],
                        }
                for target in policy.targets:
                    for action in policy.actions:
                        results[target].setdefault(action, []).append(
                            {"matchers": result_matchers, "options": policy.options}
                        )
        user_model = UserRoutePermissions.model_validate(user)
        user_model.permissions = results
        return user_model
