from __future__ import annotations

from datetime import datetime
from unittest.mock import patch

from flask.testing import FlaskClient

from app.extensions import db
from app.memory_log import get_app_errors
from app.models import City, OmWeatherRecord, User


def test_login_page_accessible(client: FlaskClient) -> None:
    response = client.get("/auth/login")
    assert response.status_code == 200
    assert b"Login" in response.data


def test_health_ok(client: FlaskClient) -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.get_json() == {"status": "ok"}


def test_index_requires_login(client: FlaskClient) -> None:
    response = client.get("/")
    assert response.status_code == 302
    assert "/auth/login" in response.headers["Location"]


def test_login_success(auth_client: FlaskClient) -> None:
    response = auth_client.get("/", follow_redirects=True)
    assert response.status_code == 200
    assert b"Cities" in response.data


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
        args=["users-create"],
        input="cliuser\nsecretpass\nsecretpass\n",
    )
    assert result.exit_code == 0
    with app.app_context():
        user = User.query.filter_by(username="cliuser").first()
        assert user is not None
        assert user.check_password("secretpass")


def test_create_user_password_mismatch(app, runner) -> None:
    result = runner.invoke(
        args=["users-create"],
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


def test_users_show_empty(app, runner) -> None:
    result = runner.invoke(args=["users-show"])
    assert result.exit_code == 0
    assert "No users." in result.output


def test_users_show_with_users(app, runner, user: User) -> None:
    result = runner.invoke(args=["users-show"])
    assert result.exit_code == 0
    assert "ID  Username  Created" in result.output
    assert "testuser" in result.output


def test_cities_seed_cli(app, runner) -> None:
    result = runner.invoke(args=["cities-seed"])
    assert result.exit_code == 0
    assert "Added 10 test cities" in result.output

    with app.app_context():
        assert City.query.count() == 10
        berlin = City.query.filter_by(name="Berlin", country="Germany").first()
        assert berlin is not None
        assert berlin.latitude is None
        assert berlin.longitude is None


def test_cities_show_empty(app, runner) -> None:
    result = runner.invoke(args=["cities-show"])
    assert result.exit_code == 0
    assert "No cities." in result.output


def test_cities_show_with_cities(app, runner) -> None:
    with app.app_context():
        db.session.add(City(name="Berlin", country="Germany"))
        db.session.commit()

    result = runner.invoke(args=["cities-show"])
    assert result.exit_code == 0
    assert "ID  Name    Country  Geocoded" in result.output
    assert "Berlin" in result.output
    assert "Germany" in result.output
    assert "default" in result.output


def test_cities_seed_idempotent(app, runner) -> None:
    with app.app_context():
        db.session.add(City(name="Berlin", country="Germany"))
        db.session.commit()

    result = runner.invoke(args=["cities-seed"])
    assert result.exit_code == 0
    assert "already exist" in result.output

    with app.app_context():
        assert City.query.count() == 1


def test_seed_cities_tools(auth_client: FlaskClient) -> None:
    response = auth_client.post("/admin/tools/seed-cities/", follow_redirects=True)
    assert b"Added 10 test cities" in response.data
    with auth_client.application.app_context():
        assert City.query.count() == 10


def test_city_detail_with_records(auth_client: FlaskClient) -> None:
    with auth_client.application.app_context():
        city = City(name="Berlin", country="Germany")
        db.session.add(city)
        db.session.commit()
        record = OmWeatherRecord(
            city_id=city.id,
            recorded_at=datetime(2026, 1, 1, 12, 0),
            observed_at_local=datetime(2026, 1, 1, 13, 0),
            timezone="Europe/Berlin",
            temperature_c=10.0,
            dew_point_c=2.0,
            humidity_percent=50.0,
            pressure_mmhg=760.0,
            wind_speed_ms=2.0,
            apparent_temperature_c=8.5,
            weather_code=1,
            uv_index=3.0,
            snow_depth_m=0.05,
        )
        db.session.add(record)
        db.session.commit()
        city_id = city.id
        record_id = record.id

    response = auth_client.get(f"/admin/admin_cities/details/?id={city_id}")
    assert response.status_code == 200
    assert f"/admin/weather_records/details/?id={record_id}".encode() in response.data
    assert b"List" in response.data
    assert b"Create" in response.data
    assert b"Edit" in response.data
    assert b"Details" in response.data
    assert b"Berlin" in response.data
    assert b"10.0" in response.data
    assert b"Mainly clear" in response.data
    assert b"OpenWeatherMap" in response.data
    assert b"Open-Meteo" in response.data
    assert b"om-temperatureChart" in response.data
    assert b"om-pressureChart" in response.data
    assert b"om-snowChart" in response.data


def test_fetch_weather_tools_by_coordinates(
    auth_client: FlaskClient, mock_weather_api: None
) -> None:
    with auth_client.application.app_context():
        city = City(
            latitude=48.85,
            longitude=2.35,
            geocoded_name="Paris, France",
        )
        db.session.add(city)
        db.session.commit()
        city_id = city.id

    response = auth_client.post("/admin/tools/fetch-weather/", follow_redirects=True)
    assert b"Fetched weather for 1 cities" in response.data
    with auth_client.application.app_context():
        records = OmWeatherRecord.query.filter_by(city_id=city_id).all()
        assert len(records) == 1
        record = records[0]
        assert record.temperature_c == 15.5
        assert record.snow_depth_m == 0.12
        assert record.dew_point_c == 7.8
        assert record.pressure_mmhg == 760.0
        assert record.apparent_temperature_c == 14.2
        assert record.uv_index == 5.5
        assert record.timezone == "Europe/Paris"
        assert record.observed_at_local == datetime(2026, 6, 27, 14, 30)


def test_fetch_weather_tools_by_name_country(
    auth_client: FlaskClient, mock_weather_api: None, mock_geocoding: None
) -> None:
    with auth_client.application.app_context():
        city = City(name="Paris", country="France")
        db.session.add(city)
        db.session.commit()
        city_id = city.id

    response = auth_client.post("/admin/tools/fetch-weather/", follow_redirects=True)
    assert b"Fetched weather for 1 cities" in response.data
    with auth_client.application.app_context():
        records = OmWeatherRecord.query.filter_by(city_id=city_id).all()
        assert len(records) == 1


def test_fetch_weather_skips_duplicate_observed_at(
    auth_client: FlaskClient, mock_weather_api: None
) -> None:
    with auth_client.application.app_context():
        city = City(
            latitude=48.85,
            longitude=2.35,
            geocoded_name="Paris, France",
        )
        db.session.add(city)
        db.session.commit()
        city_id = city.id

    auth_client.post("/admin/tools/fetch-weather/", follow_redirects=True)
    auth_client.post("/admin/tools/fetch-weather/", follow_redirects=True)

    with auth_client.application.app_context():
        records = OmWeatherRecord.query.filter_by(city_id=city_id).all()
        assert len(records) == 1
        assert records[0].observed_at_local == datetime(2026, 6, 27, 14, 30)


def test_weather_map_page(auth_client: FlaskClient, mock_geocoding: None) -> None:
    with auth_client.application.app_context():
        city = City(name="Paris", country="France")
        db.session.add(city)
        db.session.commit()
        db.session.add(
            OmWeatherRecord(
                city_id=city.id,
                recorded_at=datetime(2026, 6, 27, 12, 0),
                observed_at_local=datetime(2026, 6, 27, 14, 0),
                timezone="Europe/Paris",
                temperature_c=22.4,
                weather_code=1,
            )
        )
        db.session.commit()
        assert city.latitude is None

    response = auth_client.get("/admin/weather_map/")
    assert response.status_code == 200
    assert b"Weather map" in response.data
    assert b"weatherMap" in response.data
    assert b"Paris, France" in response.data
    assert b"Mainly clear" in response.data
    assert b'"om_temperature_c": 22.4' in response.data
    assert b'"om_weather_emoji"' in response.data
    assert b'"latitude": 48.8566' in response.data

    with auth_client.application.app_context():
        city = City.query.filter_by(name="Paris", country="France").first()
        assert city is not None
        assert city.latitude == 48.8566
        assert city.longitude == 2.3522


def test_fetch_weather_persists_coordinates(
    auth_client: FlaskClient, mock_weather_api: None, mock_geocoding: None
) -> None:
    with auth_client.application.app_context():
        city = City(name="Paris", country="France")
        db.session.add(city)
        db.session.commit()
        city_id = city.id

    response = auth_client.post("/admin/tools/fetch-weather/", follow_redirects=True)
    assert b"Fetched weather for 1 cities" in response.data
    with auth_client.application.app_context():
        city = db.session.get(City, city_id)
        assert city is not None
        assert city.latitude == 48.8566
        assert city.longitude == 2.3522


def test_city_fetch_weather_shows_flash_when_geocoding_request_fails(
    auth_client: FlaskClient,
) -> None:
    with auth_client.application.app_context():
        city = City(name="E2E Bad City", country="NowhereLand")
        db.session.add(city)
        db.session.commit()
        city_id = city.id

    with patch("app.services.geocoding.requests.get", side_effect=RuntimeError("cassette miss")):
        response = auth_client.post(
            f"/admin/admin_cities/fetch-weather/?id={city_id}",
            follow_redirects=True,
        )

    assert response.status_code == 200
    assert b"Failed to fetch weather: cassette miss" in response.data

    errors = get_app_errors()
    assert len(errors) == 1
    assert errors[0].source == "weather.fetch"
    assert errors[0].exception_type == "GeocodingError"
    assert "Geocoding failed" in errors[0].message


def test_clear_cities_tools(auth_client: FlaskClient) -> None:
    with auth_client.application.app_context():
        db.session.add(City(name="Berlin", country="Germany"))
        db.session.commit()
        assert City.query.count() == 1

    response = auth_client.post("/admin/tools/clear-cities/", follow_redirects=True)
    assert b"Deleted 1 city/cities." in response.data
    with auth_client.application.app_context():
        assert City.query.count() == 0


def test_clear_om_weather_tools(auth_client: FlaskClient) -> None:
    with auth_client.application.app_context():
        city = City(name="Berlin", country="Germany")
        db.session.add(city)
        db.session.commit()
        db.session.add(
            OmWeatherRecord(
                city_id=city.id,
                recorded_at=datetime(2026, 1, 1, 12, 0),
                temperature_c=10.0,
            )
        )
        db.session.commit()
        assert OmWeatherRecord.query.count() == 1

    response = auth_client.post("/admin/tools/clear-om-weather/", follow_redirects=True)
    assert b"Deleted 1 Open-Meteo weather record(s)." in response.data
    with auth_client.application.app_context():
        assert OmWeatherRecord.query.count() == 0
        assert City.query.count() == 1


def test_clear_owm_weather_tools(auth_client: FlaskClient) -> None:
    from app.models import OwmWeatherRecord

    with auth_client.application.app_context():
        city = City(name="Berlin", country="Germany")
        db.session.add(city)
        db.session.commit()
        db.session.add(
            OwmWeatherRecord(
                city_id=city.id,
                recorded_at=datetime(2026, 1, 1, 12, 0),
                observed_at=datetime(2026, 1, 1, 12, 0),
                temperature_c=10.0,
            )
        )
        db.session.commit()
        assert OwmWeatherRecord.query.count() == 1

    response = auth_client.post("/admin/tools/clear-owm-weather/", follow_redirects=True)
    assert b"Deleted 1 OpenWeatherMap weather record(s)." in response.data
    with auth_client.application.app_context():
        assert OwmWeatherRecord.query.count() == 0
        assert City.query.count() == 1


def test_app_settings_admin_ensures_singleton(auth_client: FlaskClient) -> None:
    with auth_client.application.app_context():
        from app.models import AppSettings

        db.session.query(AppSettings).delete()
        db.session.commit()
        assert AppSettings.query.count() == 0

    response = auth_client.get("/admin/app_settings/")
    assert response.status_code == 200
    assert b"Default check interval" in response.data

    with auth_client.application.app_context():
        from app.models import AppSettings

        settings = db.session.get(AppSettings, 1)
        assert settings is not None
        assert settings.default_check_interval_minutes == 1


def test_run_worker_once(
    runner, app, mock_weather_api: None, mock_geocoding: None
) -> None:
    with app.app_context():
        city = City(name="Paris", country="France")
        db.session.add(city)
        db.session.commit()

    result = runner.invoke(args=["run-worker", "--once"])
    assert result.exit_code == 0
    assert "Fetched weather for 1 cities." in result.output
