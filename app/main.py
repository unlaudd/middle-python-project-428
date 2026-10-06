"""Основной модуль приложения для бронирования авиабилетов.

Содержит фабрику приложения create_app, маршруты API и логику
раздачи статических файлов с поддержкой SPA-fallback для корректной
работы клиентского роутинга (Vue/React и т.д.).
"""

from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse


def create_app() -> FastAPI:
    """Создает и настраивает экземпляр приложения FastAPI.

    Инициализирует маршруты для API и настраивает раздачу статических файлов
    с поддержкой SPA-fallback.

    Returns:
        FastAPI: Настроенный экземпляр приложения FastAPI.

    Example:
        >>> app = create_app()
        >>> isinstance(app, FastAPI)
        True
    """
    app = FastAPI()

    @app.api_route("/api/cities", methods=["GET", "HEAD"])
    async def get_cities() -> list:
        """Возвращает список доступных городов для бронирования.

        На текущем этапе реализации возвращает пустой список.
        Данные будут наполнены на следующих шагах проекта.

        Returns:
            list: Список словарей с информацией о городах.
        """
        return []

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
            return JSONResponse(status_code=404, content={"detail": "Not Found"})

        file_path = (PUBLIC_DIR / path).resolve()

        if path and file_path.is_relative_to(PUBLIC_DIR) and file_path.is_file():
            return FileResponse(file_path)

        index_path = PUBLIC_DIR / "index.html"
        if index_path.is_file():
            return FileResponse(index_path)

        return JSONResponse(status_code=404, content={"detail": "Not Found"})

    return app
