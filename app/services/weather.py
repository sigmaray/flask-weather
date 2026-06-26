from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import requests

from app.extensions import db
from app.models import City, WeatherRecord

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherFetchError(Exception):
    pass


def fetch_weather_for_city(city: City) -> WeatherRecord:
    params: dict[str, str | float] = {
        "latitude": city.latitude,
        "longitude": city.longitude,
        "current": "temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code,precipitation,snow_depth",
        "timezone": "UTC",
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
        temperature_c=float(current["temperature_2m"]),
        humidity_percent=_optional_float(current.get("relative_humidity_2m")),
        wind_speed_ms=_optional_float(current.get("wind_speed_10m")),
        weather_code=_optional_int(current.get("weather_code")),
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
