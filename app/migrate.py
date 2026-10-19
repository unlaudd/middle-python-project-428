"""Script for applying database migrations.

Reads DATABASE_URL from the .env file and applies all unapplied
migrations from the migrations/ directory.
"""

import os

from dotenv import load_dotenv
from yoyo import get_backend, read_migrations

load_dotenv()


def apply_migrations():
    """Apply all unapplied migrations to the database.

    Raises:
        ValueError: If DATABASE_URL is not set in the environment.
    """
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
