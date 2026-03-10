"""Custom exceptions for the application."""

from http import HTTPStatus
from typing import Any

from fastapi import HTTPException


class BaseError(HTTPException):
    """
    Базовый класс для всех кастомных исключений приложения.

    Все кастомные исключения должны наследоваться от этого класса.
    """

    status_code: int = HTTPStatus.INTERNAL_SERVER_ERROR
    detail: str = "Упс, такого мы не ожидали. Сообщите об этом команде разработки"

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        super(Exception, self).__init__(*args, **kwargs)


class ObjectNotFoundError(BaseError):
    """Объект не найден в базе данных."""

    status_code = HTTPStatus.NOT_FOUND
    detail = "Объект не найден в базе данных или недостаточно прав для выполнения операции"


class DuplicatedObjectError(BaseError):
    """Объект с такими данными уже существует."""

    status_code = HTTPStatus.BAD_REQUEST
    detail = "Ошибка. Схожий объект уже есть в базе данных"


class ImpossibleObjectError(BaseError):
    """Нарушены условия по атрибутам объекта."""

    status_code = HTTPStatus.BAD_REQUEST
    detail = "Нарушены условия по атрибутам объекта, проверьте введенные данные и попробуйте еще раз"


class AccessDeniedError(BaseError):
    """Недостаточно прав для выполнения операции."""

    status_code = HTTPStatus.FORBIDDEN
    detail = "Недостаточно прав для выполнения операции"


class BadPermissionsError(BaseError):
    """Недостаточно прав для выполнения операции."""

    status_code = HTTPStatus.FORBIDDEN
    detail = "Вам нужно больше прав для выполнения этого действия"


class AuthTokenValidateError(BaseError):
    """Токен для авторизации невалиден."""

    status_code = HTTPStatus.UNAUTHORIZED
    detail = "Токен для авторизации невалиден"


class AuthTokenExpiredError(BaseError):
    """Токен авторизации истек."""

    status_code = HTTPStatus.UNAUTHORIZED
    detail = "Токен авторизации истек"


class ForeignKeyConstraintError(BaseError):
    """Ошибка внешнего ключа."""

    status_code = HTTPStatus.BAD_REQUEST
    detail = "Ошибка внешнего ключа"


class DeletingViolatesForeignKeyConstraintError(BaseError):
    """Удаление нарушает ограничение внешнего ключа."""

    status_code = HTTPStatus.BAD_REQUEST
    detail = "Ошибка: Нарушение ограничения внешнего ключа. Сначала надо удалить зависимые сущности."


class UpdatingViolatesForeignKeyConstraintError(BaseError):
    status_code = HTTPStatus.BAD_REQUEST
    detail = "Ошибка: Нарушение ограничения внешнего ключа. Сначала надо удалить зависимые сущности."


class CannotAddByDeletedResourceError(BaseError):
    status_code = HTTPStatus.BAD_REQUEST
    detail = "Связанный ресурс удален, создание невозможно"


class CannotChangeDeletedResourceError(BaseError):
    status_code = HTTPStatus.BAD_REQUEST
    detail = "Ресурс удален, обновление невозможно"
