"""Module containing SQL queries for database operations.

Includes functions for flight search, flight retrieval by ID,
booking creation, and booking management.
"""

import secrets
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
    """Search for flights based on the provided parameters.

    Args:
        pool: Active database connection pool.
        origin: Departure city code.
        destination: Arrival city code.
        date: Departure date in YYYY-MM-DD format.
        passengers: Required number of available seats.

    Returns:
        list[dict]: List of found flights as dictionaries.
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
        WHERE f.origin_code = %s
          AND f.destination_code = %s
          AND f.seats_available >= %s
          AND (f.departure_at AT TIME ZONE 'UTC')::date = %s
        ORDER BY f.departure_at
    """

    async with pool.connection() as conn:
        # Use dict_row for automatic conversion of rows to dictionaries
        async with conn.cursor(row_factory=dict_row) as cur:
            await cur.execute(query, (origin, destination, passengers, date))
            return await cur.fetchall()


async def get_flight_by_id(pool: AsyncConnectionPool, flight_id: str) -> dict | None:
    """Retrieve complete flight information by its identifier.

    Args:
        pool: Active database connection pool.
        flight_id: The flight identifier.

    Returns:
        dict | None: Dictionary with flight data or None if not found.
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
    """Generate a secure unique 6-character booking code.

    Excludes characters 0, O, 1, I for easier reading and dictation.
    Uses secrets module for cryptographically secure random generation.

    Returns:
        str: A 6-character alphanumeric booking code.
    """
    alphabet = "".join(
        c for c in string.ascii_uppercase + string.digits if c not in "0O1I"
    )
    return "".join(secrets.choice(alphabet) for _ in range(6))


async def create_booking(
    pool: AsyncConnectionPool,
    flight_id: str,
    contact: dict,
    passengers: list[dict],
) -> tuple[dict, list[dict]]:
    """Create a booking and passenger records in a single transaction.

    Args:
        pool: Active database connection pool.
        flight_id: The flight identifier.
        contact: Dictionary with contact information (email, phone).
        passengers: List of dictionaries with passenger data.

    Returns:
        tuple[dict, list[dict]]: Tuple of created booking data
                                 and passenger list.

    Raises:
        ValueError: If the flight with the given ID is not found.
        RuntimeError: If unable to generate a unique code
                      after multiple attempts.
    """
    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # 1. Check flight existence and retrieve its price
            await cur.execute(
                "SELECT id, price_amount FROM flights WHERE id = %s",
                (flight_id,),
            )
            flight = await cur.fetchone()
            if not flight:
                raise ValueError("unknown_flight")

            total_price = flight["price_amount"] * len(passengers)
            created_at = datetime.now(timezone.utc)

            # 2. Attempt to create booking with unique code
            # (collision protection)
            max_retries = 5
            for _ in range(max_retries):
                code = generate_booking_code()
                try:
                    # Begin transaction
                    async with conn.transaction():
                        # Insert booking
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

                        # Insert passengers (loop is more reliable than
                        # executemany in some async psycopg versions)
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

                        # Retrieve assembled booking information for response
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

                        # Retrieve passengers for this booking
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
                    # Code already taken, transaction rollback is automatic,
                    # loop continues with new code
                    continue

            raise RuntimeError("Не удалось сгенерировать уникальный код брони")


async def get_and_verify_booking(
    pool: AsyncConnectionPool, code: str, last_name: str | None
) -> tuple[dict, list[dict]] | None:
    """Search for a booking by code and verify passenger's last name.

    Args:
        pool: Active database connection pool.
        code: The booking code.
        last_name: Last name for verification.

    Returns:
        tuple[dict, list[dict]] | None: Booking and passenger data, or None.
    """
    if not last_name:
        return None

    code = code.strip().upper()
    last_name_clean = last_name.strip().lower()

    async with pool.connection() as conn:
        async with conn.cursor(row_factory=dict_row) as cur:
            # Step 1: Check booking existence and last name match
            await cur.execute(
                """
                SELECT 1 FROM bookings b
                JOIN passengers p ON b.code = p.booking_code
                WHERE b.code = %s AND LOWER(TRIM(p.last_name)) = %s
                """,
                (code, last_name_clean),
            )
            if not await cur.fetchone():
                return None

            # Step 2: Retrieve complete booking data
            await cur.execute(
                """
                SELECT 
                    b.code, b.status, b.total_price_amount, b.created_at, 
                    b.contact_email, b.contact_phone,
                    f.id AS id, f.flight_number, f.duration_minutes, 
                    f.seats_available, f.price_amount, f.departure_at, f.arrival_at,
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
            if not booking_row:
                return None

            # Step 3: Retrieve all passengers for this booking
            await cur.execute(
                """
                SELECT first_name, last_name, date_of_birth, document_number 
                FROM passengers 
                WHERE booking_code = %s
                """,
                (code,),
            )
            passenger_rows = await cur.fetchall()
            return booking_row, passenger_rows


async def cancel_booking(
    pool: AsyncConnectionPool, code: str, last_name: str | None
) -> tuple[dict, list[dict]] | None:
    """Cancel a booking if code and last name match.

    Args:
        pool: Active database connection pool.
        code: The booking code.
        last_name: Last name for verification.

    Returns:
        tuple[dict, list[dict]] | None: Updated booking and passenger data,
                                        or None if verification failed.
    """
    # First verify that booking exists and last name is correct
    result = await get_and_verify_booking(pool, code, last_name)
    if not result:
        return None

    booking_row, passenger_rows = result
    code = code.strip().upper()

    # Update status to cancelled
    async with pool.connection() as conn:
        async with conn.cursor() as cur:
            await cur.execute(
                "UPDATE bookings SET status = 'cancelled' WHERE code = %s",
                (code,),
            )

    # Return updated data (change status in dictionary for response)
    booking_row["status"] = "cancelled"
    return booking_row, passenger_rows
