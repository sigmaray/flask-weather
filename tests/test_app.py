from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

import pytest
from flask.testing import FlaskClient

from app.extensions import db
from app.models import City, User, WeatherRecord


def test_login_page_accessible(client: FlaskClient) -> None:
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_index_requires_login(client: FlaskClient) -> None:
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_login_success(auth_client: FlaskClient) -> None:
    response = auth_client.get("/")
    assert response.status_code == 200
    assert b"testuser" in response.data
    assert b"Logout" in response.data


def test_login_failure(client: FlaskClient, user: User) -> None:
    response = client.post(
        "/auth/login",
        data={"username": "testuser", "password": "wrong"},
        follow_redirects=True,
    )
    assert b"Invalid username or password" in response.data


def test_logout(auth_client: FlaskClient) -> None:
    response = auth_client.get("/auth/logout", follow_redirects=True)
    assert b"logged out" in response.data.lower() or b"Login" in response.data


def test_no_register_route(client: FlaskClient) -> None:
    response = client.get("/auth/register")
    assert response.status_code == 404


def test_create_user_cli(app, runner) -> None:
    result = runner.invoke(
        args=["create-user"],
        input="cliuser\nsecretpass\nsecretpass\n",
    )
    assert result.exit_code == 0
    with app.app_context():
        user = User.query.filter_by(username="cliuser").first()
        assert user is not None
        assert user.check_password("secretpass")


def test_create_user_password_mismatch(app, runner) -> None:
    result = runner.invoke(
        args=["create-user"],
        input="cliuser2\nsecretpass\notherpass\n",
    )
    assert result.exit_code == 1


def test_users_clear_cli(app, runner, user: User) -> None:
    with app.app_context():
        assert User.query.count() == 1

    result = runner.invoke(args=["users-clear", "-y"])
    assert result.exit_code == 0
    assert "Deleted 1 user(s)." in result.output

    with app.app_context():
        assert User.query.count() == 0


def test_users_clear_empty(app, runner) -> None:
    result = runner.invoke(args=["users-clear", "-y"])
    assert result.exit_code == 0
    assert "No users to delete." in result.output


def test_users_clear_abort(app, runner, user: User) -> None:
    result = runner.invoke(args=["users-clear"], input="n\n")
    assert result.exit_code == 1
    assert "Aborted." in result.output

    with app.app_context():
        assert User.query.count() == 1


def test_users_seed_cli(app, runner) -> None:
    result = runner.invoke(args=["users-seed"])
    assert result.exit_code == 0
    assert "Test user created" in result.output
    assert "admin" in result.output

    with app.app_context():
        user = User.query.filter_by(username="admin").first()
        assert user is not None
        assert user.check_password("admin")


def test_users_seed_idempotent(app, runner, user: User) -> None:
    result = runner.invoke(args=["users-seed"])
    assert result.exit_code == 0
    assert "already exists" in result.output

    with app.app_context():
        assert User.query.count() == 1


def test_add_city(auth_client: FlaskClient) -> None:
    response = auth_client.post(
        "/cities/add",
        data={
            "location_mode": "coordinates",
            "name": "Moscow",
            "latitude": "55.7558",
            "longitude": "37.6173",
            "check_interval_minutes": "30",
        },
        follow_redirects=True,
    )
    assert b"Moscow" in response.data
    with auth_client.application.app_context():
        city = City.query.filter_by(name="Moscow").first()
        assert city is not None
        assert city.check_interval_minutes == 30


def test_add_city_by_country(auth_client: FlaskClient) -> None:
    geocode_result = ("Berlin, Germany", 52.52437, 13.41053)
    with patch("app.blueprints.cities.geocode_city", return_value=geocode_result):
        response = auth_client.post(
            "/cities/add",
            data={
                "location_mode": "country_city",
                "country": "Germany",
                "city": "Berlin",
            },
            follow_redirects=True,
        )

    assert b"Berlin, Germany" in response.data
    with auth_client.application.app_context():
        city = City.query.filter_by(name="Berlin, Germany").first()
        assert city is not None
        assert city.latitude == pytest.approx(52.52437)
        assert city.longitude == pytest.approx(13.41053)


def test_settings_update(auth_client: FlaskClient) -> None:
    response = auth_client.post(
        "/settings/",
        data={"default_check_interval_minutes": "45"},
        follow_redirects=True,
    )
    assert b"Settings saved" in response.data
    with auth_client.application.app_context():
        from app.models import AppSettings

        assert AppSettings.get_singleton().default_check_interval_minutes == 45


def test_city_detail_with_records(auth_client: FlaskClient) -> None:
    with auth_client.application.app_context():
        city = City(name="Berlin", latitude=52.52, longitude=13.405)
        db.session.add(city)
        db.session.commit()
        record = WeatherRecord(
            city_id=city.id,
            recorded_at=datetime(2026, 1, 1, 12, 0),
            temperature_c=10.0,
            humidity_percent=50.0,
            wind_speed_ms=2.0,
        )
        db.session.add(record)
        db.session.commit()
        city_id = city.id

    response = auth_client.get(f"/cities/{city_id}")
    assert response.status_code == 200
    assert b"Berlin" in response.data
    assert b"10.0" in response.data
    assert b"temperatureChart" in response.data


def test_fetch_weather(auth_client: FlaskClient, mock_weather_api: None) -> None:
    with auth_client.application.app_context():
        city = City(name="Paris", latitude=48.85, longitude=2.35)
        db.session.add(city)
        db.session.commit()
        city_id = city.id

    response = auth_client.post(f"/cities/{city_id}/fetch", follow_redirects=True)
    assert b"Weather data fetched" in response.data
    with auth_client.application.app_context():
        records = WeatherRecord.query.filter_by(city_id=city_id).all()
        assert len(records) == 1
        assert records[0].temperature_c == 15.5
