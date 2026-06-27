from __future__ import annotations

import traceback
from collections import deque
from dataclasses import dataclass
from datetime import UTC, datetime
from threading import Lock
from typing import Any

import requests

_MAX_REQUESTS = 100
_MAX_ERRORS = 100

_lock = Lock()
_request_log: deque[WeatherApiRequestLog] = deque(maxlen=_MAX_REQUESTS)
_error_log: deque[AppErrorLog] = deque(maxlen=_MAX_ERRORS)


@dataclass
class WeatherApiRequestLog:
    timestamp: datetime
    method: str
    url: str
    client_headers: dict[str, str]
    server_headers: dict[str, str]
    response_body: str
    status_code: int | None


@dataclass
class AppErrorLog:
    timestamp: datetime
    source: str
    message: str
    exception_type: str | None = None
    traceback: str | None = None


def _header_dict(headers: Any) -> dict[str, str]:
    if headers is None:
        return {}
    return {str(key): str(value) for key, value in headers.items()}


def log_weather_api_request(
    *,
    method: str,
    url: str,
    client_headers: dict[str, str],
    server_headers: dict[str, str],
    response_body: str,
    status_code: int | None,
) -> None:
    entry = WeatherApiRequestLog(
        timestamp=datetime.now(UTC).replace(tzinfo=None),
        method=method,
        url=url,
        client_headers=client_headers,
        server_headers=server_headers,
        response_body=response_body,
        status_code=status_code,
    )
    with _lock:
        _request_log.appendleft(entry)


def log_weather_api_request_from_response(response: requests.Response) -> None:
    log_weather_api_request(
        method=response.request.method or "GET",
        url=response.url,
        client_headers=_header_dict(response.request.headers),
        server_headers=_header_dict(response.headers),
        response_body=response.text,
        status_code=response.status_code,
    )


def log_weather_api_request_failed(
    *,
    method: str,
    url: str,
    client_headers: dict[str, str],
    error_message: str,
) -> None:
    log_weather_api_request(
        method=method,
        url=url,
        client_headers=client_headers,
        server_headers={},
        response_body=error_message,
        status_code=None,
    )


def weather_api_get(url: str, params: dict[str, Any], timeout: int = 15) -> requests.Response:
    prepared_headers: dict[str, str] = {}
    try:
        response = requests.get(url, params=params, timeout=timeout)
        log_weather_api_request_from_response(response)
        return response
    except requests.RequestException as exc:
        request = getattr(exc, "request", None)
        if request is not None:
            log_weather_api_request_failed(
                method=request.method or "GET",
                url=request.url or url,
                client_headers=_header_dict(request.headers),
                error_message=str(exc),
            )
        else:
            log_weather_api_request_failed(
                method="GET",
                url=url,
                client_headers=prepared_headers,
                error_message=str(exc),
            )
        raise


def log_app_error(source: str, message: str, exc: BaseException | None = None) -> None:
    entry = AppErrorLog(
        timestamp=datetime.now(UTC).replace(tzinfo=None),
        source=source,
        message=message,
        exception_type=type(exc).__name__ if exc is not None else None,
        traceback=traceback.format_exc() if exc is not None else None,
    )
    with _lock:
        _error_log.appendleft(entry)


def get_weather_api_requests() -> list[WeatherApiRequestLog]:
    with _lock:
        return list(_request_log)


def get_app_errors() -> list[AppErrorLog]:
    with _lock:
        return list(_error_log)


def clear_weather_api_requests() -> None:
    with _lock:
        _request_log.clear()


def clear_app_errors() -> None:
    with _lock:
        _error_log.clear()


def clear_all() -> None:
    clear_weather_api_requests()
    clear_app_errors()
