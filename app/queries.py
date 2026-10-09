"""Модуль с SQL-запросами к базе данных.

Содержит функции для поиска рейсов и получения рейса по идентификатору.
"""
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


async def get_flight_by_id(
    pool: AsyncConnectionPool, 
    flight_id: str
) -> dict | None:
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
