# Flask Weather Archive

Weather history archive for cities, managed via a Flask web UI and admin panel.

## Features

- Authentication (login via UI; users created only via CLI)
- Admin panel (Flask-Admin) for logged-in users
- City management with per-city or default check intervals
- Weather history tables and charts per city
- Settings page for default check interval
- Background scheduler for periodic weather fetches (Open-Meteo API)

## Stack

- Flask, SQLAlchemy, Alembic, Flask-Login, Flask-Admin
- PostgreSQL, Docker Compose
- pytest, ruff, mypy
- Playwright (TypeScript) for e2e tests
- GitHub Actions CI

## Quick start

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
pip install -e .

docker compose up -d db
export DATABASE_URL=postgresql://weather:weather@localhost:5432/weather
export FLASK_APP=wsgi:app
flask db upgrade
flask create-user admin
docker compose up --build
```

Open http://localhost:5000 and sign in.

## Development

```bash
ruff check .
mypy app wsgi.py
pytest -v
```

### E2E tests

```bash
# Start app locally, then:
cd e2e && npm ci && npx playwright install chromium
BASE_URL=http://localhost:5000 E2E_USERNAME=admin E2E_PASSWORD=... npm test
```

## CLI

```bash
flask create-user <username>   # prompts for password + confirmation
flask fetch-weather            # fetch for all due cities
```
