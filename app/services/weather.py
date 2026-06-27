from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from app.extensions import db
from app.models import City, WeatherRecord
from app.services.geocoding import GeocodingError, geocode_city

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
HPA_TO_MMHG = 0.750061683


class WeatherFetchError(Exception):
    pass


def resolve_city_coordinates(city: City) -> tuple[float, float]:
    """Return latitude and longitude for a city, geocoding by name if needed."""
    if city.has_coordinate_location():
        assert city.latitude is not None
        assert city.longitude is not None
        return city.latitude, city.longitude

    if city.has_name_location():
        assert city.name is not None
        assert city.country is not None
        _, latitude, longitude = geocode_city(city.name, city.country)
        return latitude, longitude

    raise GeocodingError("City has no location data.")


def ensure_city_coordinates(city: City) -> tuple[float, float]:
    """Resolve coordinates and persist them on the city when missing."""
    if city.has_coordinate_location():
        assert city.latitude is not None
        assert city.longitude is not None
        return city.latitude, city.longitude

    latitude, longitude = resolve_city_coordinates(city)
    city.latitude = latitude
    city.longitude = longitude
    return latitude, longitude


def _parse_local_observation_time(current: dict[str, Any]) -> datetime | None:
    time_str = current.get("time")
    if not time_str:
        return None
    try:
        return datetime.fromisoformat(str(time_str))
    except ValueError:
        return None


def _pressure_hpa_to_mmhg(hpa: float | None) -> float | None:
    if hpa is None:
        return None
    return round(hpa * HPA_TO_MMHG, 1)


def _daily_uv_index(data: dict[str, Any]) -> float | None:
    daily = data.get("daily")
    if not daily:
        return None
    values = daily.get("uv_index_max")
    if not values:
        return None
    return _optional_float(values[0])


def fetch_weather_for_city(city: City) -> WeatherRecord:
    try:
        latitude, longitude = ensure_city_coordinates(city)
    except GeocodingError as exc:
        raise WeatherFetchError(str(exc)) from exc
    params: dict[str, str | float] = {
        "latitude": latitude,
        "longitude": longitude,
        "current": (
            "temperature_2m,relative_humidity_2m,dew_point_2m,pressure_msl,"
            "apparent_temperature,wind_speed_10m,weather_code,precipitation,snow_depth"
        ),
        "daily": "uv_index_max",
        "timezone": "auto",
        "wind_speed_unit": "ms",
    }
    try:
        response = requests.get(OPEN_METEO_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        raise WeatherFetchError(str(exc)) from exc

    data: dict[str, Any] = response.json()
    current = data.get("current")
    if not current:
        raise WeatherFetchError("No current weather data in response")

    recorded_at = datetime.now(UTC).replace(tzinfo=None)
    record = WeatherRecord(
        city_id=city.id,
        recorded_at=recorded_at,
        observed_at_local=_parse_local_observation_time(current),
        timezone=_optional_str(data.get("timezone")),
        temperature_c=float(current["temperature_2m"]),
        dew_point_c=_optional_float(current.get("dew_point_2m")),
        humidity_percent=_optional_float(current.get("relative_humidity_2m")),
        pressure_mmhg=_pressure_hpa_to_mmhg(_optional_float(current.get("pressure_msl"))),
        wind_speed_ms=_optional_float(current.get("wind_speed_10m")),
        apparent_temperature_c=_optional_float(current.get("apparent_temperature")),
        weather_code=_optional_int(current.get("weather_code")),
        uv_index=_daily_uv_index(data),
        precipitation_mm=_optional_float(current.get("precipitation")),
        snow_depth_m=_optional_float(current.get("snow_depth")),
    )
    city.last_checked_at = recorded_at
    db.session.add(record)
    db.session.commit()
    return record


def fetch_due_cities() -> list[WeatherRecord]:
    from datetime import timedelta

    from app.models import AppSettings

    default_interval = AppSettings.get_singleton().default_check_interval_minutes
    now = datetime.utcnow()
    records: list[WeatherRecord] = []

    for city in City.query.all():
        interval = (
            city.check_interval_minutes
            if city.check_interval_minutes is not None
            else default_interval
        )
        due = city.last_checked_at is None or now - city.last_checked_at >= timedelta(
            minutes=interval
        )
        if due:
            try:
                records.append(fetch_weather_for_city(city))
            except WeatherFetchError:
                db.session.rollback()
    return records


def _optional_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _optional_int(value: Any) -> int | None:
    if value is None:
        return None
    return int(value)


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def clear_weather_records() -> tuple[str, str]:
    """Delete all weather records. Returns (flash category, message)."""
    count = WeatherRecord.query.count()
    if count == 0:
        return ("info", "No weather records to delete.")

    WeatherRecord.query.delete()
    db.session.commit()
    return ("success", f"Deleted {count} weather record(s).")
