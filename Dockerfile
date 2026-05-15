FROM python:3.10
COPY --from=ghcr.io/astral-sh/uv:0.9.24 /uv /uvx /bin/

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

COPY pyproject.toml uv.lock README.md LICENSE /app/
RUN uv sync --frozen --no-dev --no-install-project
COPY karmabot /app/karmabot
COPY start.sh /app/main
RUN uv sync --frozen --no-dev && chmod +x /app/main

ENTRYPOINT ["/app/main"]
