"""User service."""

from uuid import UUID

import loguru
from sqlalchemy.exc import NoResultFound
from sqlalchemy.orm import Session

from nutrition_tracking_api.api.crud.auth.role import RoleCRUD
from nutrition_tracking_api.api.crud.auth.user import UserCRUD
from nutrition_tracking_api.api.exceptions import ObjectNotFoundError, WrongCredentialsError
from nutrition_tracking_api.api.schemas.auth.common import PermissionRules
from nutrition_tracking_api.api.schemas.auth.token import RegisterRequest
from nutrition_tracking_api.api.schemas.auth.user import (
    UserCreate,
    UserFilters,
    UserOut,
    UserOutMulti,
    UserProfileUpdate,
    UserUpdate,
)
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

    def _handle_post_create(self, resource: User, create_data: UserCreate) -> None:  # type: ignore[override]
        """Назначить дефолтную роль всем новым пользователям."""
        self.add_default_role(resource.id)
        super()._handle_post_create(resource, create_data)

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
            WrongCredentialsError: Если пользователь не найден или пароль неверный

        """
        try:
            user = self.get_by_username(username)
        except Exception as e:
            raise WrongCredentialsError from e

        if not user.password_hash or not verify_password(password, user.password_hash):
            raise WrongCredentialsError

        return user

    def create_with_password(self, data: RegisterRequest) -> UserOut:
        """Создать нового пользователя с паролем (публичная регистрация)."""
        create_data = UserCreate(
            username=data.username,
            password=data.password,
            email=data.email,
            full_name=data.full_name,
            birth_date=data.birth_date,
            gender=data.gender,
            height_cm=data.height_cm,
            weight_kg=data.weight_kg,
            activity_level=data.activity_level,
            is_superuser=False,
            is_service_user=False,
        )
        return self.create(create_data)

    def get_me(self, user: User) -> UserOut:
        """Получить текущего пользователя."""
        return self.out_model.model_validate(user)

    def update_profile(self, user_id: UUID, profile_data: UserProfileUpdate) -> UserOut:
        """Обновить профиль текущего пользователя."""
        return self.update(user_id, profile_data)  # type: ignore[arg-type]
