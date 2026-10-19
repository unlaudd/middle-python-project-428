# Flight Booking Backend API / Бекенд для бронирования авиабилетов

[![Hexlet Check](https://github.com/unlaudd/middle-python-project-428/actions/workflows/hexlet-check.yml/badge.svg)](https://github.com/unlaudd/middle-python-project-428/actions)
[![Tests](https://github.com/unlaudd/middle-python-project-428/actions/workflows/test.yml/badge.svg)](https://github.com/unlaudd/middle-python-project-428/actions/workflows/test.yml)
[![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688.svg)](https://fastapi.tiangolo.com/)

🌐 **Live Demo / Живая демонстрация:** [https://middle-python-project-428.onrender.com](https://middle-python-project-428.onrender.com)

---

## 🇬🇧 English Version

A robust, production-ready backend API for a flight booking service. It handles city directories, flight searches, booking creation with server-side price calculation, and booking management (viewing and cancellation). The frontend is provided by Hexlet and consumes this API strictly according to the defined contract.

### 🚀 API Endpoints

| Method | Endpoint | Description | Request / Response |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Application health check. | `{"status": "ok"}` |
| `GET` | `/api/cities` | List of available cities (MOW and LED are always first). | `[{"code": "MOW", "name": "Москва", ...}]` |
| `GET` | `/api/flights` | Search for flights. | **Query:** `?origin=MOW&destination=LED&date=2024-10-25&passengers=1`<br>**Response:** `200 OK` with array of flights. |
| `GET` | `/api/flights/{id}` | Get detailed info about a specific flight. | **Response:** `200 OK` with flight object, or `404 Not Found`. |
| `POST` | `/api/bookings` | Create a new booking. Server calculates `totalPrice`. | **Body:** `{"flightId": "...", "contact": {...}, "passengers": [...]}`<br>**Response:** `201 Created` with booking details. |
| `GET` | `/api/bookings/{code}` | View booking. Requires `lastName` query param for security. | **Query:** `?lastName=Иванов`<br>**Response:** `200 OK` or `404` (identical response to prevent enumeration). |
| `POST` | `/api/bookings/{code}/cancel` | Cancel an existing booking. | **Body:** `{"lastName": "Иванов"}`<br>**Response:** `200 OK` with `status: "cancelled"`, or `404`. |


### 🛠 Tech Stack

- **Language:** Python 3.12+
- **Framework:** FastAPI + Uvicorn (ASGI)
- **Database:** PostgreSQL (async connections via `psycopg` pool)
- **Migrations:** `yoyo-migrations`
- **Dependency Management:** `uv` (Python), `npm` (Node.js for frontend)
- **Code Quality:** Ruff (linting, formatting, strict Google-style docstrings)
- **Automation:** GNU Make
- **Deployment:** Docker, Render

### 💻 Getting Started

1. **Clone & Configure:**

   ```bash
   git clone https://github.com/unlaudd/middle-python-project-428.git
   cd middle-python-project-428
   # Create .env file with DATABASE_URL and PORT
   ```

2. **Install & Build:**

   ```bash
   make install
   make build
   ```

3. **Run:** (Applies migrations, seeds data, and starts server)

   ```bash
   make start
   ```

### 🐳 Running with Docker

```bash
docker build -t flight-booking .
docker run --rm -e PORT=8080 -e DATABASE_URL="postgresql://user:pass@host:5432/db" -p 8080:8080 flight-booking
```

### 🧪 Testing

```bash
make test
uv run ruff check .
uv run ruff format .
```

---

## 🇷🇺 Для удобства русскоязычных разработчиков и проверяющих, ниже приведена полная версия на русском языке.

## 🇷🇺 Русская версия

Надежный, готовый к продакшену бекенд API для сервиса бронирования авиабилетов. Реализует справочник городов, поиск рейсов, создание брони с расчетом стоимости на стороне сервера, а также просмотр и отмену брони. Фронтенд предоставлен Хекслетом и взаимодействует с этим API строго по заданному контракту.

### 🚀 API Эндпоинты

| Метод | Эндпоинт | Описание | Запрос / Ответ |
| :--- | :--- | :--- | :--- |
| `GET` | `/api/health` | Проверка работоспособности приложения. | `{"status": "ok"}` |
| `GET` | `/api/cities` | Список доступных городов (MOW и LED всегда первые). | `[{"code": "MOW", "name": "Москва", ...}]` |
| `GET` | `/api/flights` | Поиск рейсов. | **Query:** `?origin=MOW&destination=LED&date=2024-10-25&passengers=1`<br>**Ответ:** `200 OK` с массивом рейсов. |
| `GET` | `/api/flights/{id}` | Подробная информация о конкретном рейсе. | **Ответ:** `200 OK` с объектом рейса или `404 Not Found`. |
| `POST` | `/api/bookings` | Создание новой брони. Сервер сам считает `totalPrice`. | **Тело:** `{"flightId": "...", "contact": {...}, "passengers": [...]}`<br>**Ответ:** `201 Created` с деталями брони. |
| `GET` | `/api/bookings/{code}` | Просмотр брони. Требует параметр `lastName` для безопасности. | **Query:** `?lastName=Иванов`<br>**Ответ:** `200 OK` или `404` (одинаковый ответ для защиты от перебора). |
| `POST` | `/api/bookings/{code}/cancel` | Отмена существующей брони. | **Тело:** `{"lastName": "Иванов"}`<br>**Ответ:** `200 OK` со `status: "cancelled"` или `404`. |


### 🛠 Стек технологий

- **Язык:** Python 3.12+
- **Фреймворк:** FastAPI + Uvicorn (ASGI)
- **База данных:** PostgreSQL (асинхронные подключения через пул `psycopg`)
- **Миграции:** `yoyo-migrations`
- **Управление зависимостями:** `uv` (Python), `npm` (Node.js для фронтенда)
- **Качество кода:** Ruff (линтинг, форматирование, строгие докстроки в стиле Google)
- **Автоматизация:** GNU Make
- **Деплой:** Docker, Render

### 💻 Быстрый старт

1. **Клонирование и настройка:**

   ```bash
   git clone https://github.com/unlaudd/middle-python-project-428.git
   cd middle-python-project-428
   # Создайте файл .env с переменными DATABASE_URL и PORT
   ```

2. **Установка и сборка:**

   ```bash
   make install
   make build
   ```

3. **Запуск:** (Автоматически применяет миграции, заполняет БД и запускает сервер)

   ```bash
   make start
   ```

### 🐳 Запуск через Docker

```bash
docker build -t flight-booking .
docker run --rm -e PORT=8080 -e DATABASE_URL="postgresql://user:pass@host:5432/db" -p 8080:8080 flight-booking
```

### 🧪 Тестирование и качество

```bash
make test
uv run ruff check .
uv run ruff format .
```

<details>
<summary>ℹ️ Автоматические проверки Хекслета</summary>

Тесты запускаются на каждый коммит. За запуск отвечает файл `.github/workflows/hexlet-check.yml`. Пожалуйста, не удаляйте и не переименовывайте этот файл или репозиторий, так как это необходимо для работы системы автоматической проверки Хекслета.

</details>

---

## О Хекслете

Хекслет — школа программирования: авторские программы обучения с практикой, поддержкой наставников и реальными проектами, которые остаются в резюме. Этот репозиторий — один из таких проектов.
