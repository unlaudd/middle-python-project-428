# 1) Собранный фронтенд Хекслета — забираем из npm-_package
FROM node:26-alpine AS frontend
WORKDIR /build
COPY package.json package-lock.json ./
RUN npm ci --omit=dev

# 2) Рантайм
FROM python:3.13-slim

# uv ставит зависимости по uv.lock — тот же менеджер, что и локально
COPY --from=ghcr.io/astral-sh/uv:0.12 /uv /usr/local/bin/uv

# make нужен, потому что образ запускается через `make start`
RUN apt-get update \
    && apt-get install -y --no-install-recommends make \
    && rm -rf /var/lib/apt/lists/*

# Логи без буферизации
ENV PYTHONUNBUFFERED=1
# Кеш uv и окружение проекта лежат на разных слоях образа
ENV UV_LINK_MODE=copy

WORKDIR /app

# --frozen: ставим ровно то, что в uv.lock. --no-dev: тесты и линтер в проде не нужны
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev

COPY . .
COPY --from=frontend /build/node_modules/@hexlet/python-flight-booking-frontend/dist/. ./public/

CMD ["make", "start"]