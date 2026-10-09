"""Тесты для эндпоинта создания бронирования."""

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


def get_valid_flight_id(client) -> str:
    """Вспомогательная функция для получения валидного ID рейса."""
    date = get_test_date(1)
    resp = client.get(f"/api/flights?origin=MOW&destination=LED&date={date}")
    flights = resp.json()
    if not flights:
        pytest.skip("Нет доступных рейсов для тестирования")
    return flights[0]["id"]


def test_create_booking_success(client):
    """Успешное создание брони с одним пассажиром."""
    flight_id = get_valid_flight_id(client)

    payload = {
        "flightId": flight_id,
        "contact": {"email": "test@example.com", "phone": "+79991234567"},
        "passengers": [
            {
                "firstName": "Иван",
                "lastName": "Петров",
                "dateOfBirth": "1990-05-20",
                "documentNumber": "1",  # Минимально валидное значение по ТЗ
            }
        ],
    }

    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert len(data["code"]) == 6
    assert data["code"].isalnum()
    assert data["status"] == "confirmed"
    assert data["flight"]["id"] == flight_id
    assert len(data["passengers"]) == 1
    assert data["passengers"][0]["documentNumber"] == "1"


def test_create_booking_multiple_passengers(client):
    """Стоимость должна умножаться на количество пассажиров."""
    flight_id = get_valid_flight_id(client)

    # Сначала узнаем цену рейса
    flight_resp = client.get(f"/api/flights/{flight_id}")
    flight_price = flight_resp.json()["price"]["amount"]

    payload = {
        "flightId": flight_id,
        "contact": {"email": "test@example.com", "phone": "+79991234567"},
        "passengers": [
            {
                "firstName": "Иван",
                "lastName": "Петров",
                "dateOfBirth": "1990-05-20",
                "documentNumber": "1",
            },
            {
                "firstName": "Мария",
                "lastName": "Петрова",
                "dateOfBirth": "1992-08-15",
                "documentNumber": "2",
            },
        ],
    }

    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 201
    data = response.json()

    assert len(data["passengers"]) == 2
    assert data["totalPrice"]["amount"] == flight_price * 2


def test_create_booking_empty_passengers(client):
    """Пустой список пассажиров должен возвращать 400."""
    flight_id = get_valid_flight_id(client)

    payload = {
        "flightId": flight_id,
        "contact": {"email": "test@example.com", "phone": "+79991234567"},
        "passengers": [],
    }

    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_missing_field(client):
    """Отсутствие обязательного поля (например, lastName) должно возвращать 400."""
    flight_id = get_valid_flight_id(client)

    payload = {
        "flightId": flight_id,
        "contact": {"email": "test@example.com", "phone": "+79991234567"},
        "passengers": [
            {
                "firstName": "Иван",
                "dateOfBirth": "1990-05-20",
                "documentNumber": "1",
            }  # нет lastName
        ],
    }

    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_unknown_flight(client):
    """Неизвестный flightId должен возвращать 400."""
    payload = {
        "flightId": "FAKE_FLIGHT_ID_123",
        "contact": {"email": "test@example.com", "phone": "+79991234567"},
        "passengers": [
            {
                "firstName": "Иван",
                "lastName": "Петров",
                "dateOfBirth": "1990-05-20",
                "documentNumber": "1",
            }
        ],
    }

    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"
    assert "Неизвестный идентификатор рейса" in response.json()["message"]
