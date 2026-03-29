"""FastAPI application instance."""

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

import sentry_sdk
from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from prometheus_client import CollectorRegistry
from prometheus_fastapi_instrumentator import Instrumentator, metrics
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware

from nutrition_tracking_api.api.dependencies.auth import validate_token
from nutrition_tracking_api.api.metrics.metrics import http_metrics_by_user
from nutrition_tracking_api.api.middlewares import LoggingMiddleware, RequestIDMiddleware
from nutrition_tracking_api.api.routes.auth import auth_router
from nutrition_tracking_api.api.routes.auth.token import router as public_auth_router
from nutrition_tracking_api.api.routes.core import core_router
from nutrition_tracking_api.api.routes.nutrition import nutrition_router
from nutrition_tracking_api.api.routes.root.routes import router as root_router
from nutrition_tracking_api.logger import init_logger
from nutrition_tracking_api.settings import settings

origins = [
    *settings.CORS_ORIGINS.split(","),
]


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:  # noqa: ARG001
    """
    Application lifespan event handler.

    Заменяет deprecated @app.on_event("startup") и @app.on_event("shutdown")
    """
    # Startup
    from loguru import logger

    logger.info(f"Starting {settings.APP_NAME} application")
    logger.info(f"Environment: {settings.ENV}")
    logger.info(f"Debug mode: {settings.DEBUG}")

    yield

    # Shutdown
    logger.info(f"Shutting down {settings.APP_NAME} application")


def create_app() -> FastAPI:
    """
    Создает и настраивает FastAPI приложение.

    Returns
    -------
        FastAPI: Настроенное приложение

    """
    dependencies = [Depends(validate_token)]

    app = FastAPI(
        title=settings.APP_NAME,
        description="Hello world",
        version="0.1.0",
        debug=settings.DEBUG,
        lifespan=lifespan,
    )

    # Include routers
    app.include_router(root_router)
    app.include_router(
        public_auth_router
    )  # Публичные endpoints: /auth/register/, /auth/login/, /auth/token/refresh/, /auth/logout/
    app.include_router(auth_router, dependencies=dependencies)
    app.include_router(core_router, dependencies=dependencies)
    app.include_router(nutrition_router, dependencies=dependencies)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    if settings.ENV != "dev":
        app.add_middleware(LoggingMiddleware)

    # Initialize Sentry and Prometheus
    init_sentry(app)
    init_prometheus(app)

    return app


IS_SENTRY_INITIALIZED = False


def init_sentry_sdk() -> None:
    global IS_SENTRY_INITIALIZED  # noqa: PLW0603
    if IS_SENTRY_INITIALIZED:
        return
    IS_SENTRY_INITIALIZED = True

    def traces_sampler(_: dict[Any, Any]) -> float:
        return 1.0

    sentry_sdk.init(
        traces_sampler=traces_sampler,
        environment=settings.ENV,
    )


def init_sentry(app_: FastAPI) -> None:
    init_sentry_sdk()
    app_.add_middleware(SentryAsgiMiddleware)


def init_prometheus(app_: FastAPI) -> None:
    """
    Инициализирует Prometheus метрики для приложения.

    Использует кастомный registry для изоляции метрик.
    Добавляет кастомные метрики (http_metrics_by_user) и дефолтные метрики.

    Args:
    ----
        app_: FastAPI приложение

    """
    api_registry = CollectorRegistry()

    instrumentator = Instrumentator(registry=api_registry)

    instrumentator.add(http_metrics_by_user(registry=api_registry))

    instrumentator.add(metrics.default(registry=api_registry))

    instrumentator.instrument(app_).expose(app_)


# Initialize logger
init_logger()

# Create app instance
app: FastAPI = create_app()


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "nutrition_tracking_api.api.main:app",
        host="0.0.0.0",  # noqa: S104
        port=8000,
        reload=settings.DEBUG,
        log_level=settings.LOG_LEVEL.lower(),
    )
