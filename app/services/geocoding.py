from __future__ import annotations

from typing import Any

import requests

OPEN_METEO_GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
NOMINATIM_REVERSE_URL = "https://nominatim.openstreetmap.org/reverse"


class GeocodingError(Exception):
    pass


def geocode_city(city: str, country: str) -> tuple[str, float, float]:
    """Resolve city and country to a display name and coordinates."""
    city = city.strip()
    country = country.strip()
    if not city or not country:
        raise GeocodingError("City and country are required.")

    results = _search(city)
    match = _pick_result(results, city, country)
    if match is None:
        results = _search(f"{city}, {country}")
        match = _pick_result(results, city, country)

    if match is None:
        raise GeocodingError(f"Could not find {city!r} in {country!r}.")

    display_name = f"{match['name']}, {match['country']}"
    return display_name, float(match["latitude"]), float(match["longitude"])


def reverse_geocode(latitude: float, longitude: float) -> str:
    """Resolve coordinates to a display name."""
    try:
        response = requests.get(
            NOMINATIM_REVERSE_URL,
            params={
                "lat": str(latitude),
                "lon": str(longitude),
                "format": "json",
            },
            headers={"User-Agent": "flask-weather/1.0"},
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise GeocodingError(str(exc)) from exc

    data: dict[str, Any] = response.json()
    display_name = data.get("display_name")
    if not display_name:
        raise GeocodingError(
            f"Could not resolve coordinates ({latitude}, {longitude})."
        )
    return str(display_name)


def _search(name: str) -> list[dict[str, Any]]:
    try:
        params: dict[str, str | int] = {
            "name": name,
            "count": 10,
            "language": "en",
            "format": "json",
        }
        response = requests.get(
            OPEN_METEO_GEOCODING_URL,
            params=params,
            timeout=15,
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        raise GeocodingError(str(exc)) from exc

    data: dict[str, Any] = response.json()
    results = data.get("results")
    if not results:
        return []
    return list(results)


def _pick_result(
    results: list[dict[str, Any]], city: str, country: str
) -> dict[str, Any] | None:
    if not results:
        return None

    country_lower = country.lower()
    for result in results:
        result_country = str(result.get("country", "")).lower()
        result_code = str(result.get("country_code", "")).lower()
        if (
            country_lower in result_country
            or result_country in country_lower
            or country_lower == result_code
        ):
            return result

    city_lower = city.lower()
    for result in results:
        if str(result.get("name", "")).lower() == city_lower:
            return result

    return results[0] if len(results) == 1 else None
