# Flask Weather Archive

[English](README.md) | **Русский**

Самостоятельно разворачиваемый архив истории погоды по городам. Приложение периодически запрашивает текущие условия у [Open-Meteo](https://open-meteo.com/), сохраняет их в PostgreSQL и позволяет просматривать таблицы и графики через веб-интерфейс на Flask-Admin.

## Как это работает

1. Вы добавляете **города** — по названию и стране или по широте/долготе.
2. **Фоновый планировщик** (или ручные действия) запрашивает погоду с настраиваемым интервалом.
3. Каждый запрос добавляет **запись о погоде** (температура, влажность, ветер, давление и др.).
4. **Панель администратора** показывает историю по городам, графики, карту последних показаний и диагностические логи.

Публичной регистрации нет: пользователей создают только через CLI или инструменты админки.

## Возможности

| Раздел | Описание |
|--------|----------|
| **Аутентификация** | Страница входа; самостоятельная регистрация отсутствует |
| **Города** | Добавление по названию + стране (геокодирование через Open-Meteo) или по координатам (обратное геокодирование через Nominatim) |
| **Данные о погоде** | Температура, точка росы, влажность, давление (мм рт. ст.), ветер, УФ-индекс, осадки, глубина снега, код погоды WMO |
| **Планирование** | Интервал для каждого города или общий по умолчанию; фоновая задача запускается каждую минуту и обрабатывает города, для которых наступило время проверки |
| **Админ-интерфейс** | CRUD для городов и пользователей, настройки, инструменты, статус планировщика, карта погоды, логи API и ошибок |
| **CLI** | Управление пользователями и городами, ручной запрос погоды |
| **Тестирование** | Модульные тесты pytest, e2e-тесты Playwright, CI в GitHub Actions |

## Стек технологий

- **Бэкенд:** Python 3.12, Flask, SQLAlchemy, Alembic, Flask-Login, Flask-Admin, APScheduler, Gunicorn
- **База данных:** PostgreSQL 16
- **Внешние API:** Open-Meteo (прогноз + геокодирование), Nominatim (обратное геокодирование)
- **Инструменты:** ruff, mypy, pytest, Docker Compose
- **E2E:** Playwright (TypeScript)

## Требования

- Python 3.12+
- Docker и Docker Compose (рекомендуется) или локальный экземпляр PostgreSQL
- Node.js 20+ (только для e2e-тестов)

## Быстрый старт (Docker)

Самый быстрый способ запустить всё — базу данных и веб-приложение:

```bash
docker compose up --build
```

При первом запуске контейнер автоматически применяет миграции. Затем создайте пользователя (в другом терминале, пока стек работает):

```bash
docker compose exec web flask users-create
```

Или создайте тестового пользователя `admin` / `admin`:

```bash
docker compose exec web flask users-seed
```

Откройте [http://localhost:5000](http://localhost:5000), войдите в систему и перейдите в **Tools → Seed test cities**, чтобы заполнить базу примерами.

## Локальная разработка

Используйте Docker только для PostgreSQL, а Flask-приложение запускайте на хосте — так удобнее итеративно разрабатывать.

### 1. Окружение Python

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

### 2. База данных

```bash
docker compose up -d db
```

Строка подключения по умолчанию (совпадает с `docker-compose.yml`):

```
postgresql://weather:weather@localhost:5432/weather
```

### 3. Конфигурация

Скопируйте пример файла окружения и при необходимости отредактируйте:

```bash
cp .env.example .env
```

| Переменная | Значение по умолчанию | Описание |
|------------|----------------------|----------|
| `DATABASE_URL` | `postgresql://weather:weather@localhost:5432/weather` | Строка подключения к PostgreSQL |
| `SECRET_KEY` | `dev-secret-key` | Ключ подписи сессий Flask — **обязательно смените в production** |
| `SCHEDULER_ENABLED` | `true` | Установите `false`, чтобы отключить фоновый сбор погоды |
| `FLASK_DEBUG` | — | Установите `1` для режима отладки Flask (только локально) |
| `FLASK_APP` | `wsgi:app` | Обязательна для команд Flask CLI |

Экспортируйте переменные или загрузите `.env` перед запуском команд:

```bash
export DATABASE_URL=postgresql://weather:weather@localhost:5432/weather
export FLASK_APP=wsgi:app
```

### 4. Инициализация и запуск

```bash
flask db upgrade
flask users-seed          # опционально: admin / admin
flask cities-seed         # опционально: 10 тестовых городов
flask run                 # http://localhost:5000
```

Для локального запуска в production-подобном режиме:

```bash
gunicorn --bind 0.0.0.0:5000 --workers 2 wsgi:app
```

## Панель администратора

После входа вы попадаете в список **Cities**. Все разделы доступны по адресу `/admin`:

| Раздел | Назначение |
|--------|------------|
| **Tools** | Заполнение/очистка тестовых данных, запрос погоды для всех «просроченных» городов, счётчики записей в таблицах |
| **Users** | Управление учётными записями (смена пароля при редактировании) |
| **Cities** | Добавление и редактирование городов; **Details** — таблица истории, графики и кнопка **Fetch now** |
| **Weather** | Только чтение: список всех сохранённых записей о погоде |
| **Settings** | Глобальный интервал проверки по умолчанию (в минутах) |
| **Background Tasks** | Список задач планировщика и их статус |
| **Map** | Карта Leaflet с последней температурой по каждому городу |
| **API Requests** | Лог в памяти исходящих HTTP-запросов к API погоды и геокодирования |
| **Error Log** | Лог в памяти ошибок приложения |

### Добавление города

Укажите **один из вариантов**:

- **Название + страна** — координаты определяются при первом запросе погоды, или
- **Широта + долгота** — отображаемое имя определяется через обратное геокодирование

Не смешивайте оба способа в одной записи. Пустой интервал для города означает использование глобального значения из **Settings**.

### Сбор погоды

- Планировщик запускается каждую **1 минуту** и вызывает `fetch_due_cities()`.
- Город считается «просроченным», если `last_checked_at` старше его эффективного интервала.
- **Fetch now** на странице города запрашивает погоду немедленно, вне расписания.
- **Tools → Fetch weather** запрашивает погоду для всех просроченных городов сразу.

## Команды CLI

Все команды требуют `FLASK_APP=wsgi:app` и корректный `DATABASE_URL`.

### Пользователи

```bash
flask users-create    # интерактивно: логин, пароль, подтверждение
flask users-show      # список пользователей
flask users-seed      # создать admin / admin, если пользователей нет
flask users-clear     # удалить всех пользователей (-y без подтверждения)
```

### Города

```bash
flask cities-seed     # добавить 10 тестовых городов, если таблица пуста
flask cities-show     # список городов с координатами и интервалами
```

### Погода

```bash
flask fetch-weather   # запросить погоду для всех городов, для которых наступило время
```

## Разработка

### Линтинг и проверка типов

```bash
make linter    # ruff check .
make types     # mypy app wsgi.py
```

Или напрямую:

```bash
ruff check .
mypy app wsgi.py
```

### Модульные тесты

Тесты используют PostgreSQL (как в CI):

```bash
export DATABASE_URL=postgresql://weather:weather@localhost:5432/weather_test
docker compose exec db psql -U weather -c "CREATE DATABASE weather_test;" 2>/dev/null || true
pytest -v
pytest -v --cov=app --cov-report=term-missing
```

### E2E-тесты (Playwright)

Запустите приложение локально, затем выполните тесты из каталога `e2e/`:

```bash
# Терминал 1 — приложение
export DATABASE_URL=postgresql://weather:weather@localhost:5432/weather_e2e
flask db upgrade
printf 'e2euser\ne2epass\ne2epass\n' | flask users-create
flask run --port 5000

# Терминал 2 — тесты
cd e2e
npm ci
npx playwright install chromium
BASE_URL=http://localhost:5000 E2E_USERNAME=e2euser E2E_PASSWORD=e2epass npm test
```

Из корня репозитория:

```bash
make browser-tests   # запускает npm test в e2e/ (сначала задайте BASE_URL и учётные данные)
```

E2E-наборы покрывают аутентификацию, города, настройки, планировщик, инструменты, логи и навигацию по админке.

## Структура проекта

```
app/
  admin.py, admin_views.py   # настройка Flask-Admin и кастомные представления
  blueprints/auth.py         # вход / выход
  cli.py                     # команды Flask CLI
  factory.py                 # фабрика приложения
  models.py                  # User, City, WeatherRecord, AppSettings
  scheduler.py               # фоновые задачи APScheduler
  services/                  # запрос погоды, геокодирование, seed-хелперы
  templates/                 # шаблоны Jinja2 (админ-интерфейс)
e2e/                         # тесты Playwright (TypeScript)
migrations/                  # миграции базы данных Alembic
tests/                       # модульные тесты pytest
wsgi.py                      # точка входа WSGI
docker-compose.yml           # сервисы PostgreSQL и web
Dockerfile                   # production-образ (Gunicorn)
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) запускается при push/PR в `main`:

1. **lint-and-test** — ruff, mypy, pytest с покрытием (сервис PostgreSQL)
2. **e2e** — запуск приложения, создание пользователя, Playwright с кэшированными ответами API через VCR

## Заметки для production

- Задайте надёжный `SECRET_KEY`.
- Используйте управляемый экземпляр PostgreSQL и соответствующий `DATABASE_URL`.
- Docker-образ выполняет `flask db upgrade` перед запуском Gunicorn.
- Логи API и ошибок хранятся **в памяти** и сбрасываются при перезапуске процесса — они предназначены для отладки, а не для долгосрочного аудита.
