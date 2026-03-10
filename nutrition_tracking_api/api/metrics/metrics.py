"""Prometheus metrics for the application."""

from collections.abc import Callable

from prometheus_client import REGISTRY, CollectorRegistry, Counter, Histogram
from prometheus_fastapi_instrumentator.metrics import Info

from nutrition_tracking_api.api.metrics.utils import get_username_from_request


def http_metrics_by_user(
    registry: CollectorRegistry = REGISTRY,
    subsystem: str = "api",
    namespace: str = "nutrition_tracking_api",
    latency_highr_buckets: tuple[float, ...] = (
        0.01,
        0.025,
        0.05,
        0.075,
        0.1,
        0.25,
        0.5,
        0.75,
        1,
        1.5,
        2,
        2.5,
        3,
        3.5,
        4,
        4.5,
        5,
        7.5,
        10,
        30,
        60,
    ),
    latency_lowr_buckets: tuple[float, ...] = (0.1, 0.5, 1),
) -> Callable[[Info], None]:
    """
    Создает кастомные метрики для мониторинга HTTP запросов с учетом пользователей.

    Создает две метрики:
    1. Counter: Общее количество запросов с labels (method, status, path, user)
    2. Histogram (highr): Длительность запросов с высоким разрешением (много buckets, без labels)
       - Используется для точных перцентилей (p95, p99)
    3. Histogram (lowr): Длительность запросов с низким разрешением (мало buckets, с labels)
       - Используется для агрегации по endpoint/user

    Args:
    ----
        registry: Prometheus registry для регистрации метрик
        subsystem: Подсистема (префикс имени метрики)
        namespace: Namespace (префикс имени метрики)
        latency_highr_buckets: Buckets для histogram с высоким разрешением
        latency_lowr_buckets: Buckets для histogram с низким разрешением

    Returns:
    -------
        Функция инструментации для prometheus_fastapi_instrumentator

    """
    # Добавить inf bucket если его нет
    if latency_highr_buckets[-1] != float("inf"):
        latency_highr_buckets = (*latency_highr_buckets, float("inf"))

    if latency_lowr_buckets[-1] != float("inf"):
        latency_lowr_buckets = (*latency_lowr_buckets, float("inf"))

    # Counter: общее количество запросов
    total = Counter(
        name="http_requests_by_user",
        documentation="Total number of requests by method, status, path and user",
        labelnames=(
            "method",
            "status",
            "path",
            "user",
        ),
        registry=registry,
        namespace=namespace,
        subsystem=subsystem,
    )

    # Histogram: длительность с высоким разрешением (без labels)
    latency_highr = Histogram(
        name="http_request_duration_highr_seconds",
        documentation=(
            "Latency with many buckets but no API specific labels. Made for more accurate percentile calculations."
        ),
        buckets=latency_highr_buckets,
        namespace=namespace,
        subsystem=subsystem,
        registry=registry,
    )

    # Histogram: длительность с низким разрешением (с labels)
    latency_lowr = Histogram(
        name="http_request_duration_seconds",
        documentation=(
            "Latency with only few buckets by path. Made to be only used if aggregation by path is important."
        ),
        buckets=latency_lowr_buckets,
        labelnames=(
            "method",
            "path",
            "user",
            "status",
        ),
        namespace=namespace,
        subsystem=subsystem,
        registry=registry,
    )

    def instrumentation(info: Info) -> None:
        """
        Функция инструментации, вызываемая для каждого запроса.

        Args:
        ----
            info: Информация о запросе от instrumentator

        """
        # Получить username из request (из токена или "undefined")
        username = get_username_from_request(info.request)

        # Инкремент counter
        total.labels(
            info.request.method,
            info.modified_status,
            info.modified_handler,
            username,
        ).inc()

        # Histogram highr: только для успешных запросов (2xx)
        if info.modified_status.startswith("2"):
            latency_highr.observe(info.modified_duration)

        # Histogram lowr: для всех запросов
        latency_lowr.labels(
            path=info.modified_handler,
            method=info.method,
            status=info.modified_status,
            user=username,
        ).observe(info.modified_duration)

    return instrumentation
