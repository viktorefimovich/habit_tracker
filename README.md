# Habit Tracker

Бэкенд SPA-приложения «Трекер полезных привычек» по мотивам книги Джеймса Клира
«Атомные привычки». Курсовая работа по блоку Django REST Framework.

## Стек

- Python 3.12+
- Poetry (управление зависимостями и виртуальным окружением)
- Django 5 + Django REST Framework 3.15
- djangorestframework-simplejwt (JWT-авторизация)
- PostgreSQL (БД) + Redis (брокер для Celery)
- Celery + django-celery-beat (отложенные задачи и расписание)
- drf-yasg (Swagger/Redoc документация)
- django-cors-headers (CORS)
- pytest-django + coverage (тесты)

## Структура

```
habit_tracker/
├── config/              
│   ├── settings.py
│   ├── urls.py
│   ├── celery.py
│   ├── wsgi.py
│   └── asgi.py
├── users/               
├── habits/              
│   ├── models.py
│   ├── validators.py    
│   ├── serializers.py
│   ├── views.py
│   ├── permissions.py   
│   ├── paginators.py    
│   ├── services.py      
│   └── tasks.py         
├── manage.py
├── pyproject.toml      
├── .env.template
├── .flake8
├── pytest.ini
└── .coveragerc
```

## Установка (через Poetry)

```bash
gh repo clone viktorefimovich/habit_tracker
cd habit_tracker

poetry install

```

## Запуск

```bash
# 1. Применить миграции
python manage.py makemigrations
python manage.py migrate

# 2. Создать суперпользователя (опционально)
python manage.py createsuperuser

# 3. Запустить веб-сервер
python manage.py runserver

# 4. В отдельных терминалах — Celery worker и beat
celery -A config worker -l info
celery -A config beat -l info --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

## Запуск через Docker

Поднимает весь стек одной командой: PostgreSQL, Redis, Django (Gunicorn),
Celery worker, Celery beat и Nginx.

```bash
# 1. Подготовить переменные окружения
cp .env.template .env
# затем открыть .env и заполнить SECRET_KEY, TELEGRAM_BOT_TOKEN, TELEGRAM_API_URL

# 2. Собрать и запустить весь стек
docker compose up --build

# 3. Создать суперпользователя (в отдельном терминале)
docker compose exec web python manage.py createsuperuser
```

После запуска приложение доступно через Nginx:

- `http://localhost/swagger/` — Swagger UI
- `http://localhost/admin/` — админка

Полезные команды:

```bash
docker compose ps               # статус сервисов
docker compose logs -f web      # логи веб-сервиса
docker compose down             # остановить (тома с данными сохраняются)
docker compose down -v          # остановить и удалить тома (чистый старт)
```

Миграции и сбор статики выполняет разовый сервис `backend-init` при каждом старте —
вручную их запускать не нужно.

## CI/CD и деплой

Pipeline описан в `.github/workflows/ci-cd.yml` и состоит из цепочки job:

1. **lint** — проверка кода `flake8`.
2. **test** — `pytest` на временных PostgreSQL и Redis (стартует, только если линтер прошёл).
3. **docker-build** — проверка, что Docker-образы собираются.
4. **deploy** — деплой на сервер по SSH (только при пуше/мёрже в `develop`).

Деплой заходит на сервер Yandex Cloud по SSH, делает `git pull` и пересобирает стек
прод-командой:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

Доступы к серверу хранятся в GitHub Secrets: `SSH_HOST`, `SSH_USER`,
`SSH_PRIVATE_KEY`, `SSH_PORT`. На сервере рядом с проектом лежит боевой `.env`
(в репозиторий не входит).

## Документация API

После запуска доступна по адресам:

- `http://localhost/swagger/` — Swagger UI (через Docker/Nginx) или `http://localhost:8000/swagger/` (через Poetry)
- `http://localhost/redoc/` — Redoc

## Эндпоинты

| Метод | URL                     | Назначение                                | Доступ                  |
|------:|-------------------------|--------------------------------------------|-------------------------|
| POST  | `/api/users/`           | Регистрация (возвращает access + refresh)  | AllowAny                |
| POST  | `/api/users/login/`     | Авторизация по email/password (JWT)        | AllowAny                |
| POST  | `/api/users/token/refresh/` | Обновить access по refresh-токену          | AllowAny                |
| GET   | `/api/users/me/`        | Профиль текущего пользователя              | IsAuthenticated         |
| PATCH | `/api/users/me/`        | Обновить профиль (в т.ч. telegram_chat_id) | IsAuthenticated         |
| GET   | `/api/habits/`          | Список своих привычек (пагинация 5/стр.)   | IsAuthenticated         |
| POST  | `/api/habits/`          | Создать привычку                           | IsAuthenticated         |
| GET   | `/api/habits/{id}/`     | Получить свою привычку                     | IsAuthenticated+IsOwner |
| PUT/PATCH | `/api/habits/{id}/`     | Обновить свою привычку                     | IsAuthenticated+IsOwner |
| DELETE | `/api/habits/{id}/`     | Удалить свою привычку                      | IsAuthenticated+IsOwner |
| GET   | `/api/habits/public/`   | Список публичных привычек (read-only)      | IsAuthenticated         |

## Авторизация (JWT)

Используется `djangorestframework-simplejwt`. Поток:

1. Регистрируемся или логинимся — получаем `access` (живёт 1 час) и `refresh` (7 дней).
2. На защищённые эндпоинты идём с заголовком `Authorization: Bearer <access>`.
3. Когда `access` протухает (401), отправляем `refresh` на `/api/users/token/refresh/`
   и получаем новый `access`. По умолчанию refresh ротируется — на запрос приходит
   новая пара `access/refresh`, старый refresh становится недействительным.

Поскольку у пользователя `USERNAME_FIELD = "email"`, при логине в теле запроса
указываем `email` (не `username`):

```json
POST /api/users/login/
{ "email": "user@example.com", "password": "..." }
```

## Модель Habit

| Поле              | Тип                | Назначение                                                                 |
|-------------------|--------------------|---------------------------------------------------------------------------|
| user              | FK → User          | Владелец привычки                                                          |
| place             | CharField          | Место выполнения                                                           |
| time              | TimeField          | Время выполнения                                                           |
| action            | CharField          | Что делаем                                                                 |
| is_pleasant       | BooleanField       | Приятная (награда) или полезная                                            |
| related_habit     | FK → Habit (self)  | Связанная приятная привычка (для полезной)                                 |
| periodicity       | PositiveSmallInt   | Раз в сколько дней, 1…7                                                    |
| reward            | CharField          | Текст вознаграждения                                                       |
| duration          | PositiveSmallInt   | Секунды, не более 120                                                      |
| is_public         | BooleanField       | Видна в /public/                                                           |
| last_notified_at  | DateTime (auto)    | Когда последний раз отправили напоминание (для Celery)                     |

## Валидаторы (см. `habits/validators.py`)

1. Нельзя одновременно указывать `reward` и `related_habit`.
2. `duration` ≤ 120 секунд.
3. `related_habit` должна указывать на приятную привычку.
4. У приятной привычки не может быть `reward` или `related_habit`.
5. `periodicity` ≥ 1.
6. `periodicity` ≤ 7.
7. Связанная привычка должна принадлежать тому же пользователю
   (проверяется в сериализаторе).

## Telegram

1. Создайте бота через [@BotFather](https://t.me/BotFather), получите токен.
2. Сохраните токен в `.env` как `TELEGRAM_BOT_TOKEN=...`.
3. Пользователь должен один раз написать боту — после этого Telegram присвоит
   `chat_id`, который пользователь указывает в профиле через `PATCH /api/users/me/`.
4. Celery beat запускает задачу `habits.tasks.send_habit_reminders` каждую минуту;
   она сама отбирает привычки, которым пора напомнить, и отправляет сообщения.

## Тесты

```bash
# Полный прогон с покрытием
pytest

# Только определённый файл
pytest habits/tests.py -v

# Сгенерировать HTML-отчёт покрытия в htmlcov/
coverage html
```

Покрытие настраивается через `.coveragerc`

## Линтер

```bash
flake8 .
```

Конфигурация в `.flake8`: длина строки 119, миграции и виртуальное окружение исключены.

## CORS

Список разрешённых доменов фронтенда хранится в переменной `CORS_ALLOWED_ORIGINS`
файла `.env` (через запятую). По умолчанию разрешён `http://localhost:3000`.
