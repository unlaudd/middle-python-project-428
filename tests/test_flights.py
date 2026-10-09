"""Тесты для эндпоинтов поиска и получения рейсов."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Создает TestClient с корректным управлением lifespan."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def get_test_date(days_offset: int = 0) -> str:
    """Возвращает дату в формате YYYY-MM-DD со смещением от сегодня."""
    target_date = datetime.now(timezone.utc) + timedelta(days=days_offset)
    return target_date.strftime("%Y-%m-%d")


def test_search_flights_success(client):
    """Успешный поиск рейсов должен вернуть 200 и массив объектов."""
    date = get_test_date(1)  # Завтра
    response = client.get(
        f"/api/flights?origin=MOW&destination=LED&date={date}&passengers=1"
    )

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    if len(data) > 0:
        flight = data[0]
        assert "id" in flight
        assert "flightNumber" in flight
        assert flight["origin"]["code"] == "MOW"
        assert flight["destination"]["code"] == "LED"
        assert flight["departureAt"].endswith("Z")


def test_search_flights_empty_result(client):
    """Поиск по одинаковым городам должен вернуть пустой массив, а не ошибку."""
    date = get_test_date(1)
    response = client.get(f"/api/flights?origin=MOW&destination=MOW&date={date}")

    assert response.status_code == 200
    assert response.json() == []


def test_search_flights_missing_params(client):
    """Отсутствие обязательного параметра date должно вернуть 400."""
    response = client.get("/api/flights?origin=MOW&destination=LED")

    assert response.status_code == 400
    assert response.json() == {
        "code": "validation_error",
        "message": "Неверный формат или отсутствие обязательных параметров",
    }


def test_search_flights_invalid_passengers(client):
    """Passengers < 1 должен вернуть 400."""
    date = get_test_date(1)
    response = client.get(
        f"/api/flights?origin=MOW&destination=LED&date={date}&passengers=0"
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_get_flight_by_id_success(client):
    """Получение существующего рейса по ID должно вернуть 200 и объект."""
    date = get_test_date(1)
    # Сначала найдем любой рейс через поиск
    search_resp = client.get(f"/api/flights?origin=MOW&destination=LED&date={date}")
    flights = search_resp.json()

    if not flights:
        pytest.skip("Нет рейсов для тестирования (возможно, проблема с seed)")

    flight_id = flights[0]["id"]

    response = client.get(f"/api/flights/{flight_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == flight_id
    assert data["departureAt"].endswith("Z")


def test_get_flight_by_id_not_found(client):
    """Получение несуществующего рейса должно вернуть 404."""
    response = client.get("/api/flights/NOPE_FAKE_ID")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Рейс не найден"}
