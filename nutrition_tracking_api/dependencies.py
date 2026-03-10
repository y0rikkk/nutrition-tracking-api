"""Global FastAPI dependencies."""

from collections.abc import Generator
from typing import Annotated

from fastapi import Depends, HTTPException, Request
from loguru import logger
from psycopg2 import errors as pg_errors
from sqlalchemy import text
from sqlalchemy.exc import (
    DatabaseError,
    IntegrityError,
    InvalidRequestError,
    MultipleResultsFound,
    NoResultFound,
)
from sqlalchemy.orm import Session

from nutrition_tracking_api.api.exceptions import (
    AccessDeniedError,
    BadPermissionsError,
    BaseError,
    DeletingViolatesForeignKeyConstraintError,
    DuplicatedObjectError,
    ForeignKeyConstraintError,
    ImpossibleObjectError,
    ObjectNotFoundError,
    UpdatingViolatesForeignKeyConstraintError,
)
from nutrition_tracking_api.api.schemas.auth.common import PermissionRules
from nutrition_tracking_api.api.schemas.auth.user import UserOut
from nutrition_tracking_api.app_schemas import RequestState
from nutrition_tracking_api.orm.database import SessionLocal
from nutrition_tracking_api.settings import settings


def log_db_error(
    exception: DatabaseError,
) -> None:
    operation_name = "Неизвестной операции"
    if exception.statement and exception.statement.startswith("CREATE"):
        operation_name = "Создания"
    elif exception.statement and exception.statement.startswith("UPDATE"):
        operation_name = "Изменения"
    elif exception.statement and exception.statement.startswith("DELETE"):
        operation_name = "Удаления"
    elif exception.statement and exception.statement.startswith("SELECT"):
        operation_name = "Выборки"
    elif exception.statement and exception.statement.startswith("INSERT"):
        operation_name = "Вставки"
    params = exception.params if exception.params else {}
    logger.opt(exception=True).error(
        "Ошибка при выполнении {}.\nПараметры: {},\nОшибка: {}",
        operation_name,
        params,
        exception,
    )


def log_invalid_request_error(
    error: InvalidRequestError | Exception,
) -> None:
    logger.opt(exception=True).error(
        "Ошибка при выполнении операции.\nОшибка: {}",
        error,
    )


def handle_integrity_error(e: IntegrityError) -> None:
    if isinstance(e.orig, pg_errors.UniqueViolation):
        raise DuplicatedObjectError from e
    if isinstance(e.orig, pg_errors.CheckViolation):
        raise ImpossibleObjectError from e
    if isinstance(e.orig, pg_errors.ForeignKeyViolation):
        if e.statement and e.statement.startswith("DELETE"):
            raise DeletingViolatesForeignKeyConstraintError from e
        if e.statement and e.statement.startswith("UPDATE"):
            raise UpdatingViolatesForeignKeyConstraintError from e
        raise ForeignKeyConstraintError from e
    raise BaseError from e


def get_session_generator() -> Session:
    return SessionLocal()


def get_session(session_generator: Session = Depends(get_session_generator)) -> Generator[Session, None, None]:
    """
    FastAPI dependency для получения database session.

    Yields
    ------
        Session: SQLAlchemy database session

    """
    with session_generator as session:
        if settings.DB_SCHEMA:
            session.execute(text(f"SET search_path TO {settings.DB_SCHEMA}"))
        try:
            yield session
            session.commit()
        except IntegrityError as e:
            log_db_error(e)
            session.rollback()
            handle_integrity_error(e)
            raise
        except NoResultFound as e:
            log_invalid_request_error(e)
            session.rollback()
            raise ObjectNotFoundError from e
        except (AccessDeniedError, BadPermissionsError) as e:
            log_invalid_request_error(e)
            session.rollback()
            raise BadPermissionsError from e
        except MultipleResultsFound as e:
            log_invalid_request_error(e)
            session.rollback()
            raise DuplicatedObjectError from e
        except HTTPException:
            session.rollback()
            raise
        except Exception as e:
            log_invalid_request_error(e)
            session.rollback()
            raise


def get_request_state(request: Request) -> RequestState:
    """
    Dependency для получения состояния запроса.

    Args:
    ----
        request: FastAPI Request объект

    Returns:
    -------
        RequestState: Состояние запроса с request_id

    """
    request_id = getattr(request.state, "request_id", None)
    return RequestState(request_id=request_id)


def get_permission_rules(request: Request) -> list[PermissionRules]:
    """
    Извлечь rules из request.state (заполняются в PermissionService).

    Args:
    ----
        request: FastAPI Request

    Returns:
    -------
        Список PermissionRules

    """
    try:
        return request.state.rules  # type: ignore[no-any-return]
    except AttributeError:
        return [PermissionRules(matchers=None)]


def get_request_user(request: Request) -> UserOut | None:
    """
    Извлечь текущего пользователя из request.state.

    Args:
    ----
        request: FastAPI Request

    Returns:
    -------
        UserOut или None если не аутентифицирован

    """
    try:
        return request.state.user  # type: ignore[no-any-return]
    except AttributeError:
        return None


# Type aliases для удобства использования в зависимостях
SessionDependency = Annotated[Session, Depends(get_session)]
RequestStateDependency = Annotated[RequestState, Depends(get_request_state)]
RulesDependency = Annotated[list[PermissionRules], Depends(get_permission_rules)]
UserDependency = Annotated[UserOut | None, Depends(get_request_user)]
