from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import AppSettings, User


@pytest.fixture(autouse=True)
def clear_memory_logs() -> Generator[None, None, None]:
    from app.memory_log import clear_all

    clear_all()
    yield
    clear_all()


@pytest.fixture
def app() -> Generator[Flask, None, None]:
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SCHEDULER_ENABLED": False,
            "SECRET_KEY": "test-secret",
        }
    )
    with application.app_context():
        db.create_all()
        AppSettings.get_singleton()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app: Flask) -> FlaskClient:
    return app.test_client()


@pytest.fixture
def runner(app: Flask):
    return app.test_cli_runner()


@pytest.fixture
def user(app: Flask) -> User:
    with app.app_context():
        u = User(username="testuser")
        u.set_password("password123")
        db.session.add(u)
        db.session.commit()
        return u


@pytest.fixture
def auth_client(client: FlaskClient, user: User) -> FlaskClient:
    client.post(
        "/auth/login",
        data={"username": "testuser", "password": "password123"},
        follow_redirects=True,
    )
    return client


@pytest.fixture
def mock_geocoding() -> Generator[None, None, None]:
    from app.services.geocoding import GeocodingError

    coords: dict[tuple[str, str], tuple[str, float, float]] = {
        ("Berlin", "Germany"): ("Berlin, Germany", 52.52, 13.405),
        ("Paris", "France"): ("Paris, France", 48.8566, 2.3522),
        ("London", "United Kingdom"): ("London, United Kingdom", 51.5074, -0.1278),
        ("Tokyo", "Japan"): ("Tokyo, Japan", 35.6762, 139.6503),
        ("New York", "United States"): ("New York, United States", 40.7128, -74.0060),
    }

    def fake_geocode(city: str, country: str) -> tuple[str, float, float]:
        key = (city, country)
        if key not in coords:
            raise GeocodingError(f"Could not find {city!r} in {country!r}.")
        return coords[key]

    with patch("app.services.weather.geocode_city", side_effect=fake_geocode):
        yield


@pytest.fixture
def mock_weather_api() -> Generator[None, None, None]:
    response_data = {
        "timezone": "Europe/Paris",
        "current": {
            "time": "2026-06-27T14:30",
            "temperature_2m": 15.5,
            "relative_humidity_2m": 60,
            "dew_point_2m": 7.8,
            "pressure_msl": 1013.2,
            "apparent_temperature": 14.2,
            "wind_speed_10m": 3.2,
            "weather_code": 1,
            "precipitation": 0.0,
            "snow_depth": 0.12,
        },
        "daily": {
            "uv_index_max": [5.5],
        },
    }
    with patch("app.memory_log.requests.get") as mock_get:
        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status = lambda: None
        mock_get.return_value.url = "https://api.open-meteo.com/v1/forecast?latitude=48.8566"
        mock_get.return_value.status_code = 200
        mock_get.return_value.text = '{"timezone":"Europe/Paris"}'
        mock_get.return_value.headers = {"Content-Type": "application/json"}
        mock_get.return_value.request.method = "GET"
        mock_get.return_value.request.headers = {"User-Agent": "python-requests/2.32.0"}
        yield
