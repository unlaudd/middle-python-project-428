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


def test_get_booking_success(client):
    """Успешный просмотр брони по коду и фамилии."""
    # 1. Создаем бронь
    flight_id = get_valid_flight_id(client)
    payload = {
        "flightId": flight_id,
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
    create_resp = client.post("/api/bookings", json=payload)
    booking_code = create_resp.json()["code"]

    # 2. Ищем её
    response = client.get(f"/api/bookings/{booking_code}?lastName=Петров")

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == booking_code
    assert data["status"] == "confirmed"


def test_get_booking_case_insensitive(client):
    """Поиск должен работать независимо от регистра и пробелов."""
    flight_id = get_valid_flight_id(client)
    payload = {
        "flightId": flight_id,
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
    booking_code = client.post("/api/bookings", json=payload).json()["code"]

    # Разный регистр и лишние пробелы
    response = client.get(f"/api/bookings/{booking_code}?lastName=  петров  ")
    assert response.status_code == 200
    assert response.json()["code"] == booking_code


def test_get_booking_not_found(client):
    """Неверный код или неверная фамилия должны давать 404."""
    flight_id = get_valid_flight_id(client)
    payload = {
        "flightId": flight_id,
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
    booking_code = client.post("/api/bookings", json=payload).json()["code"]

    # Неверная фамилия
    resp_wrong_name = client.get(f"/api/bookings/{booking_code}?lastName=Сидоров")
    assert resp_wrong_name.status_code == 404
    assert resp_wrong_name.json()["code"] == "not_found"

    # Неверный код
    resp_wrong_code = client.get("/api/bookings/FAKECODE?lastName=Петров")
    assert resp_wrong_code.status_code == 404
    assert resp_wrong_code.json()["code"] == "not_found"

    # Отсутствующий lastName
    resp_no_name = client.get(f"/api/bookings/{booking_code}")
    assert resp_no_name.status_code == 404
    assert resp_no_name.json()["code"] == "not_found"


def test_cancel_booking_success(client):
    """Успешная отмена брони меняет статус на cancelled."""
    flight_id = get_valid_flight_id(client)
    payload = {
        "flightId": flight_id,
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
    booking_code = client.post("/api/bookings", json=payload).json()["code"]

    response = client.post(
        f"/api/bookings/{booking_code}/cancel", json={"lastName": "Петров"}
    )

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == booking_code
    assert data["status"] == "cancelled"


def test_cancel_booking_repeated(client):
    """Повторная отмена уже отмененной брони должна возвращать 200 и cancelled."""
    flight_id = get_valid_flight_id(client)
    payload = {
        "flightId": flight_id,
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
    booking_code = client.post("/api/bookings", json=payload).json()["code"]

    # Первая отмена
    client.post(f"/api/bookings/{booking_code}/cancel", json={"lastName": "Петров"})

    # Повторная отмена
    response = client.post(
        f"/api/bookings/{booking_code}/cancel", json={"lastName": "Петров"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_booking_not_found(client):
    """Отмена с неверными данными должна давать 404."""
    flight_id = get_valid_flight_id(client)
    payload = {
        "flightId": flight_id,
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
    booking_code = client.post("/api/bookings", json=payload).json()["code"]

    # Неверная фамилия
    resp_wrong_name = client.post(
        f"/api/bookings/{booking_code}/cancel", json={"lastName": "Сидоров"}
    )
    assert resp_wrong_name.status_code == 404
    assert resp_wrong_name.json()["code"] == "not_found"

    # Отсутствующий lastName в теле
    resp_no_name = client.post(f"/api/bookings/{booking_code}/cancel", json={})
    assert resp_no_name.status_code == 404
    assert resp_no_name.json()["code"] == "not_found"
