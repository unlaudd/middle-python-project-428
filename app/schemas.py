"""Validation schemas for incoming request data (Pydantic)."""

from datetime import date as date_type

from pydantic import BaseModel, Field, field_validator


class ContactRequest(BaseModel):
    """Request schema for contact information."""

    email: str = Field(..., min_length=1, description="Email заказчика")
    phone: str = Field(..., min_length=1, description="Телефон заказчика")


class PassengerRequest(BaseModel):
    """Request schema for passenger data."""

    firstName: str = Field(..., min_length=1, description="Имя пассажира")
    lastName: str = Field(..., min_length=1, description="Фамилия пассажира")
    dateOfBirth: date_type = Field(..., description="Дата рождения (YYYY-MM-DD)")
    documentNumber: str = Field(..., min_length=1, description="Номер документа")


class BookingRequest(BaseModel):
    """Request schema for booking creation."""

    flightId: str = Field(..., min_length=1, description="Идентификатор рейса")
    contact: ContactRequest
    passengers: list[PassengerRequest] = Field(
        ..., min_length=1, description="Список пассажиров (минимум 1)"
    )


class CancelBookingRequest(BaseModel):
    """Request schema for booking cancellation."""

    lastName: str | None = Field(
        default=None, description="Фамилия пассажира для подтверждения"
    )

    @field_validator("lastName")
    @classmethod
    def validate_last_name(cls, v: str | None) -> str | None:
        """Validate that lastName is not empty if provided."""
        if v is not None and v.strip() == "":
            return None
        return v
