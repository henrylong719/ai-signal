FROM python:3.12

ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy

# Install uv
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#installing-uv
COPY --from=ghcr.io/astral-sh/uv:0.9.26 /uv /uvx /bin/

# Use backend as the working directory
WORKDIR /app/backend

# Place virtual environment executables at the front of PATH
# Ref: https://docs.astral.sh/uv/guides/integration/docker/#using-the-environment
ENV PATH="/app/backend/.venv/bin:$PATH"

# Copy dependency files first for better Docker layer caching
COPY backend/pyproject.toml backend/uv.lock ./

# Install dependencies
# Do not use Docker cache mounts here because Railway's builder rejects them.
RUN uv sync --frozen --no-install-project

# Copy backend source code
COPY backend/app ./app
COPY backend/scripts ./scripts
COPY backend/alembic.ini ./alembic.ini

# Install the backend project itself
RUN uv sync --frozen

# Railway provides PORT dynamically.
# Use sh -c so ${PORT:-8000} is expanded correctly.
CMD ["sh", "-c", "fastapi run --host 0.0.0.0 --port ${PORT:-8000} app/main.py"]
