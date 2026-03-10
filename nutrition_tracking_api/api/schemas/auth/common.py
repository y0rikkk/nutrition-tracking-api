"""Общие схемы для системы аутентификации и авторизации."""

from enum import StrEnum
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SecretConfig(BaseModel):
    """RSA публичный ключ из JWKS endpoint для верификации JWT."""

    kty: str
    use: str
    kid: str
    e: str
    n: str
    alg: str


class Condition(StrEnum):
    """Операторы для матчеров в политиках."""

    LIKE = "like"
    ILIKE = "ilike"
    EQUAL = "eq"
    NOT_EQUAL = "ne"
    IN = "in"
    GTE = "gte"
    LTE = "lte"
    GT = "gt"
    LT = "lt"


class MatcherRule(BaseModel):
    """Одно правило фильтрации данных внутри политики."""

    field: str
    condition: Condition | None = None
    value: str | list[str]


class PermissionRules(BaseModel):
    """Runtime-объект с правилами из одной Policy. Хранится в request.state.rules."""

    matchers: list[MatcherRule] | None = None
    options: list[str] | None = None


class AuthorOut(BaseModel):
    """Минимальное представление пользователя для записей истории."""

    id: UUID
    username: str
    ad_login: str | None = None
    full_name: str | None = None
    master_id: int | None = None

    model_config = ConfigDict(from_attributes=True)


class UserShortOut(BaseModel):
    """Минимальное представление пользователя для creator, modifier, archiver."""

    id: UUID
    full_name: str | None = None
    username: str | None

    model_config = ConfigDict(from_attributes=True)
