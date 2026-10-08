"""Основной модуль приложения для бронирования авиабилетов.

Содержит фабрику приложения create_app, маршруты API и логику
раздачи статических файлов с поддержкой SPA-fallback для корректной
работы клиентского роутинга (Vue/React и т.д.).
"""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

from app.db import get_db_pool, lifespan


def create_app() -> FastAPI:
    """Создает и настраивает экземпляр приложения FastAPI.

    Инициализирует маршруты для API, настраивает раздачу статических файлов
    и регистрирует обработчик lifespan для управления базой данных.

    Returns:
        FastAPI: Настроенный экземпляр приложения FastAPI.

    Example:
        >>> app = create_app()
        >>> isinstance(app, FastAPI)
        True
    """
    # Передаем lifespan для корректного управления ресурсами (включая тесты)
    app = FastAPI(lifespan=lifespan)

    @app.api_route("/api/health", methods=["GET", "HEAD"])
    async def health_check() -> dict:
        """Проверка работоспособности приложения (Health Check).

        Не обращается к базе данных, проверяет только, что сервер
        поднят и способен обрабатывать запросы.

        Returns:
            dict: Словарь со статусом "ok".
        """
        return {"status": "ok"}

    @app.api_route("/api/cities", methods=["GET", "HEAD"])
    async def get_cities() -> list:
        """Возвращает список доступных городов для бронирования из базы данных.

        Гарантирует, что Москва (MOW) и Санкт-Петербург (LED) всегда 
        находятся в начале списка, так как фронтенд использует их 
        для поиска по умолчанию.

        Returns:
            list[dict]: Список словарей с информацией о городах (code, name, country).
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

    PUBLIC_DIR = Path(__file__).resolve().parent.parent / "public"

    @app.api_route("/{path:path}", methods=["GET", "HEAD"])
    async def spa_fallback(path: str):
        """Обрабатывает запросы к статическим файлам и реализует SPA-fallback.

        Если запрошенный путь указывает на существующий файл в директории public,
        возвращает этот файл. В противном случае возвращает index.html для
        поддержки клиентского роутинга. Запросы к несуществующим путям,
        начинающимся с 'api/', возвращают JSON 404.

        Args:
            path (str): Относительный путь из URL-запроса.

        Returns:
            FileResponse: Запрошенный статический файл или index.html.
            JSONResponse: Ошибка 404 в формате JSON для несуществующих API путей.
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
