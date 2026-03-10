"""Loguru logger."""

from __future__ import annotations

import datetime
import json
import traceback
from typing import TypeVar

import loguru
from loguru import logger
from loguru._logger import Logger

from nutrition_tracking_api.settings import settings

# Сопоставление уровней логирования loguru
# https://loguru.readthedocs.io/en/stable/api/logger.html
ll = logger.level
_SAGE_LOG_LEVELS = {
    ll("TRACE").no: "TRACE",
    ll("DEBUG").no: "DEBUG",
    ll("INFO").no: "INFO",
    ll("SUCCESS").no: "INFO",
    ll("WARNING").no: "WARN",
    ll("ERROR").no: "ERROR",
    ll("CRITICAL").no: "CRITICAL",
}

LoggerT = TypeVar("LoggerT", bound=Logger)


def sink_serializer(message: loguru.Message) -> None:
    record = message.record

    simplified = {
        # Обязательные поля:
        "@timestamp": (record["time"].replace(tzinfo=datetime.UTC).isoformat(timespec="milliseconds")),
        "env": settings.ENV,
        "path": f"{record['file'].path}:{record['line']}",
        "message": record["message"],
        "extra": record["extra"],
        "exception": None,
    }

    # Добавить исключение если есть
    if (exception := record["exception"]) is not None:
        simplified["exception"] = {
            "type": repr(exception.type),
            "value": str(exception.value),
            "traceback": "".join(traceback.format_tb(exception.traceback)),
        }

    print(  # noqa: T201
        json.dumps(
            simplified,
            default=str,
            ensure_ascii=False,
        )
    )


IS_LOGGER_INITIALIZED = False


def init_logger(level: str = settings.LOG_LEVEL) -> None:
    """
    Инициализация логирования в loguru.

    - В режиме local/dev: дефолтный loguru (pretty print)
    - В режиме prod: JSON формат через sink_serializer

    Args:
    ----
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)

    """
    global IS_LOGGER_INITIALIZED  # noqa: PLW0603
    if IS_LOGGER_INITIALIZED:
        return
    IS_LOGGER_INITIALIZED = True

    if settings.ENV != "dev":
        logger.remove()
        logger.add(
            sink_serializer,
            level=level,
        )
