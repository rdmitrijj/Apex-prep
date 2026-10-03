# Production image: builds the SPA, then serves it from FastAPI (one Render web service).
FROM node:22-alpine AS web
WORKDIR /web
COPY frontend/package.json frontend/yarn.lock ./
RUN yarn install --frozen-lockfile
COPY frontend/ ./
# Render passes service env vars as Docker build args; Vite inlines VITE_* at build time.
ARG VITE_DESMOS_API_KEY=""
ENV VITE_DESMOS_API_KEY=$VITE_DESMOS_API_KEY
RUN yarn build

FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /bin/uv
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_PROJECT_ENVIRONMENT=/venv PATH=/venv/bin:$PATH
WORKDIR /app/backend
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project
COPY backend/ ./
COPY --from=web /web/dist /app/frontend/dist
EXPOSE 8000
CMD ["sh", "-c", "alembic upgrade head && python -m app.seed && exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000} --proxy-headers --forwarded-allow-ips='*'"]
