FROM python:3.13-slim

LABEL description="Nutrition Tracking Api image"

USER root
ARG ENVIRONMENT=production
ENV ENVIRONMENT=${ENVIRONMENT}

# Install poetry
RUN pip install poetry

WORKDIR /app

# Copy dependency files
COPY pyproject.toml poetry.lock /app/

# Install system dependencies for development environment
RUN \
    if [ "$ENVIRONMENT" = "development" ]; \
    then \
        apt-get update && apt-get install -y --no-install-recommends \
        make \
        && apt-get autoclean && apt-get autoremove \
        && rm -rf /var/lib/apt/lists/* \
        && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/*; \
    else \
        echo "Production mode"; \
    fi \
    && poetry config virtualenvs.create false \
    && poetry install $(test "$ENVIRONMENT" != development && echo "--only main") --no-interaction --no-ansi

# Copy application code
COPY ./nutrition_tracking_api ./nutrition_tracking_api

# Create non-root user
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

WORKDIR /app

ARG APP_VERSION
ENV APP_VERSION=$APP_VERSION

ENV PYTHONPATH=/app:$PYTHONPATH

CMD ["uvicorn", "nutrition_tracking_api.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
