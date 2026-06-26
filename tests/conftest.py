from __future__ import annotations

from collections.abc import Generator
from unittest.mock import patch

import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import AppSettings, User


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
def mock_weather_api() -> Generator[None, None, None]:
    response_data = {
        "current": {
            "temperature_2m": 15.5,
            "relative_humidity_2m": 60,
            "wind_speed_10m": 3.2,
            "weather_code": 1,
            "precipitation": 0.0,
        }
    }
    with patch("app.services.weather.requests.get") as mock_get:
        mock_get.return_value.json.return_value = response_data
        mock_get.return_value.raise_for_status = lambda: None
        yield
