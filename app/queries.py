"""Модуль с SQL-запросами к базе данных.

Содержит функции для поиска рейсов и получения рейса по идентификатору.
"""

import random
import string
from datetime import datetime, timezone

from psycopg.errors import UniqueViolation
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool


async def get_flights(
    pool: AsyncConnectionPool,
    origin: str,
    destination: str,
    date: str,
    passengers: int,
) -> list[dict]:
    """Ищет рейсы по заданным параметрам.

    Args:
        pool: Активный пул соединений с БД.
        origin: Код города вылета.
        destination: Код города прилета.
        date: Дата вылета в формате YYYY-MM-DD.
        passengers: Требуемое количество свободных мест.

    Returns:
        list[dict]: Список найденных рейсов в виде словарей.
    """
    start_dt = f"{date}T00:00:00Z"
    end_dt = f"{date}T23:59:59Z"

    query = """
        SELECT 
            f.id, f.flight_number, f.duration_minutes, 
            f.seats_available, f.price_amount,
            f.departure_at, f.arrival_at,
            a.code AS airline_code, a.name AS airline_name,
            o.code AS origin_code, o.name AS origin_name, 
            o.country AS origin_country,
            d.code AS dest_code, d.name AS dest_name, 
            d.country AS dest_country
        FROM flights f
        JOIN airlines a ON f.airline_code = a.code
        JOIN cities o ON f.origin_code = o.code
        JOIN cities d ON f.destination_code = d.code
        WHERE f.origin_code = %s
          AND f.destination_code = %s
          AND f.seats_available >= %s
          AND f.departure_at >= %s::timestamptz
          AND f.departure_at < (%s::timestamptz + interval '1 day')
        ORDER BY f.departure_at
    """

    async with pool.connection() as conn:
        # Используем dict_row для автоматического преобразования строк в словари
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(
                query, (origin, destination, passengers, start_dt, end_dt)
            )
            return await cur.fetchall()


async def get_flight_by_id(pool: AsyncConnectionPool, flight_id: str) -> dict | None:
    """Получает полную информацию о рейсе по его идентификатору.

    Args:
        pool: Активный пул соединений с БД.
        flight_id: Идентификатор рейса.

    Returns:
        dict | None: Словарь с данными рейса или None, если рейс не найден.
    """
    query = """
        SELECT 
            f.id, f.flight_number, f.duration_minutes, 
            f.seats_available, f.price_amount,
            f.departure_at, f.arrival_at,
            a.code AS airline_code, a.name AS airline_name,
            o.code AS origin_code, o.name AS origin_name, 
            o.country AS origin_country,
            d.code AS dest_code, d.name AS dest_name, 
            d.country AS dest_country
        FROM flights f
        JOIN airlines a ON f.airline_code = a.code
        JOIN cities o ON f.origin_code = o.code
        JOIN cities d ON f.destination_code = d.code
        WHERE f.id = %s
    """

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, (flight_id,))
            return await cur.fetchone()


def generate_booking_code() -> str:
    """Генерирует уникальный 6-значный код брони.

    Исключает символы 0, O, 1, I для удобства чтения и диктовки.
    """
    alphabet = "".join(
        c for c in string.ascii_uppercase + string.digits if c not in "0O1I"
    )
    return "".join(random.choices(alphabet, k=6))


async def create_booking(
    pool: AsyncConnectionPool,
    flight_id: str,
    contact: dict,
    passengers: list[dict],
) -> tuple[dict, list[dict]]:
    """Создает бронь и записи пассажиров в одной транзакции.

    Args:
        pool: Активный пул соединений с БД.
        flight_id: Идентификатор рейса.
        contact: Словарь с контактами (email, phone).
        passengers: Список словарей с данными пассажиров.

    Returns:
        tuple[dict, list[dict]]: Кортеж из данных созданной брони
                                 и списка пассажиров.

    Raises:
        ValueError: Если рейс с таким ID не найден.
        RuntimeError: Если не удалось сгенерировать уникальный код
                      после нескольких попыток.
    """
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # 1. Проверяем существование рейса и получаем его цену
            await cur.execute(
                "SELECT id, price_amount FROM flights WHERE id = %s",
                (flight_id,),
            )
            flight = await cur.fetchone()
            if not flight:
                raise ValueError("unknown_flight")

            total_price = flight["price_amount"] * len(passengers)
            created_at = datetime.now(timezone.utc)

            # 2. Пытаемся создать бронь с уникальным кодом
            # (защита от коллизий)
            max_retries = 5
            for _ in range(max_retries):
                code = generate_booking_code()
                try:
                    # Начинаем транзакцию
                    async with conn.transaction():
                        # Вставка брони
                        await cur.execute(
                            """
                            INSERT INTO bookings 
                            (code, status, flight_id, contact_email, 
                             contact_phone, total_price_amount, created_at)
                            VALUES (%s, 'confirmed', %s, %s, %s, %s, %s)
                            """,
                            (
                                code,
                                flight_id,
                                contact["email"],
                                contact["phone"],
                                total_price,
                                created_at,
                            ),
                        )

                        # Вставка пассажиров (цикл надежнее executemany
                        # в некоторых версиях async psycopg)
                        for p in passengers:
                            await cur.execute(
                                """
                                INSERT INTO passengers 
                                (booking_code, first_name, last_name, 
                                 date_of_birth, document_number)
                                VALUES (%s, %s, %s, %s, %s)
                                """,
                                (
                                    code,
                                    p["firstName"],
                                    p["lastName"],
                                    p["dateOfBirth"],
                                    p["documentNumber"],
                                ),
                            )

                        # Получаем собранную информацию о брони для ответа
                        await cur.execute(
                            """
                            SELECT 
                                b.code, b.status, b.total_price_amount, 
                                b.created_at, b.contact_email, b.contact_phone,
                                f.id AS id, f.flight_number, 
                                f.duration_minutes, f.seats_available, 
                                f.price_amount, f.departure_at, f.arrival_at,
                                a.code AS airline_code, a.name AS airline_name,
                                o.code AS origin_code, o.name AS origin_name, 
                                o.country AS origin_country,
                                d.code AS dest_code, d.name AS dest_name, 
                                d.country AS dest_country
                            FROM bookings b
                            JOIN flights f ON b.flight_id = f.id
                            JOIN airlines a ON f.airline_code = a.code
                            JOIN cities o ON f.origin_code = o.code
                            JOIN cities d ON f.destination_code = d.code
                            WHERE b.code = %s
                            """,
                            (code,),
                        )
                        booking_row = await cur.fetchone()

                        # Получаем пассажиров этой брони
                        await cur.execute(
                            """
                            SELECT first_name, last_name, date_of_birth, 
                                   document_number 
                            FROM passengers 
                            WHERE booking_code = %s
                            """,
                            (code,),
                        )
                        passenger_rows = await cur.fetchall()

                        return booking_row, passenger_rows

                except UniqueViolation:
                    # Код уже занят, откат транзакции происходит автоматически,
                    # цикл продолжается с новым кодом
                    continue

            raise RuntimeError("Не удалось сгенерировать уникальный код брони")
