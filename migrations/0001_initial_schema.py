"""Начальная миграция: создание всех таблиц и индексов.

Используем IF NOT EXISTS для безопасности при повторном применении.
"""

from yoyo import step

__depends__ = {}

steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS cities (
            code VARCHAR(3) PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            country VARCHAR(100)
        );

        CREATE TABLE IF NOT EXISTS airlines (
            code VARCHAR(10) PRIMARY KEY,
            name VARCHAR(100) NOT NULL
        );

        CREATE TABLE IF NOT EXISTS flights (
            id VARCHAR(50) PRIMARY KEY,
            flight_number VARCHAR(20) NOT NULL,
            airline_code VARCHAR(10) REFERENCES airlines(code),
            origin_code VARCHAR(3) REFERENCES cities(code),
            destination_code VARCHAR(3) REFERENCES cities(code),
            departure_at TIMESTAMPTZ NOT NULL,
            arrival_at TIMESTAMPTZ NOT NULL,
            duration_minutes INT NOT NULL,
            price_amount INT NOT NULL,
            seats_available INT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS bookings (
            code VARCHAR(6) PRIMARY KEY,
            status VARCHAR(20) NOT NULL,
            flight_id VARCHAR(50) REFERENCES flights(id),
            contact_email VARCHAR(255) NOT NULL,
            contact_phone VARCHAR(50) NOT NULL,
            total_price_amount INT NOT NULL,
            created_at TIMESTAMPTZ NOT NULL
        );

        CREATE TABLE IF NOT EXISTS passengers (
            id SERIAL PRIMARY KEY,
            booking_code VARCHAR(6) REFERENCES bookings(code) ON DELETE CASCADE,
            first_name VARCHAR(100) NOT NULL,
            last_name VARCHAR(100) NOT NULL,
            date_of_birth DATE NOT NULL,
            document_number VARCHAR(100) NOT NULL
        );

        CREATE INDEX IF NOT EXISTS idx_flights_search 
        ON flights(origin_code, destination_code, departure_at, seats_available);
        """,
        """
        DROP TABLE IF EXISTS passengers;
        DROP TABLE IF EXISTS bookings;
        DROP TABLE IF EXISTS flights;
        DROP TABLE IF EXISTS airlines;
        DROP TABLE IF EXISTS cities;
        """,
    )
]
