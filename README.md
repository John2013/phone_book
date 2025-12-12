# Phone Address Service

Микросервис для хранения и управления связками "телефон-адрес" с использованием FastAPI и Redis.

## Описание

Сервис предоставляет RESTful API для операций CRUD с данными телефон-адрес, используя Redis как быстрое хранилище данных.

## Требования

- Python 3.14+
- uv (для управления зависимостями)
- Redis (для хранения данных)

## Установка

1. Клонируйте репозиторий:
```bash
git clone https://github.com/John2013/phone_book
cd phone-address-service
```

2. Установите зависимости с помощью uv:
```bash
uv sync
```

3. Скопируйте файл конфигурации:
```bash
cp .env.example .env
```

4. Настройте переменные окружения в файле `.env` при необходимости.

## Запуск

### Локальный запуск

1. Запустите Redis:
```bash
redis-server
```

2. Запустите приложение:
```bash
make run
# или
uv run python main.py
```

### Запуск с Docker Compose

```bash
make docker-up
# или
docker-compose up -d
```

## Docker

### Сборка образа

```bash
make docker-build
# или
docker build -t phone-address-service .
```

### Среды развертывания

#### Разработка
```bash
make docker-dev
# или
docker-compose --profile dev up --build
```

#### Продакшн
```bash
make docker-prod
# или
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

### Конфигурация окружений

- `.env.development` - настройки для разработки
- `.env.production` - настройки для продакшна
- `docker-compose.prod.yml` - продакшн конфигурация с ограничениями ресурсов

### Полезные команды

```bash
# Просмотр логов
make docker-logs

# Интеграционные тесты
make docker-test

# Очистка Docker ресурсов
make docker-clean
```

## Разработка

### Установка зависимостей для разработки

```bash
make install-dev
# или
uv sync --extra dev
```

### Запуск тестов

```bash
make test
# или
uv run pytest
```

### Запуск тестов с покрытием

```bash
make test-cov
# или
uv run pytest --cov=phone_address_service --cov-report=html --cov-report=term
```

## API Endpoints

После запуска сервиса API будет доступно по адресу `http://localhost:8000`

- `GET /health` - проверка состояния сервиса
- `GET /docs` - интерактивная документация Swagger UI
- `GET /redoc` - альтернативная документация ReDoc

## Конфигурация

Сервис настраивается через переменные окружения. Основные параметры:

- `REDIS_HOST` - хост Redis (по умолчанию: localhost)
- `REDIS_PORT` - порт Redis (по умолчанию: 6379)
- `API_PORT` - порт API (по умолчанию: 8000)
- `LOG_LEVEL` - уровень логирования (по умолчанию: INFO)

Полный список параметров см. в файле `.env.example`.

## Структура проекта

```
phone_address_service/
├── api/           # API слой (FastAPI endpoints)
├── config/        # Конфигурация приложения
├── models/        # Модели данных (Pydantic)
├── repositories/  # Слой доступа к данным
└── services/      # Бизнес-логика
tests/             # Тесты
```