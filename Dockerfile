# syntax=docker/dockerfile:1.7

# -----------------------------------------------------------------------------
# Build stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS builder

# Install uv
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

WORKDIR /app

# Copy dependency manifests first for layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into a project-local venv
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_PYTHON_DOWNLOADS=never

RUN uv sync --frozen --no-install-project --no-dev

# Copy application source
COPY README.md LICENSE ./
COPY src ./src

# Install the project itself
RUN uv sync --frozen --no-dev


# -----------------------------------------------------------------------------
# Runtime stage
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

# Non-root user for security
RUN groupadd --system --gid 1000 aggregator \
    && useradd --system --uid 1000 --gid aggregator --create-home aggregator

WORKDIR /app

# Copy the fully-populated venv and source from the build stage
COPY --from=builder --chown=aggregator:aggregator /app /app

# Put the venv on PATH
ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    AGGREGATOR_TRANSPORT=http \
    AGGREGATOR_HOST=0.0.0.0 \
    AGGREGATOR_PORT=9000

USER aggregator

EXPOSE 9000

# Basic healthcheck — TCP connect on the HTTP port
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import socket; s=socket.create_connection(('127.0.0.1', 9000), 5); s.close()" || exit 1

ENTRYPOINT ["support-aggregator"]