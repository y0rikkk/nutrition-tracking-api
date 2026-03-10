"""Root API endpoints."""

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse

from nutrition_tracking_api.app_schemas import HealthResponse
from nutrition_tracking_api.orm.database import check_db_health

router = APIRouter(tags=["root"])


@router.get("/")
def root() -> dict[str, str]:
    """
    Root endpoint.

    Returns
    -------
        dict: {"project": "nutrition_tracking_api"}

    """
    return {"project": "nutrition_tracking_api"}


@router.get("/healthz")
def healthz() -> HealthResponse:
    """
    Health check endpoint.

    Проверяет что приложение запущено и работает.

    Returns
    -------
        HealthResponse: {"status": "ok"}

    """
    return HealthResponse(status="ok")


@router.get("/readyz")
def readyz() -> HealthResponse:
    """
    Readiness check endpoint.

    Проверяет что приложение готово принимать запросы.

    Returns
    -------
        HealthResponse: {"status": "ok"}

    """
    return HealthResponse(status="ok")


@router.get("/healthdb", response_model=HealthResponse)
def healthdb() -> JSONResponse | HealthResponse:
    """
    Database health check endpoint.

    Проверяет подключение к базе данных.

    Returns
    -------
        HealthResponse: {"status": "ok"} если БД доступна
        JSONResponse: {"status": "error", "message": "..."} если БД недоступна (503)

    """
    if check_db_health():
        return HealthResponse(status="ok")

    return JSONResponse(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        content={"status": "error", "message": "Database is not available"},
    )
