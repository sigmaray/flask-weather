# Flask Weather Archive

**English** | [Русский](README.ru.md)

A self-hosted weather history archive for cities. The app periodically fetches current conditions from [Open-Meteo](https://open-meteo.com/), stores them in PostgreSQL, and lets you browse history tables and charts through a Flask-Admin web UI.

## What it does

1. You add **cities** — by name and country, or by latitude/longitude.
2. A **background scheduler** (or manual actions) fetches weather on a configurable interval.
3. Each fetch appends a **weather record** (temperature, humidity, wind, pressure, and more).
4. The **admin panel** shows per-city history, charts, a map of latest readings, and diagnostic logs.

There is no public sign-up: users are created only via the CLI or admin tools.

## Features

| Area | Details |
|------|---------|
| **Authentication** | Login page; no self-registration |
| **Cities** | Add by name + country (geocoded via Open-Meteo) or by coordinates (reverse-geocoded via Nominatim) |
| **Weather data** | Temperature, dew point, humidity, pressure (mmHg), wind, UV, precipitation, snow depth, WMO weather code |
| **Scheduling** | Per-city interval or global default; background job runs every minute and fetches cities that are due |
| **Admin UI** | CRUD for cities and users, settings, tools, scheduler status, weather map, API/error logs |
| **CLI** | User and city management, manual weather fetch |
| **Testing** | pytest unit tests, Playwright e2e tests, GitHub Actions CI |

## Tech stack

- **Backend:** Python 3.12, Flask, SQLAlchemy, Alembic, Flask-Login, Flask-Admin, APScheduler, Gunicorn
- **Database:** PostgreSQL 16
- **External APIs:** Open-Meteo (forecast + geocoding), Nominatim (reverse geocoding)
- **Tooling:** ruff, mypy, pytest, Docker Compose
- **E2E:** Playwright (TypeScript)

## Requirements

- Python 3.12+
- Docker and Docker Compose (recommended), or a local PostgreSQL instance
- Node.js 20+ (only for e2e tests)

## Quick start (Docker)

The fastest way to run everything — database, web app, and background worker:

```bash
docker compose up --build
```

The stack runs two application processes: **web** (HTTP + admin UI) and **worker** (periodic weather fetching via `flask run-worker`). The web service disables the in-process scheduler (`INTERNAL_SCHEDULER_ENABLED=false`) so Gunicorn can use multiple workers without duplicating fetches.

On first start the web container runs migrations automatically. Then create a user (in another terminal, with the stack running):

```bash
docker compose exec web flask users-create
```

Or seed a dev user `admin` / `admin`:

```bash
docker compose exec web flask users-seed
```

Open [http://localhost:5000](http://localhost:5000), sign in, and go to **Tools → Seed test cities** to populate sample data.

## Local development

Use Docker only for PostgreSQL and run the Flask app on the host for faster iteration.

### 1. Python environment

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .
```

### 2. Database

```bash
docker compose up -d db
```

Default connection (matches `docker-compose.yml`):

```
postgresql://postgres:postgres@localhost:5432/weather
```

### 3. Configuration

Copy the example env file and adjust if needed:

```bash
cp .env.example .env
```

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql://postgres:postgres@localhost:5432/weather` | PostgreSQL connection string |
| `SECRET_KEY` | `dev-secret-key` | Flask session signing key — **change in production** |
| `INTERNAL_SCHEDULER_ENABLED` | `false` | Set to `true` to run APScheduler inside the web process (local dev). Docker leaves it `false` and uses the `worker` service |
| `FLASK_DEBUG` | — | Set to `1` for Flask debug mode (local dev only) |
| `FLASK_APP` | `wsgi:app` | Required for Flask CLI commands |

Export variables or load `.env` before running commands:

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/weather
export FLASK_APP=wsgi:app
```

### 4. Initialize and run

```bash
flask db upgrade
flask users-seed          # optional: admin / admin
flask cities-seed         # optional: 10 test cities
flask run                 # http://localhost:5000
```

For production-like serving locally (single process with in-process scheduler):

```bash
gunicorn --bind 0.0.0.0:5000 --workers 1 wsgi:app
```

To mirror the Docker split locally, run the worker in a second terminal:

```bash
export INTERNAL_SCHEDULER_ENABLED=false
gunicorn --bind 0.0.0.0:5000 --workers 2 wsgi:app

# terminal 2
flask run-worker
```

> **Background fetching.** Docker Compose runs weather polling in a separate **worker** container (`flask run-worker`). For local development, run `flask run-worker` in a second terminal (same as production), or set `INTERNAL_SCHEDULER_ENABLED=true` to use the in-process APScheduler in the web process.

## Admin panel

After login you land on the **Cities** list. All sections live under `/admin`:

| Section | Purpose |
|---------|---------|
| **Tools** | Seed/clear test data, fetch weather for all due cities, view table counts |
| **Users** | Manage accounts (password change on edit) |
| **Cities** | Add/edit cities; open **Details** for history table, charts, and **Fetch now** |
| **Weather** | Read-only list of all stored weather records |
| **Settings** | Global default check interval (minutes) |
| **Background Tasks** | Scheduler job list and status |
| **Map** | Leaflet map with latest temperature per city |
| **API Requests** | In-memory log of outbound weather/geocoding HTTP calls |
| **Error Log** | In-memory log of application errors |

### Adding a city

Provide **either**:

- **Name + country** — coordinates are resolved on first fetch, or
- **Latitude + longitude** — a display name is resolved via reverse geocoding

Do not mix both in one record. An empty per-city interval uses the global default from **Settings**.

### Weather fetching

- **Docker / production:** the `worker` service runs `flask run-worker` every 60 seconds and calls `fetch_due_cities()`.
- **Local dev:** run `flask run-worker` in a second terminal, or set `INTERNAL_SCHEDULER_ENABLED=true` for an in-process scheduler that wakes every **1 minute**.
- A city is due when `last_checked_at` is older than its effective interval.
- **Fetch now** on a city detail page fetches immediately, regardless of schedule.
- **Tools → Fetch weather** fetches all due cities at once.

## CLI commands

All commands require `FLASK_APP=wsgi:app` and a valid `DATABASE_URL`.

### Users

```bash
flask users-create    # interactive: login, password, confirmation
flask users-show      # list users
flask users-seed      # create admin / admin if no users exist
flask users-clear     # delete all users (-y to skip confirmation)
```

### Cities

```bash
flask cities-seed     # add 10 test cities if the table is empty
flask cities-show     # list cities with coordinates and intervals
```

### Weather

```bash
flask fetch-weather        # fetch for all cities that are currently due
flask om-weather-clear     # delete all Open-Meteo records (-y to skip confirmation)
flask owm-weather-clear    # delete all OpenWeatherMap records (-y to skip confirmation)
flask run-worker           # dedicated process: fetch due cities every 60s (Docker worker)
flask run-worker --once    # single fetch cycle, then exit
```

## Development

### Linting and type checking

```bash
ruff check .
mypy app wsgi.py
```

### Unit tests

Tests use a PostgreSQL database (same as CI):

```bash
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/weather_test
docker compose exec db psql -U postgres -c "CREATE DATABASE weather_test;" 2>/dev/null || true
pytest -v
pytest -v --cov=app --cov-report=term-missing
```

### E2E tests (Playwright)

Start the app locally, then run tests from the `e2e/` directory:

```bash
# Terminal 1 — app
export DATABASE_URL=postgresql://postgres:postgres@localhost:5432/weather_e2e
flask db upgrade
printf 'e2euser\ne2epass\ne2epass\n' | flask users-create
flask run --port 5000

# Terminal 2 — tests
cd e2e
npm ci
npx playwright install chromium
BASE_URL=http://localhost:5000 E2E_USERNAME=e2euser E2E_PASSWORD=e2epass npm test
```

E2E suites cover auth, cities, settings, scheduler, tools, logs, and admin navigation.

## Project layout

```
app/
  admin.py, admin_views.py   # Flask-Admin setup and custom views
  blueprints/auth.py         # Login / logout
  cli.py                     # Flask CLI commands
  factory.py                 # Application factory
  models.py                  # User, City, OmWeatherRecord, AppSettings
  scheduler.py               # APScheduler background jobs
  services/                  # Weather fetch, geocoding, seed helpers
  templates/                 # Jinja2 templates (admin UI)
e2e/                         # Playwright tests (TypeScript)
migrations/                  # Alembic database migrations
tests/                       # pytest unit tests
wsgi.py                      # WSGI entry point
docker-compose.yml           # web + worker services (external PostgreSQL on infra)
docker-compose.with-pg.yml   # optional overlay: bundled PostgreSQL for local Docker
Dockerfile                   # Production image (Gunicorn)
```

## CI

GitHub Actions (`.github/workflows/ci.yml`) runs on push/PR to `main`:

1. **lint-and-test** — ruff, mypy, pytest with coverage (PostgreSQL service)
2. **e2e** — starts the app, seeds a user, runs Playwright with VCR-cached API responses

## Production notes

- Set a strong `SECRET_KEY`.
- Use a managed PostgreSQL instance and set `DATABASE_URL` accordingly. For a shared PostgreSQL 16 setup on a VPS (one instance, multiple Docker apps), see [docs/example-postgresql-docker-compose/README.md](docs/example-postgresql-docker-compose/README.md).
- The Docker image runs `flask db upgrade` before Gunicorn on startup.
- API and error logs are stored **in memory** and reset on process restart — they are intended for debugging, not long-term auditing.
