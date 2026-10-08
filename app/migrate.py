"""Скрипт для применения миграций базы данных.

Читает DATABASE_URL из .env файла и применяет все неприменённые
миграции из директории migrations/.
"""

import os

from dotenv import load_dotenv
from yoyo import get_backend, read_migrations

load_dotenv()


def apply_migrations():
    """Применяет все неприменённые миграции к базе данных."""
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL не задан в окружении")

    backend = get_backend(database_url)
    migrations = read_migrations("migrations")

    with backend.lock():
        to_apply = backend.to_apply(migrations)
        if to_apply:
            backend.apply_migrations(to_apply)
            print(f"Применено миграций: {len(to_apply)}")
        else:
            print("Все миграции уже применены.")


if __name__ == "__main__":
    apply_migrations()
