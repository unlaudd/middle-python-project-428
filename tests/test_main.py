"""Tests for the flight booking API.

Contains tests for verifying endpoint functionality,
SPA-fallback behavior, and API response format correctness.
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import create_app


@pytest.fixture
def client():
    """Create a TestClient for application testing.

    Using a context manager (with) ensures that lifespan events
    (startup/shutdown) are properly invoked, including the
    initialization of the database connection pool.

    Yields:
        TestClient: Client for making HTTP requests to the application.
    """
    app = create_app()
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture(autouse=True)
def ensure_public_dir():
    """Ensure public/index.html exists for SPA-fallback tests.

    Creates the public directory and index.html file if they don't exist,
    allowing tests to run even without executing make build.
    """
    public_dir = Path(__file__).parent.parent / "public"
    public_dir.mkdir(exist_ok=True)
    index_file = public_dir / "index.html"
    if not index_file.exists():
        index_file.write_text("<!DOCTYPE html><html><body>Mock</body></html>")


def test_health_check_get(client):
    """Test GET /api/health.

    Expected: status 200 and body {"status": "ok"}.
    """
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_health_check_head(client):
    """Test HEAD /api/health.

    Expected: status 200 with empty response body.
    """
    response = client.head("/api/health")
    assert response.status_code == 200
    assert response.text == ""


def test_api_cities_head(client):
    """Test HEAD /api/cities.

    Expected: status 200 for monitoring support.
    """
    response = client.head("/api/cities")
    assert response.status_code == 200


def test_spa_fallback(client):
    """Test SPA-fallback for direct links.

    GET /lookup should return HTML (index.html), not 404.
    """
    response = client.get("/lookup")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_api_unknown_path_404(client):
    """Test handling of unknown API paths.

    GET /api/unknown should return 404 in contract format:
    {"code": "not_found", "message": "Not Found"}.
    """
    response = client.get("/api/unknown")
    assert response.status_code == 404
    assert response.json() == {"code": "not_found", "message": "Not Found"}
