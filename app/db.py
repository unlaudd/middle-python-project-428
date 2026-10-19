"""Module for managing PostgreSQL database connections.

Uses an asynchronous connection pool via psycopg_pool and manages
its lifecycle through the FastAPI lifespan mechanism.
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

# Global variable to store the connection pool
db_pool: AsyncConnectionPool | None = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Manage the lifecycle of the database connection pool.

    Creates and opens the connection pool on application startup,
    and closes it on shutdown.

    Args:
        app: The FastAPI application instance.

    Yields:
        None
    """
    global db_pool
    # open=False prevents automatic opening in the constructor,
    # eliminating psycopg_pool RuntimeWarning
    db_pool = AsyncConnectionPool(
        DATABASE_URL,
        min_size=1,
        max_size=10,
        kwargs={"autocommit": True},
        open=False,
    )
    # Explicitly open the pool
    await db_pool.open()
    yield
    await db_pool.close()
    db_pool = None


def get_db_pool() -> AsyncConnectionPool:
    """Retrieve the active database connection pool.

    Returns:
        AsyncConnectionPool: The configured connection pool instance.

    Raises:
        RuntimeError: If the pool is not initialized (app not running in lifespan).
    """
    if db_pool is None:
        raise RuntimeError(
            "Database pool is not initialized. "
            "Ensure the app is running within its lifespan context."
        )
    return db_pool
