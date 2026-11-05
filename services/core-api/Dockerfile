# ClearTrace core-api image. Evaluation-only licence (see LICENSE).
# Application dependencies are gated by docs/LICENSE_POLICY.md.
# OS packages from the Debian base are listed in
# docs/licence_exceptions/SHIPPED_IMAGE_OS_PACKAGES.md.
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS build
WORKDIR /src
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock README.md LICENSE NOTICE ./
COPY packages packages
COPY services services
COPY db db
COPY api api
RUN uv sync --frozen --no-dev --all-packages --no-install-project \
 && uv sync --frozen --no-dev --all-packages

FROM python:3.12-slim-bookworm AS runtime
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH" \
    CLEARTRACE_PACKS_ROOT=/app/policies/packs
WORKDIR /app
RUN useradd --create-home --uid 10001 cleartrace
COPY --from=build /src/.venv /app/.venv
COPY --from=build /src/packages /app/packages
COPY --from=build /src/services /app/services
COPY --from=build /src/db /app/db
COPY --from=build /src/api /app/api
COPY policies /app/policies
COPY LICENSE NOTICE README.md pyproject.toml ./
USER cleartrace
EXPOSE 8000
CMD ["cleartrace-api"]
