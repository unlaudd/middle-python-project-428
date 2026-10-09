"""Схемы валидации входящих данных (Pydantic)."""

from pydantic import BaseModel, Field


class ContactRequest(BaseModel):
    """Схема запроса контактных данных."""

    email: str = Field(..., min_length=1, description="Email заказчика")
    phone: str = Field(..., min_length=1, description="Телефон заказчика")


class PassengerRequest(BaseModel):
    """Схема запроса данных пассажира."""

    firstName: str = Field(..., min_length=1, description="Имя пассажира")
    lastName: str = Field(..., min_length=1, description="Фамилия пассажира")
    dateOfBirth: str = Field(
        ..., min_length=1, description="Дата рождения (YYYY-MM-DD)"
    )
    documentNumber: str = Field(..., min_length=1, description="Номер документа")


class BookingRequest(BaseModel):
    """Схема запроса на создание бронирования."""

    flightId: str = Field(..., min_length=1, description="Идентификатор рейса")
    contact: ContactRequest
    passengers: list[PassengerRequest] = Field(
        ..., min_length=1, description="Список пассажиров (минимум 1)"
    )


class CancelBookingRequest(BaseModel):
    """Схема запроса на отмену бронирования."""

    lastName: str | None = Field(
        default=None, description="Фамилия пассажира для подтверждения"
    )
