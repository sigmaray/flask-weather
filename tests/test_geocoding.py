from __future__ import annotations

from unittest.mock import patch

import pytest

from app.services.geocoding import GeocodingError, geocode_city, reverse_geocode

BERLIN_RESPONSE = {
    "results": [
        {
            "name": "Berlin",
            "latitude": 52.52437,
            "longitude": 13.41053,
            "country": "Germany",
            "country_code": "DE",
        },
        {
            "name": "Berlin",
            "latitude": 44.469,
            "longitude": -71.1801,
            "country": "United States",
            "country_code": "US",
        },
    ]
}


def test_geocode_city_prefers_matching_country() -> None:
    with patch("app.services.geocoding.requests.get") as mock_get:
        mock_get.return_value.json.return_value = BERLIN_RESPONSE
        mock_get.return_value.raise_for_status = lambda: None

        name, lat, lon = geocode_city("Berlin", "Germany")

    assert name == "Berlin, Germany"
    assert lat == pytest.approx(52.52437)
    assert lon == pytest.approx(13.41053)


def test_geocode_city_not_found() -> None:
    with patch("app.services.geocoding.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"results": []}
        mock_get.return_value.raise_for_status = lambda: None

        with pytest.raises(GeocodingError, match="Could not find"):
            geocode_city("Nowhere", "Atlantis")


def test_reverse_geocode() -> None:
    with patch("app.services.geocoding.requests.get") as mock_get:
        mock_get.return_value.json.return_value = {"display_name": "Berlin, Germany"}
        mock_get.return_value.raise_for_status = lambda: None

        name = reverse_geocode(52.52, 13.405)

    assert name == "Berlin, Germany"
