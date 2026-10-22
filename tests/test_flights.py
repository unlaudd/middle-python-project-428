"""Tests for flight search and retrieval endpoints."""

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


def test_search_flights_success(client):
    """Successful flight search should return 200 and a list of objects."""
    date = get_test_date(1)  # Tomorrow
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
    """Search for the same city should return an empty list, not an error."""
    date = get_test_date(1)
    response = client.get(f"/api/flights?origin=MOW&destination=MOW&date={date}")

    assert response.status_code == 200
    assert response.json() == []


def test_search_flights_missing_params(client):
    """Missing required 'date' parameter should return 400."""
    response = client.get("/api/flights?origin=MOW&destination=LED")

    assert response.status_code == 400
    assert response.json() == {
        "code": "validation_error",
        "message": "Неверный формат или отсутствие обязательных параметров",
    }


def test_search_flights_invalid_passengers(client):
    """Passengers < 1 should return 400."""
    date = get_test_date(1)
    response = client.get(
        f"/api/flights?origin=MOW&destination=LED&date={date}&passengers=0"
    )

    assert response.status_code == 400
    assert response.json()["code"] == "validation_error"


def test_get_flight_by_id_success(client):
    """Retrieving an existing flight by ID should return 200 and the object."""
    date = get_test_date(1)
    # First, find any flight via search
    search_resp = client.get(f"/api/flights?origin=MOW&destination=LED&date={date}")
    flights = search_resp.json()

    assert flights, "No flights available for testing - seed data may be broken"

    flight_id = flights[0]["id"]

    response = client.get(f"/api/flights/{flight_id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == flight_id
    assert data["departureAt"].endswith("Z")


def test_get_flight_by_id_not_found(client):
    """Retrieving a non-existent flight should return 404."""
    response = client.get("/api/flights/NOPE_FAKE_ID")

    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Рейс не найден"}


def test_search_flights_correct_date_only(client):
    """Search should return flights only for the requested date."""
    date = get_test_date(1)  # Tomorrow
    response = client.get(
        f"/api/flights?origin=MOW&destination=LED&date={date}&passengers=1"
    )

    assert response.status_code == 200
    data = response.json()

    # All returned flights must have departure date matching the requested date
    for flight in data:
        departure_date = flight["departureAt"][:10]  # Extract YYYY-MM-DD
        assert departure_date == date, (
            f"Flight departs on {departure_date}, expected {date}"
        )
