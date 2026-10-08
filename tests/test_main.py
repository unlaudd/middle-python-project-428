"""Тесты для API бронирования авиабилетов.

Содержит тесты для проверки работоспособности эндпоинтов,
SPA-fallback и корректности форматов ответов согласно контракту API.
"""
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Создает TestClient для тестирования приложения.

    Использование контекстного менеджера (with) гарантирует,
    что события lifespan (startup/shutdown) будут корректно
    вызваны, включая инициализацию пула подключений к БД.

    Yields:
        TestClient: Клиент для выполнения HTTP-запросов к приложению.
    """
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def ensure_public_dir():
    """Гарантирует наличие public/index.html для тестов SPA-fallback.

    Создает директорию public и файл index.html, если они отсутствуют,
    чтобы тесты могли работать даже без запуска make build.
    """
    public_dir = Path(__file__).parent.parent / "public"
    public_dir.mkdir(exist_ok=True)
    index_file = public_dir / "index.html"
    if not index_file.exists():
        index_file.write_text("<!DOCTYPE html><html><body>Mock</body></html>")


def test_health_check_get(client):
    """Проверяет GET /api/health.

    Ожидается статус 200 и тело {"status": "ok"}.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_head(client):
    """Проверяет HEAD /api/health.

    Ожидается статус 200 без тела ответа.
    """
    response = client.head("/api/health")
    assert response.status_code == 200
    assert response.text == ""


def test_api_cities_head(client):
    """Проверяет HEAD /api/cities.

    Ожидается статус 200 для поддержки мониторингов.
    """
    response = client.head("/api/cities")
    assert response.status_code == 200


def test_spa_fallback(client):
    """Проверяет SPA-fallback для прямых ссылок.

    GET /lookup должен возвращать HTML (index.html), а не 404.
    """
    response = client.get("/lookup")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_api_unknown_path_404(client):
    """Проверяет обработку неизвестных API путей.

    GET /api/unknown должен возвращать 404 в формате контракта:
    {"code": "not_found", "message": "Not Found"}.
    """
    response = client.get("/api/unknown")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Not Found"}
