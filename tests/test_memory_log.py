from __future__ import annotations

from unittest.mock import MagicMock

import pytest
from flask.testing import FlaskClient

from app.memory_log import format_http_body, get_app_errors, get_weather_api_requests
from app.models import City


def test_weather_api_log_page_requires_auth(client: FlaskClient) -> None:
    response = client.get("/admin/weather_api_log/")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_app_error_log_page_requires_auth(client: FlaskClient) -> None:
    response = client.get("/admin/app_error_log/")
    assert response.status_code == 302
    assert "/auth/login" in response.location


def test_weather_api_log_page_empty(auth_client: FlaskClient) -> None:
    response = auth_client.get("/admin/weather_api_log/")
    assert response.status_code == 200
    assert b"Weather API Requests" in response.data
    assert b"No requests logged yet." in response.data


def test_app_error_log_page_empty(auth_client: FlaskClient) -> None:
    response = auth_client.get("/admin/app_error_log/")
    assert response.status_code == 200
    assert b"Application Errors" in response.data
    assert b"No errors logged yet." in response.data


def test_weather_api_log_page(
    auth_client: FlaskClient,
    mock_geocoding,
    mock_weather_api,
    app,
) -> None:
    with app.app_context():
        city = City(name="Paris", country="France")
        from app.extensions import db

        db.session.add(city)
        db.session.commit()

        from app.services.weather import fetch_weather_for_city

        fetch_weather_for_city(city)

    response = auth_client.get("/admin/weather_api_log/")
    assert response.status_code == 200
    assert b"Weather API Requests" in response.data
    assert b"GET" in response.data

    requests = get_weather_api_requests()
    assert len(requests) == 1
    assert requests[0].method == "GET"
    assert requests[0].status_code is not None


def test_app_error_log_page(auth_client: FlaskClient) -> None:
    from app.memory_log import log_app_error

    log_app_error("test.source", "Something went wrong", ValueError("boom"))

    response = auth_client.get("/admin/app_error_log/")
    assert response.status_code == 200
    assert b"Application Errors" in response.data
    assert b"test.source" in response.data
    assert b"Something went wrong" in response.data

    errors = get_app_errors()
    assert len(errors) == 1
    assert errors[0].exception_type == "ValueError"


def test_weather_api_request_logged_on_failure(
    app,
    mock_geocoding,
) -> None:
    from unittest.mock import patch

    import requests

    with app.app_context():
        city = City(name="Paris", country="France")
        from app.extensions import db

        db.session.add(city)
        db.session.commit()

        mock_response = MagicMock()
        mock_response.raise_for_status.side_effect = requests.HTTPError("503 Service Unavailable")
        mock_response.url = "https://api.open-meteo.com/v1/forecast"
        mock_response.status_code = 503
        mock_response.text = "Service Unavailable"
        mock_response.headers = {"Content-Type": "text/plain"}
        mock_response.request.method = "GET"
        mock_response.request.headers = {"User-Agent": "python-requests"}

        with patch("app.memory_log.requests.get", return_value=mock_response):
            from app.services.weather import WeatherFetchError, fetch_weather_for_city

            with pytest.raises(WeatherFetchError):
                fetch_weather_for_city(city)

    requests_log = get_weather_api_requests()
    assert len(requests_log) == 1
    assert requests_log[0].status_code == 503
    assert "Service Unavailable" in requests_log[0].response_body

    errors = get_app_errors()
    assert len(errors) == 1
    assert errors[0].source == "weather.fetch.open_meteo"


def test_format_http_body_json() -> None:
    body = '{"timezone":"Europe/Paris","current":{"temperature_2m":15.5}}'
    formatted = format_http_body(body, {"Content-Type": "application/json"})
    assert '"timezone": "Europe/Paris"' in formatted
    assert '"temperature_2m": 15.5' in formatted


def test_format_http_body_xml() -> None:
    body = '<?xml version="1.0"?><root><item>value</item></root>'
    formatted = format_http_body(body, {"Content-Type": "application/xml"})
    assert "<root>" in formatted
    assert "<item>" in formatted
    assert "value" in formatted


def test_format_http_body_plain_text_unchanged() -> None:
    body = "Service Unavailable"
    assert format_http_body(body, {"Content-Type": "text/plain"}) == body


def test_weather_api_log_page_formats_json_body(
    auth_client: FlaskClient,
    mock_geocoding,
    mock_weather_api,
    app,
) -> None:
    with app.app_context():
        city = City(name="Paris", country="France")
        from app.extensions import db

        db.session.add(city)
        db.session.commit()

        from app.services.weather import fetch_weather_for_city

        fetch_weather_for_city(city)

    response = auth_client.get("/admin/weather_api_log/")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "timezone" in text
    assert "Europe/Paris" in text
    formatted = format_http_body(
        '{"timezone":"Europe/Paris"}',
        {"Content-Type": "application/json"},
    )
    assert '\n  "timezone"' in formatted
