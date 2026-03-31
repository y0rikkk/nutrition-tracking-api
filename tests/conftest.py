"""Pytest fixtures for tests."""

from collections.abc import Generator
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pytest_mock import MockerFixture
from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from alembic.command import upgrade
from alembic.config import Config
from nutrition_tracking_api.api.main import app
from nutrition_tracking_api.api.schemas.auth.roles import RoleOut
from nutrition_tracking_api.api.schemas.auth.user import UserOut
from nutrition_tracking_api.api.services.auth.policy import PolicyService
from nutrition_tracking_api.api.services.auth.role import RoleService
from nutrition_tracking_api.api.services.auth.users import UserService
from nutrition_tracking_api.dependencies import get_session_generator
from nutrition_tracking_api.orm.models.auth import Policy, Role, User
from nutrition_tracking_api.orm.models.nutrition import FoodItem, MealEntry, MealFoodItem
from nutrition_tracking_api.settings import settings
from tests.factories.auth import PolicyFactory, RoleFactory, UserFactory
from tests.factories.nutrition.food_item import FoodItemFactory
from tests.factories.nutrition.meal_entry import MealEntryFactory
from tests.factories.nutrition.meal_food_item import MealFoodItemFactory

# Сервисный токен для тестового клиента
TEST_SERVICE_USER_TOKEN = "test_service_token"


@pytest.fixture(scope="session")
def test_engine() -> Engine:
    """Create test database engine."""
    return create_engine(
        settings.test_database_url,
        isolation_level="AUTOCOMMIT",
        pool_size=0,
    )


@pytest.fixture(scope="session", autouse=True)
def setup_test_db(alembic_config: Config) -> Any:
    """Применяет миграции к тестовой БД. Таблицы сохраняются между прогонами."""
    upgrade(alembic_config, "head")
    return


@pytest.fixture
def db_session(test_engine: Engine) -> Generator[Session, None, None]:
    """Create a new database session for a test, shared with FastAPI DI."""
    session = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)()
    app.dependency_overrides[get_session_generator] = lambda: session
    yield session
    app.dependency_overrides.pop(get_session_generator, None)
    session.close()


@pytest.fixture(autouse=True)
def truncate_tables(db_session: Session) -> Any:
    """
    Truncate all tables except alembic_version before each test.

    Гарантирует изоляцию тестов - каждый тест начинается с чистой БД.
    """
    result = db_session.execute(
        text(
            """
            SELECT tablename
            FROM pg_catalog.pg_tables
            WHERE schemaname = 'public'
            AND tablename != 'alembic_version'
            """
        )
    )
    tables = [row[0] for row in result]

    if not tables:
        return

    table_names = ", ".join(f"public.{table}" for table in tables)
    db_session.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture(scope="session")
def alembic_config() -> Config:
    """Alembic config с подключением к тестовой БД."""
    config = Config("alembic.ini")
    config.attributes["connection_url"] = settings.test_database_url
    return config


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """
    Create FastAPI test client.

    Передаёт сервисный токен — validate_token выполняется по реальному флоу,
    только verify_service_token мокается в _mock_service_auth.
    """
    with TestClient(app, headers={"XXX-Token-Authorization": TEST_SERVICE_USER_TOKEN}) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def _mock_service_auth(mocker: MockerFixture) -> None:
    """
    Autouse-фикстура: мокает verify_service_token для всех тестов.

    validate_token проходит реальный флоу (проверка публичных путей,
    извлечение токенов), но финальная верификация токена в БД обходится.
    """
    mocker.patch(
        "nutrition_tracking_api.api.services.auth.authorization.AuthService.verify_service_token",
        return_value=True,
    )


# ---------------------------------------------------------------------------
# Сервисные фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture
def test_user_service(db_session: Session) -> UserService:
    """UserService с тестовой сессией."""
    return UserService(db_session)


@pytest.fixture
def test_role_service(db_session: Session) -> RoleService:
    """RoleService с тестовой сессией."""
    return RoleService(db_session)


@pytest.fixture
def test_policy_service(db_session: Session) -> PolicyService:
    """PolicyService с тестовой сессией."""
    return PolicyService(db_session)


# ---------------------------------------------------------------------------
# Базовые фикстуры моделей
# ---------------------------------------------------------------------------


@pytest.fixture
def user() -> User:
    """Пользователь в БД без ролей."""
    return UserFactory()  # type: ignore[return-value]


@pytest.fixture
def superuser() -> User:
    """Суперпользователь в БД (is_superuser=True — обходит проверку политик).
    Username для исключения коллизий с обычными пользователями.
    """
    return UserFactory(is_superuser=True, username="superuser")  # type: ignore[return-value]


@pytest.fixture
def role() -> Role:
    """Роль в БД без политик."""
    return RoleFactory()  # type: ignore[return-value]


@pytest.fixture
def policy() -> Policy:
    """Политика в БД (targets: /auth/users/, actions: GET/POST/PATCH/DELETE)."""
    return PolicyFactory()  # type: ignore[return-value]


@pytest.fixture
def food_item() -> FoodItem:
    """FoodItem в БД."""
    return FoodItemFactory()  # type: ignore[return-value]


@pytest.fixture
def meal_entry() -> MealEntry:
    """MealEntry в БД (со своим пользователем)."""
    return MealEntryFactory()  # type: ignore[return-value]


@pytest.fixture
def meal_food_item(meal_entry: MealEntry) -> MealFoodItem:
    """MealFoodItem в БД, привязанный к meal_entry."""
    return MealFoodItemFactory(meal_entry=meal_entry)  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Составные auth-фикстуры
# ---------------------------------------------------------------------------


@pytest.fixture
def role_with_policy(
    role: Role,
    policy: Policy,
    test_role_service: RoleService,
) -> RoleOut:
    """Роль с привязанной политикой (targets: /auth/users/, actions: все)."""
    return test_role_service.add_policy(role_id=role.id, policy_id=policy.id)


@pytest.fixture
def user_with_permissions(
    user: User,
    role_with_policy: RoleOut,
    test_user_service: UserService,
) -> UserOut:
    """
    Пользователь с ролью и политикой (targets: /auth/users/).

    Использование в тесте:
        resp = client.get(
            "/auth/users/",
            headers={"Authorization": f"Bearer {user_with_permissions.access_token}"},
        )
    """
    return test_user_service.add_roles(user_id=user.id, role_ids=[role_with_policy.id])


@pytest.fixture
def make_user_with_permissions(
    test_user_service: UserService,
    test_role_service: RoleService,
) -> Any:
    """
    Fixture factory для создания пользователя с правами на произвольные пути.

    Использование в тесте:
        def test_something(client, make_user_with_permissions):
            user = make_user_with_permissions(
                targets=["/auth/roles/", "/auth/roles/{object_id}"],
                actions=["GET"],
            )
            resp = client.get(
                "/auth/roles/",
                headers={"Authorization": f"Bearer {user.access_token}"},
            )
            assert resp.status_code == 200

        # С matcher rules:
        def test_with_matcher(client, make_user_with_permissions):
            from nutrition_tracking_api.api.schemas.auth.common import MatcherRule
            user = make_user_with_permissions(
                targets=["/auth/users/{object_id}"],
                actions=["GET"],
                matchers=[MatcherRule(field="id", condition="eq", value="$user.id")],
            )
    """

    def _factory(
        targets: list[str],
        actions: list[str] | None = None,
        matchers: list[Any] | None = None,
        options: list[str] | None = None,
    ) -> UserOut:
        from tests.factories.auth import PolicyFactory, RoleFactory

        u: User = UserFactory()  # type: ignore[assignment]
        p: Policy = PolicyFactory(  # type: ignore[assignment]
            targets=targets,
            actions=actions or ["GET", "POST", "PATCH", "DELETE"],
            matchers=matchers,
            options=options,
        )
        r: Role = RoleFactory()  # type: ignore[assignment]
        test_role_service.add_policy(role_id=r.id, policy_id=p.id)
        return test_user_service.add_roles(user_id=u.id, role_ids=[r.id])

    return _factory


@pytest.fixture
def nutrition_user(
    test_user_service: UserService,
    test_role_service: RoleService,
) -> User:
    """Пользователь со всеми nutrition политиками из миграции.

    Имеет доступ ко всем nutrition endpoint'ам с матчерами по user_id.
    Используется в тестах, где требуется JWT Bearer аутентификация.
    """
    u: User = UserFactory()  # type: ignore[assignment]
    r: Role = RoleFactory()  # type: ignore[assignment]

    user_matcher = [{"field": "user_id", "condition": "eq", "value": "$user.id"}]
    meal_item_matcher = [{"field": "meal_entry.user_id", "condition": "eq", "value": "$user.id"}]

    for p in [
        PolicyFactory(
            targets=["/meals/", "/meals/{object_id}", "/meals/{object_id}/items/"],
            actions=["GET", "POST", "PATCH", "DELETE"],
            matchers=user_matcher,
        ),
        PolicyFactory(
            targets=["/meal-items/", "/meal-items/{object_id}"],
            actions=["GET", "POST", "PATCH", "DELETE"],
            matchers=meal_item_matcher,
        ),
        PolicyFactory(
            targets=["/foods/", "/foods/{object_id}"],
            actions=["GET", "POST", "PATCH", "DELETE"],
            matchers=None,
        ),
        PolicyFactory(
            targets=["/goals/", "/goals/{object_id}"],
            actions=["GET", "POST", "PATCH", "DELETE"],
            matchers=user_matcher,
        ),
        PolicyFactory(
            targets=["/weight-logs/", "/weight-logs/{object_id}"],
            actions=["GET", "POST", "PATCH", "DELETE"],
            matchers=user_matcher,
        ),
    ]:
        test_role_service.add_policy(role_id=r.id, policy_id=p.id)  # type: ignore[arg-type]

    # Сбросить кэш сессии: policies (viewonly=True) не инвалидируется при
    # изменениях через _role_policies (AssociationProxy), поэтому expire_all()
    # гарантирует свежую загрузку role.policies из БД при следующем доступе.
    test_role_service.resource_crud.session.expire_all()

    test_user_service.add_roles(user_id=u.id, role_ids=[r.id])
    return u
