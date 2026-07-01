from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, cast

import requests
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.memory_log import log_app_error, weather_api_get
from app.models import AppSettings, City, OwmWeatherRecord, OmWeatherRecord
from app.services.geocoding import GeocodingError, geocode_city

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"
OPENWEATHERMAP_URL = "https://api.openweathermap.org/data/2.5/weather"
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


def _fetch_open_meteo_for_city(
    city: City,
    latitude: float,
    longitude: float,
    recorded_at: datetime,
) -> OmWeatherRecord | None:
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
        response = weather_api_get(OPEN_METEO_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        log_app_error(
            "weather.fetch.open_meteo",
            f"Failed to fetch Open-Meteo weather for city {city.id}: {exc}",
            exc,
        )
        raise WeatherFetchError(str(exc)) from exc

    data: dict[str, Any] = response.json()
    current = data.get("current")
    if not current:
        log_app_error(
            "weather.fetch.open_meteo",
            f"No current weather data in Open-Meteo response for city {city.id}",
        )
        raise WeatherFetchError("No current weather data in Open-Meteo response")

    observed_at_local = _parse_local_observation_time(current)

    if observed_at_local is not None:
        existing = cast(
            OmWeatherRecord | None,
            OmWeatherRecord.query.filter_by(
                city_id=city.id,
                observed_at_local=observed_at_local,
            ).first(),
        )
        if existing is not None:
            return existing

    record = OmWeatherRecord(
        city_id=city.id,
        recorded_at=recorded_at,
        observed_at_local=observed_at_local,
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
    try:
        with db.session.begin_nested():
            db.session.add(record)
            db.session.flush()
    except IntegrityError:
        if observed_at_local is None:
            raise
        return cast(
            OmWeatherRecord,
            OmWeatherRecord.query.filter_by(
                city_id=city.id,
                observed_at_local=observed_at_local,
            ).one(),
        )
    return record


def _fetch_openweathermap_for_city(
    city: City,
    latitude: float,
    longitude: float,
    recorded_at: datetime,
    api_key: str,
) -> OwmWeatherRecord | None:
    params: dict[str, str | float] = {
        "lat": latitude,
        "lon": longitude,
        "appid": api_key,
        "units": "metric",
    }
    try:
        response = weather_api_get(OPENWEATHERMAP_URL, params=params, timeout=15)
        response.raise_for_status()
    except requests.RequestException as exc:
        log_app_error(
            "weather.fetch.openweathermap",
            f"Failed to fetch OpenWeatherMap weather for city {city.id}: {exc}",
            exc,
        )
        raise WeatherFetchError(str(exc)) from exc

    data: dict[str, Any] = response.json()
    main = data.get("main")
    if not main:
        log_app_error(
            "weather.fetch.openweathermap",
            f"No weather data in OpenWeatherMap response for city {city.id}",
        )
        raise WeatherFetchError("No weather data in OpenWeatherMap response")

    dt = data.get("dt")
    if dt is None:
        log_app_error(
            "weather.fetch.openweathermap",
            f"No observation time in OpenWeatherMap response for city {city.id}",
        )
        raise WeatherFetchError("No observation time in OpenWeatherMap response")

    observed_at = datetime.fromtimestamp(int(dt), tz=UTC).replace(tzinfo=None)

    existing = cast(
        OwmWeatherRecord | None,
        OwmWeatherRecord.query.filter_by(
            city_id=city.id,
            observed_at=observed_at,
        ).first(),
    )
    if existing is not None:
        return existing

    weather_items = data.get("weather") or []
    weather_item = weather_items[0] if weather_items else {}
    wind = data.get("wind") or {}
    clouds = data.get("clouds") or {}

    record = OwmWeatherRecord(
        city_id=city.id,
        recorded_at=recorded_at,
        observed_at=observed_at,
        timezone_offset_sec=_optional_int(data.get("timezone")),
        temperature_c=float(main["temp"]),
        feels_like_c=_optional_float(main.get("feels_like")),
        temp_min_c=_optional_float(main.get("temp_min")),
        temp_max_c=_optional_float(main.get("temp_max")),
        humidity_percent=_optional_float(main.get("humidity")),
        pressure_mmhg=_pressure_hpa_to_mmhg(_optional_float(main.get("pressure"))),
        wind_speed_ms=_optional_float(wind.get("speed")),
        wind_deg=_optional_float(wind.get("deg")),
        weather_id=_optional_int(weather_item.get("id")),
        weather_main=_optional_str(weather_item.get("main")),
        weather_description=_optional_str(weather_item.get("description")),
        visibility_m=_optional_float(data.get("visibility")),
        cloudiness_percent=_optional_float(clouds.get("all")),
    )
    try:
        with db.session.begin_nested():
            db.session.add(record)
            db.session.flush()
    except IntegrityError:
        return cast(
            OwmWeatherRecord,
            OwmWeatherRecord.query.filter_by(
                city_id=city.id,
                observed_at=observed_at,
            ).one(),
        )
    return record


def fetch_weather_for_city(
    city: City,
) -> tuple[OmWeatherRecord | None, OwmWeatherRecord | None]:
    settings = AppSettings.get_singleton()
    if not settings.enable_open_meteo and not settings.enable_openweathermap:
        raise WeatherFetchError("No weather data sources are enabled in settings.")

    try:
        latitude, longitude = ensure_city_coordinates(city)
    except GeocodingError as exc:
        log_app_error(
            "weather.fetch",
            f"Geocoding failed for city {city.id}: {exc}",
            exc,
        )
        raise WeatherFetchError(str(exc)) from exc

    recorded_at = datetime.now(UTC).replace(tzinfo=None)
    open_meteo_record: OmWeatherRecord | None = None
    owm_record: OwmWeatherRecord | None = None
    errors: list[str] = []

    if settings.enable_open_meteo:
        try:
            open_meteo_record = _fetch_open_meteo_for_city(
                city,
                latitude,
                longitude,
                recorded_at,
            )
        except WeatherFetchError as exc:
            errors.append(f"Open-Meteo: {exc}")

    if settings.enable_openweathermap:
        api_key = (settings.openweathermap_api_key or "").strip()
        if not api_key:
            errors.append("OpenWeatherMap: API key is not configured.")
        else:
            try:
                owm_record = _fetch_openweathermap_for_city(
                    city,
                    latitude,
                    longitude,
                    recorded_at,
                    api_key,
                )
            except WeatherFetchError as exc:
                errors.append(f"OpenWeatherMap: {exc}")

    if open_meteo_record is None and owm_record is None:
        if errors:
            raise WeatherFetchError("; ".join(errors))
        raise WeatherFetchError("No weather data was fetched.")

    city.last_checked_at = recorded_at
    db.session.commit()
    return open_meteo_record, owm_record


def fetch_due_cities() -> list[tuple[OmWeatherRecord | None, OwmWeatherRecord | None]]:
    default_interval = AppSettings.get_singleton().default_check_interval_minutes
    now = datetime.utcnow()
    results: list[tuple[OmWeatherRecord | None, OwmWeatherRecord | None]] = []

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
                results.append(fetch_weather_for_city(city))
            except WeatherFetchError:
                db.session.rollback()
    return results


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
    count = OmWeatherRecord.query.count()
    if count == 0:
        return ("info", "No weather records to delete.")

    OmWeatherRecord.query.delete()
    db.session.commit()
    return ("success", f"Deleted {count} weather record(s).")
