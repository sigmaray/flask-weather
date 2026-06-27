from __future__ import annotations

from app.services.weather import HPA_TO_MMHG, _pressure_hpa_to_mmhg
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
