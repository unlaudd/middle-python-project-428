"""Tests for the booking creation endpoint."""

from datetime import datetime, timedelta, timezone

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create a TestClient with proper lifespan management."""
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


def get_test_date(days_offset: int = 0) -> str:
    """Return a date in YYYY-MM-DD format with an offset from today."""
    target_date = datetime.now(timezone.utc) + timedelta(days=days_offset)
    return target_date.strftime("%Y-%m-%d")


def get_valid_flight_id(client) -> str:
    """Helper function to get a valid flight ID."""
    date = get_test_date(1)
    resp = client.get(f"/api/flights?origin=MOW&destination=LED&date={date}")
    flights = resp.json()
    if not flights:
        pytest.skip("Нет доступных рейсов для тестирования")
    return flights[0]["id"]


def test_create_booking_success(client):
    """Successful booking creation with one passenger."""
    flight_id = get_valid_flight_id(client)

    payload = {
        "flightId": flight_id,
        "contact": {"email": "test@example.com", "phone": "+79991234567"},
        "passengers": [
            {
                "firstName": "Иван",
                "lastName": "Петров",
                "dateOfBirth": "1990-05-20",
                "documentNumber": "1",  # Minimal valid value per requirements
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
    """Total price should be multiplied by the number of passengers."""
    flight_id = get_valid_flight_id(client)

    # First, get the flight price
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
    """Empty passenger list should return 400."""
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
    """Missing required field (e.g., lastName) should return 400."""
    flight_id = get_valid_flight_id(client)

    payload = {
        "flightId": flight_id,
        "contact": {"email": "test@example.com", "phone": "+79991234567"},
        "passengers": [
            {
                "firstName": "Иван",
                "dateOfBirth": "1990-05-20",
                "documentNumber": "1",
            }  # missing lastName
        ],
    }

    response = client.post("/api/bookings", json=payload)

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_create_booking_unknown_flight(client):
    """Unknown flightId should return 400."""
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
    """Successful booking retrieval by code and last name."""
    # 1. Create a booking
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

    # 2. Retrieve it
    response = client.get(f"/api/bookings/{booking_code}?lastName=Петров")

    assert response.status_code == 200
    data = response.json()
    assert data["code"] == booking_code
    assert data["status"] == "confirmed"


def test_get_booking_case_insensitive(client):
    """Search should work regardless of case and extra spaces."""
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

    # Different case and extra spaces
    response = client.get(f"/api/bookings/{booking_code}?lastName=  петров  ")
    assert response.status_code == 200
    assert response.json()["code"] == booking_code


def test_get_booking_not_found(client):
    """Incorrect code or last name should return 404."""
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

    # Incorrect last name
    resp_wrong_name = client.get(f"/api/bookings/{booking_code}?lastName=Сидоров")
    assert resp_wrong_name.status_code == 404
    assert resp_wrong_name.json()["code"] == "not_found"

    # Incorrect code
    resp_wrong_code = client.get("/api/bookings/FAKECODE?lastName=Петров")
    assert resp_wrong_code.status_code == 404
    assert resp_wrong_code.json()["code"] == "not_found"

    # Missing lastName
    resp_no_name = client.get(f"/api/bookings/{booking_code}")
    assert resp_no_name.status_code == 404
    assert resp_no_name.json()["code"] == "not_found"


def test_cancel_booking_success(client):
    """Successful booking cancellation changes status to cancelled."""
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
    """Repeated cancellation of an already cancelled booking.

    Should return 200 and status 'cancelled'.
    """
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

    # First cancellation
    client.post(f"/api/bookings/{booking_code}/cancel", json={"lastName": "Петров"})

    # Repeated cancellation
    response = client.post(
        f"/api/bookings/{booking_code}/cancel", json={"lastName": "Петров"}
    )

    assert response.status_code == 200
    assert response.json()["status"] == "cancelled"


def test_cancel_booking_not_found(client):
    """Cancellation with incorrect data should return 404."""
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

    # Incorrect last name
    resp_wrong_name = client.post(
        f"/api/bookings/{booking_code}/cancel", json={"lastName": "Сидоров"}
    )
    assert resp_wrong_name.status_code == 404
    assert resp_wrong_name.json()["code"] == "not_found"

    # Missing lastName in body
    resp_no_name = client.post(f"/api/bookings/{booking_code}/cancel", json={})
    assert resp_no_name.status_code == 404
    assert resp_no_name.json()["code"] == "not_found"
