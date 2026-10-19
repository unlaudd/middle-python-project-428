"""Main module for the flight booking application.

Contains the FastAPI application factory, API routes, and logic
for serving static files with SPA-fallback support for proper
client-side routing.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.db import get_db_pool, lifespan
from app.queries import (
    cancel_booking,
    create_booking,
    get_and_verify_booking,
    get_flight_by_id,
    get_flights,
)
from app.schemas import BookingRequest, CancelBookingRequest


def format_datetime(dt) -> str:
    """Format a datetime object to ISO 8601 with a 'Z' (UTC) suffix.

    Args:
        dt: The datetime object to format.

    Returns:
        str: The formatted datetime string, or an empty string if dt is None.
    """
    if dt is None:
        return ""
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_flight(row: dict) -> dict:
    """Transform a flat database row into the API response structure for a flight.

    Args:
        row: A dictionary representing a flat database row.

    Returns:
        dict: The formatted flight data matching the API contract.
    """
    return {
        "id": row["id"],
        "flightNumber": row["flight_number"],
        "airline": {
            "code": row["airline_code"],
            "name": row["airline_name"],
        },
        "origin": {
            "code": row["origin_code"],
            "name": row["origin_name"],
            "country": row["origin_country"],
        },
        "destination": {
            "code": row["dest_code"],
            "name": row["dest_name"],
            "country": row["dest_country"],
        },
        "departureAt": format_datetime(row["departure_at"]),
        "arrivalAt": format_datetime(row["arrival_at"]),
        "durationMinutes": row["duration_minutes"],
        "price": {
            "amount": row["price_amount"],
            "currency": "RUB",
        },
        "seatsAvailable": row["seats_available"],
    }


def format_booking(booking_row: dict, passenger_rows: list[dict]) -> dict:
    """Transform database booking data into the API response structure.

    Args:
        booking_row: A dictionary representing the booking database row.
        passenger_rows: A list of dictionaries representing passenger database rows.

    Returns:
        dict: The formatted booking data matching the API contract.
    """
    return {
        "code": booking_row["code"],
        "status": booking_row["status"],
        "flight": format_flight(booking_row),
        "passengers": [
            {
                "firstName": p["first_name"],
                "lastName": p["last_name"],
                "dateOfBirth": p["date_of_birth"].strftime("%Y-%m-%d")
                if p["date_of_birth"]
                else "",
                "documentNumber": p["document_number"],
            }
            for p in passenger_rows
        ],
        "contact": {
            "email": booking_row[
                "contact_email"
            ],  # Добавим это в SELECT выше, если нужно, или возьмем из запроса
            "phone": booking_row["contact_phone"],
        },
        "totalPrice": {
            "amount": booking_row["total_price_amount"],
            "currency": "RUB",
        },
        "createdAt": format_datetime(booking_row["created_at"]),
    }


def create_app() -> FastAPI:
    """Create and configure the FastAPI application instance.

    Initializes API routes, configures static file serving,
    and registers the lifespan handler for database connection management.

    Returns:
        FastAPI: The configured FastAPI application instance.
    """
    app = FastAPI(lifespan=lifespan)

    # --- Global Exception Handlers ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        """Handle validation errors and return a 400 response."""
        return JSONResponse(
            status_code=400,
            content={
                "code": "validation_error",
                "message": "Неверный формат или отсутствие обязательных параметров",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        """Handle HTTP exceptions and format the error response."""
        code = "not_found" if exc.status_code == 404 else "validation_error"
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": exc.detail},
        )

    # --- Endpoints ---
    @app.api_route("/api/health", methods=["GET", "HEAD"])
    async def health_check() -> dict:
        """Check the application's health status.

        Returns:
            dict: A dictionary with an "ok" status.
        """
        return {"status": "ok"}

    @app.api_route("/api/cities", methods=["GET", "HEAD"])
    async def get_cities() -> list:
        """Retrieve the list of available cities from the database.

        Ensures that Moscow (MOW) and Saint Petersburg (LED) are always
        at the beginning of the list, as the frontend uses them for
        default search.

        Returns:
            list: A list of dictionaries containing city information.
        """
        pool = get_db_pool()
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute("""
                    SELECT code, name, country FROM cities 
                    ORDER BY 
                        CASE WHEN code = 'MOW' THEN 1 
                             WHEN code = 'LED' THEN 2 
                             ELSE 3 END, 
                        name
                """)
                rows = await cur.fetchall()
                return [{"code": r[0], "name": r[1], "country": r[2]} for r in rows]

    @app.get("/api/flights")
    async def search_flights(
        origin: str = Query(
            ..., pattern=r"^[A-Z]{3}$", description="Код города вылета"
        ),
        destination: str = Query(
            ..., pattern=r"^[A-Z]{3}$", description="Код города прилета"
        ),
        date: str = Query(
            ..., pattern=r"^\d{4}-\d{2}-\d{2}$", description="Дата вылета (YYYY-MM-DD)"
        ),
        passengers: int = Query(default=1, ge=1, description="Количество пассажиров"),
    ):
        """Search for flights based on the provided parameters."""
        pool = get_db_pool()
        rows = await get_flights(pool, origin, destination, date, passengers)
        return [format_flight(row) for row in rows]

    @app.get("/api/flights/{flight_id}")
    async def get_flight(flight_id: str):
        """Retrieve detailed information about a specific flight by its ID.

        Args:
            flight_id: The unique identifier of the flight.

        Returns:
            dict: The formatted flight data.

        Raises:
            HTTPException: 404 if the flight is not found.
        """
        pool = get_db_pool()
        row = await get_flight_by_id(pool, flight_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Рейс не найден")

        return format_flight(row)

    @app.post("/api/bookings", status_code=status.HTTP_201_CREATED)
    async def create_booking_endpoint(request: BookingRequest):
        """Create a new booking.

        Args:
            request: The booking request payload.

        Returns:
            dict: The created booking details.

        Raises:
            HTTPException: 400 if the flight ID is unknown.
        """
        pool = get_db_pool()

        # Convert Pydantic models to dictionaries for database queries
        contact_dict = request.contact.model_dump()
        passengers_list = [p.model_dump() for p in request.passengers]

        try:
            booking_row, passenger_rows = await create_booking(
                pool, request.flightId, contact_dict, passengers_list
            )
        except ValueError as e:
            if str(e) == "unknown_flight":
                raise HTTPException(
                    status_code=400, detail="Неизвестный идентификатор рейса"
                )
            raise

        return format_booking(booking_row, passenger_rows)

    @app.get("/api/bookings/{code}")
    async def get_booking(code: str, lastName: str | None = Query(default=None)):
        """Retrieve a booking by its code and passenger's last name.

        Args:
            code: The unique booking code.
            lastName: The passenger's last name for verification.

        Returns:
            dict: The formatted booking details.

        Raises:
            HTTPException: 404 if the booking is not found or verification fails.
        """
        pool = get_db_pool()
        result = await get_and_verify_booking(pool, code, lastName)

        if not result:
            raise HTTPException(status_code=404, detail="Бронь не найдена")

        booking_row, passenger_rows = result
        return format_booking(booking_row, passenger_rows)

    @app.post("/api/bookings/{code}/cancel")
    async def cancel_booking_endpoint(code: str, request: CancelBookingRequest):
        """Cancel a booking by its code and passenger's last name.

        Args:
            code: The unique booking code.
            request: The cancellation request payload containing the last name.

        Returns:
            dict: The updated booking details with 'cancelled' status.

        Raises:
            HTTPException: 404 if the booking is not found or verification fails.
        """
        pool = get_db_pool()
        result = await cancel_booking(pool, code, request.lastName)

        if not result:
            raise HTTPException(status_code=404, detail="Бронь не найдена")

        booking_row, passenger_rows = result
        return format_booking(booking_row, passenger_rows)

    PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def spa_fallback(path: str):
        """Handle requests for static files and implement SPA-fallback.

        If the requested path points to an existing file in the public directory,
        it returns that file. Otherwise, it returns index.html to support
        client-side routing. Requests to non-existent paths starting with 'api/'
        return a JSON 404 response.

        Args:
            path: The relative path from the URL request.

        Returns:
            FileResponse: The requested static file or index.html.
            JSONResponse: A 404 error in JSON format for non-existent API paths.
        """
        if path.startswith("api/"):
            return JSONResponse(
                status_code=404,
                content={"code": "not_found", "message": "Not Found"},
            )

        file_path = (PUBLIC_DIR / path).resolve()

        if path and file_path.is_relative_to(PUBLIC_DIR) and file_path.is_file():
            return FileResponse(file_path)

        index_path = PUBLIC_DIR / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)

        return JSONResponse(
            status_code=404,
            content={"code": "not_found", "message": "Not Found"},
        )

    return app
