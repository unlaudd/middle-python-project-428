import "@typespec/http";
import "@typespec/openapi3";

using TypeSpec.Http;

@service(#{ title: "Flight Booking API" })
@server("http://localhost:8080", "Local development server")
namespace FlightBookingApi;

// --- Модели ---

model City {
  code: string;
  name: string;
  country?: string;
}

model Money {
  amount: int32; // Целые рубли
  currency: string; // Всегда "RUB"
}

model Airline {
  code: string;
  name: string;
}

model Flight {
  id: string;
  flightNumber: string;
  airline: Airline;
  origin: City;
  destination: City;
  departureAt: utcDateTime; // ISO 8601 с Z на конце
  arrivalAt: utcDateTime;
  durationMinutes: int32;
  price: Money;
  seatsAvailable: int32;
}

model Passenger {
  firstName: string;
  lastName: string;
  dateOfBirth: plainDate; // Только дата, YYYY-MM-DD
  documentNumber: string;
}

model Contact {
  email: string;
  phone: string;
}

model Booking {
  code: string; // 6 символов A-Z и 0-9
  status: "confirmed" | "cancelled";
  flight: Flight;
  passengers: Passenger[];
  contact: Contact;
  totalPrice: Money;
  createdAt: utcDateTime;
}

// Универсальная модель ошибки для 400 и 404
model ApiError {
  code: string; // "validation_error" или "not_found"
  message: string;
}

// --- Эндпоинты ---

// 1. Health check
@route("/api/health")
@get
op healthCheck(): {
  @statusCode statusCode: 200;
  @body body: { status: "ok" };
};

// 2. Справочник городов
@route("/api/cities")
@get
op getCities(): {
  @statusCode statusCode: 200;
  @body body: City[];
};

// 3. Поиск рейсов
@route("/api/flights")
@get
op searchFlights(
  @query origin: string,
  @query destination: string,
  @query date: plainDate,
  @query passengers?: int32 // Необязательный, по умолчанию 1 (обрабатывается на бэке)
): 
  | { @statusCode statusCode: 200; @body body: Flight[] }
  | { @statusCode statusCode: 400; @body body: ApiError };

// 4. Рейс по идентификатору
@route("/api/flights/{id}")
@get
op getFlightById(
  @path id: string
): 
  | { @statusCode statusCode: 200; @body body: Flight }
  | { @statusCode statusCode: 404; @body body: ApiError };

// 5. Создание брони
model CreateBookingRequest {
  flightId: string;
  contact: Contact;
  passengers: Passenger[];
}

@route("/api/bookings")
@post
op createBooking(
  @body body: CreateBookingRequest
): 
  | { @statusCode statusCode: 201; @body body: Booking }
  | { @statusCode statusCode: 400; @body body: ApiError };

// 6. Просмотр брони
@route("/api/bookings/{code}")
@get
op getBooking(
  @path code: string,
  @query lastName: string
): 
  | { @statusCode statusCode: 200; @body body: Booking }
  | { @statusCode statusCode: 404; @body body: ApiError };

// 7. Отмена брони
model CancelBookingRequest {
  lastName: string;
}

@route("/api/bookings/{code}/cancel")
@post
op cancelBooking(
  @path code: string,
  @body body: CancelBookingRequest
): 
  | { @statusCode statusCode: 200; @body body: Booking }
  | { @statusCode statusCode: 404; @body body: ApiError };