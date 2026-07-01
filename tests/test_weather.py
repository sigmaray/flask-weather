from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from app.extensions import db
from app.models import AppSettings, City, OmWeatherRecord, OwmWeatherRecord
from app.services.weather import (
    HPA_TO_MMHG,
    WeatherFetchError,
    _pressure_hpa_to_mmhg,
    fetch_weather_for_city,
)
from app.services.weather_codes import weather_code_label


def test_weather_code_label() -> None:
    assert weather_code_label(0) == "Clear sky"
    assert weather_code_label(1) == "Mainly clear"
    assert weather_code_label(63) == "Moderate rain"
    assert weather_code_label(None) == "—"
    assert weather_code_label(123) == "Code 123"


def test_pressure_hpa_to_mmhg() -> None:
    assert _pressure_hpa_to_mmhg(1013.2) == round(1013.2 * HPA_TO_MMHG, 1)
    assert _pressure_hpa_to_mmhg(None) is None


OPEN_METEO_RESPONSE = {
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
        "cloud_cover": 42,
    },
    "daily": {
        "uv_index_max": [5.5],
    },
}

OWM_RESPONSE = {
    "dt": 1710000000,
    "timezone": 7200,
    "main": {
        "temp": 18.2,
        "feels_like": 17.5,
        "temp_min": 16.0,
        "temp_max": 20.0,
        "pressure": 1015,
        "humidity": 55,
    },
    "weather": [{"id": 800, "main": "Clear", "description": "clear sky"}],
    "wind": {"speed": 2.5, "deg": 180},
    "clouds": {"all": 10},
    "visibility": 10000,
    "rain": {"1h": 0.3},
    "snow": {"1h": 1.2},
}


def _mock_response(url: str, json_data: dict[str, object]) -> MagicMock:
    response = MagicMock()
    response.json.return_value = json_data
    response.raise_for_status = lambda: None
    response.url = url
    response.status_code = 200
    response.text = "{}"
    response.headers = {"Content-Type": "application/json"}
    response.request.method = "GET"
    response.request.headers = {"User-Agent": "python-requests/2.32.0"}
    return response


@pytest.fixture
def paris_city(app) -> int:
    with app.app_context():
        city = City(name="Paris", country="France", latitude=48.8566, longitude=2.3522)
        db.session.add(city)
        db.session.commit()
        return city.id


def test_fetch_weather_open_meteo_only(app, paris_city, mock_geocoding) -> None:
    with app.app_context():
        city = db.session.get(City, paris_city)
        assert city is not None
        settings = AppSettings.get_singleton()
        settings.enable_open_meteo = True
        settings.enable_openweathermap = False
        db.session.commit()

        with patch("app.memory_log.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                "https://api.open-meteo.com/v1/forecast",
                OPEN_METEO_RESPONSE,
            )
            open_meteo_record, owm_record = fetch_weather_for_city(city)

        assert open_meteo_record is not None
        assert owm_record is None
        assert open_meteo_record.temperature_c == 15.5
        assert open_meteo_record.cloudiness_percent == 42
        assert OmWeatherRecord.query.count() == 1
        assert OwmWeatherRecord.query.count() == 0


def test_fetch_weather_openweathermap_only(app, paris_city, mock_geocoding) -> None:
    with app.app_context():
        city = db.session.get(City, paris_city)
        assert city is not None
        settings = AppSettings.get_singleton()
        settings.enable_open_meteo = False
        settings.enable_openweathermap = True
        settings.openweathermap_api_key = "test-api-key"
        db.session.commit()

        with patch("app.memory_log.requests.get") as mock_get:
            mock_get.return_value = _mock_response(
                "https://api.openweathermap.org/data/2.5/weather",
                OWM_RESPONSE,
            )
            open_meteo_record, owm_record = fetch_weather_for_city(city)

        assert open_meteo_record is None
        assert owm_record is not None
        assert owm_record.temperature_c == 18.2
        assert owm_record.weather_main == "Clear"
        assert owm_record.precipitation_mm == 0.3
        assert owm_record.snow_1h_mm == 1.2
        assert OmWeatherRecord.query.count() == 0
        assert OwmWeatherRecord.query.count() == 1


def test_fetch_weather_both_sources(app, paris_city, mock_geocoding) -> None:
    with app.app_context():
        city = db.session.get(City, paris_city)
        assert city is not None
        settings = AppSettings.get_singleton()
        settings.enable_open_meteo = True
        settings.enable_openweathermap = True
        settings.openweathermap_api_key = "test-api-key"
        db.session.commit()

        def fake_get(url: str, *args, **kwargs):
            if "open-meteo" in url:
                return _mock_response(url, OPEN_METEO_RESPONSE)
            if "openweathermap" in url:
                return _mock_response(url, OWM_RESPONSE)
            raise AssertionError(f"Unexpected URL: {url}")

        with patch("app.memory_log.requests.get", side_effect=fake_get):
            open_meteo_record, owm_record = fetch_weather_for_city(city)

        assert open_meteo_record is not None
        assert owm_record is not None
        assert OmWeatherRecord.query.count() == 1
        assert OwmWeatherRecord.query.count() == 1


def test_fetch_weather_no_sources_enabled(app, paris_city) -> None:
    with app.app_context():
        city = db.session.get(City, paris_city)
        assert city is not None
        settings = AppSettings.get_singleton()
        settings.enable_open_meteo = False
        settings.enable_openweathermap = False
        db.session.commit()

        with pytest.raises(WeatherFetchError, match="No weather data sources are enabled"):
            fetch_weather_for_city(city)


def test_fetch_weather_owm_enabled_without_api_key(app, paris_city) -> None:
    with app.app_context():
        city = db.session.get(City, paris_city)
        assert city is not None
        settings = AppSettings.get_singleton()
        settings.enable_open_meteo = False
        settings.enable_openweathermap = True
        settings.openweathermap_api_key = None
        db.session.commit()

        with pytest.raises(WeatherFetchError, match="API key is not configured"):
            fetch_weather_for_city(city)
