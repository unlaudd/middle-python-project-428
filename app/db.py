"""Модуль для управления подключением к базе данных PostgreSQL.

Использует асинхронный пул соединений psycopg_pool и управляет
его жизненным циклом через механизм lifespan FastAPI.
"""

import os
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI
from psycopg_pool import AsyncConnectionPool

load_dotenv()

DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/flight_booking"
)

# Глобальная переменная для хранения пула
db_pool: AsyncConnectionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Управляет жизненным циклом пула соединений с базой данных.

    Создает и открывает пул при запуске приложения,
    закрывает его при завершении.
    """
    global db_pool
    # open=False предотвращает автоматическое открытие в конструкторе,
    # что убирает RuntimeWarning от psycopg_pool
    db_pool = AsyncConnectionPool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True},
        open=False,
    )
    # Явно открываем пул
    await db_pool.open()
    yield
    await db_pool.close()
    db_pool = None


def get_db_pool() -> AsyncConnectionPool:
    """Возвращает активный пул соединений с базой данных.

    Raises:
        RuntimeError: Если пул не инициализирован (приложение не запущено).

    Returns:
        AsyncConnectionPool: Настроенный пул соединений.
    """
    if db_pool is None:
        raise RuntimeError(
            "Database pool is not initialized. "
            "Ensure the app is running within its lifespan context."
        )
    return db_pool
