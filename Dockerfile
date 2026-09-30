# One image supports the API, worker, and UI through different runtime commands.
# Dependency resolution must match CI; uv refuses to change the committed lock.
FROM ghcr.io/astral-sh/uv:0.11.26 AS uv
FROM python:3.14-slim-bookworm AS dependencies
COPY --from=uv /uv /usr/local/bin/uv
ENV UV_PYTHON_DOWNLOADS=0 UV_LINK_MODE=copy
WORKDIR /app
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project

FROM python:3.14-slim-bookworm AS runtime
# psycopg uses system libpq; no compiler or uv is needed in the runtime image.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq5 ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --uid 10001 appuser
WORKDIR /app
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHON_DOTENV_DISABLED=1
COPY --from=dependencies /app/.venv /app/.venv
# Explicit copies prevent local secrets, logs, tests and Git history entering
# the image even if the build context contains extra files.
COPY Backend ./Backend
COPY FrontEnd ./FrontEnd
COPY app ./app
COPY main.py ./main.py
RUN mkdir -p /app/logs && chown appuser:appuser /app/logs
USER appuser
EXPOSE 8000 8501
CMD ["python", "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
