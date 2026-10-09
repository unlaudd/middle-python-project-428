"""Основной модуль приложения для бронирования авиабилетов.

Содержит фабрику приложения create_app, маршруты API и логику
раздачи статических файлов с поддержкой SPA-fallback.
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse

from app.db import get_db_pool, lifespan
from app.queries import get_flight_by_id, get_flights


def format_datetime(dt) -> str:
    """Форматирует datetime в ISO 8601 с суффиксом 'Z' (UTC)."""
    if dt is None:
        return ""
    # Приводим к UTC и форматируем с Z на конце, как требует контракт
    return dt.strftime("%Y-%m-%dT%H:%M:%SZ")


def format_flight(row: dict) -> dict:
    """Преобразует плоскую строку из БД в структуру ответа API."""
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


def create_app() -> FastAPI:
    """Создает и настраивает экземпляр приложения FastAPI."""
    app = FastAPI(lifespan=lifespan)

    # --- Глобальные обработчики ошибок ---
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        return JSONResponse(
            status_code=400,
            content={
                "code": "validation_error",
                "message": "Неверный формат или отсутствие обязательных параметров",
            },
        )

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        code = "not_found" if exc.status_code == 404 else "error"
        return JSONResponse(
            status_code=exc.status_code,
            content={"code": code, "message": exc.detail},
        )

    # --- Эндпоинты ---
    @app.api_route("/api/health", methods=["GET", "HEAD"])
    async def health_check() -> dict:
        """Проверка работоспособности приложения."""
        return {"status": "ok"}

    @app.api_route("/api/cities", methods=["GET", "HEAD"])
    async def get_cities() -> list:
        """Возвращает список доступных городов из базы данных."""
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
        """Ищет рейсы по заданным параметрам."""
        pool = get_db_pool()
        rows = await get_flights(pool, origin, destination, date, passengers)
        return [format_flight(row) for row in rows]

    @app.get("/api/flights/{flight_id}")
    async def get_flight(flight_id: str):
        """Получает информацию о конкретном рейсе по идентификатору."""
        pool = get_db_pool()
        row = await get_flight_by_id(pool, flight_id)

        if row is None:
            raise HTTPException(status_code=404, detail="Рейс не найден")

        return format_flight(row)

    PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def spa_fallback(path: str):
        """Обрабатывает запросы к статическим файлам и реализует SPA-fallback."""
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
