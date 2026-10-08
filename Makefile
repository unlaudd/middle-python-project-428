.PHONY: help install build start clean contract test migrate seed

.DEFAULT_GOAL := help

help: ## Показать это справочное сообщение со списком доступных команд
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Установить зависимости проекта (Python через uv и Node.js через npm)
	uv sync
	npm ci

build: ## Собрать фронтенд и скопировать статические файлы в директорию public/
	rm -rf public/assets public/index.html
	mkdir -p public
	cp -R node_modules/@hexlet/python-flight-booking-frontend/dist/. public/

contract: ## Сгенерировать OpenAPI спецификацию из TypeSpec контракта
	npx tsp compile contract

migrate: ## Применить миграции базы данных
	uv run python -m app.migrate

seed: ## Залить справочные данные (идемпотентно)
	uv run python -m app.seed

start: migrate seed ## Применить миграции, залить данные и запустить сервер
	uv run uvicorn --factory app.main:create_app --host 0.0.0.0 --port $${PORT:-8080}

test: ## Запустить тесты с помощью pytest
	uv run pytest -v

clean: ## Очистить сгенерированные файлы, кэш и виртуальные окружения
	rm -rf public
	rm -rf .venv
	rm -rf node_modules
	rm -f uv.lock package-lock.json
	rm -f openapi.yaml