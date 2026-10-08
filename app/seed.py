"""Скрипт для заливки справочных данных в базу данных.

Является идемпотентным: безопасен для многократного запуска.
"""

import hashlib
import os
from datetime import datetime, timedelta, timezone

import psycopg
from dotenv import load_dotenv

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")

CITIES = [
    ("MOW", "Москва", "Россия"),
    ("LED", "Санкт-Петербург", "Россия"),
    ("AER", "Сочи", "Россия"),
    ("KZN", "Казань", "Россия"),
    ("SVX", "Екатеринбург", "Россия"),
    ("OVB", "Новосибирск", "Россия"),
    ("KGD", "Калининград", "Россия"),
]

AIRLINES = [
    ("SU", "Аэрофлот"),
    ("DP", "Победа"),
    ("S7", "S7 Airlines"),
    ("U6", "Уральские авиалинии"),
]


def deterministic_random(seed_str: str, min_val: int, max_val: int) -> int:
    """Генерирует детерминированное псевдослучайное число в диапазоне."""
    hash_val = int(hashlib.md5(seed_str.encode()).hexdigest(), 16)
    return min_val + (hash_val % (max_val - min_val + 1))


def seed_database():
    """Заливает города, авиакомпании и рейсы на 30 дней вперед."""
    if not DATABASE_URL:
        raise ValueError("DATABASE_URL не задан в окружении")

    with psycopg.connect(DATABASE_URL) as conn:
        with conn.cursor() as cur:
            # 1. Заливка городов
            for code, name, country in CITIES:
                cur.execute(
                    "INSERT INTO cities (code, name, country) "
                    "VALUES (%s, %s, %s) ON CONFLICT (code) DO NOTHING",
                    (code, name, country),
                )

            # 2. Заливка авиакомпаний
            for code, name in AIRLINES:
                cur.execute(
                    "INSERT INTO airlines (code, name) "
                    "VALUES (%s, %s) ON CONFLICT (code) DO NOTHING",
                    (code, name),
                )

            # 3. Заливка рейсов
            today = datetime.now(timezone.utc).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
            airline_codes = [a[0] for a in AIRLINES]

            for i in range(30):
                current_date = today + timedelta(days=i)
                for origin in CITIES:
                    for dest in CITIES:
                        if origin[0] == dest[0]:
                            continue  # Рейса "город сам в себя" быть не должно

                        # 2 или 3 рейса в день для каждой пары
                        num_flights = deterministic_random(
                            f"{origin[0]}_{dest[0]}_{i}_count", 2, 3
                        )

                        for j in range(num_flights):
                            flight_id = (
                                f"FL_{origin[0]}_{dest[0]}_"
                                f"{current_date.strftime('%Y%m%d')}_{j}"
                            )
                            airline = airline_codes[
                                deterministic_random(f"{flight_id}_air", 0, 3)
                            ]
                            flight_number = (
                                f"{airline}"
                                f"{deterministic_random(f'{flight_id}_num', 100, 9999)}"
                            )
                            duration = deterministic_random(f"{flight_id}_dur", 80, 280)

                            # Вылет между 06:00 и 22:00
                            hour = deterministic_random(f"{flight_id}_hour", 6, 22)
                            minute = deterministic_random(f"{flight_id}_min", 0, 3) * 15

                            departure_at = current_date.replace(
                                hour=hour, minute=minute
                            )
                            arrival_at = departure_at + timedelta(minutes=duration)

                            price = deterministic_random(
                                f"{flight_id}_price", 3000, 8500
                            )
                            seats = deterministic_random(f"{flight_id}_seats", 10, 90)

                            cur.execute(
                                "INSERT INTO flights "
                                "(id, flight_number, airline_code, origin_code, "
                                "destination_code, departure_at, arrival_at, "
                                "duration_minutes, price_amount, seats_available) "
                                "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s) "
                                "ON CONFLICT (id) DO NOTHING",
                                (
                                    flight_id,
                                    flight_number,
                                    airline,
                                    origin[0],
                                    dest[0],
                                    departure_at,
                                    arrival_at,
                                    duration,
                                    price,
                                    seats,
                                ),
                            )
        conn.commit()
    print("Справочные данные успешно залиты.")


if __name__ == "__main__":
    seed_database()
