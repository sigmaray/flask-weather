from __future__ import annotations

WMO_WEATHER_LABELS: dict[int, str] = {
    0: "Clear sky",
    1: "Mainly clear",
    2: "Partly cloudy",
    3: "Overcast",
    45: "Fog",
    48: "Depositing rime fog",
    51: "Light drizzle",
    53: "Moderate drizzle",
    55: "Dense drizzle",
    56: "Light freezing drizzle",
    57: "Dense freezing drizzle",
    61: "Slight rain",
    63: "Moderate rain",
    65: "Heavy rain",
    66: "Light freezing rain",
    67: "Heavy freezing rain",
    71: "Slight snow",
    73: "Moderate snow",
    75: "Heavy snow",
    77: "Snow grains",
    80: "Slight rain showers",
    81: "Moderate rain showers",
    82: "Violent rain showers",
    85: "Slight snow showers",
    86: "Heavy snow showers",
    95: "Thunderstorm",
    96: "Thunderstorm with slight hail",
    99: "Thunderstorm with heavy hail",
}


def weather_code_label(code: int | None) -> str:
    if code is None:
        return "—"
    return WMO_WEATHER_LABELS.get(code, f"Code {code}")


WMO_WEATHER_EMOJI: dict[int, str] = {
    0: "☀️",
    1: "🌤️",
    2: "⛅",
    3: "☁️",
    45: "🌫️",
    48: "🌫️",
    51: "🌦️",
    53: "🌦️",
    55: "🌧️",
    56: "🌧️",
    57: "🌧️",
    61: "🌧️",
    63: "🌧️",
    65: "🌧️",
    66: "🌧️",
    67: "🌧️",
    71: "🌨️",
    73: "🌨️",
    75: "❄️",
    77: "❄️",
    80: "🌦️",
    81: "🌧️",
    82: "🌧️",
    85: "🌨️",
    86: "❄️",
    95: "⛈️",
    96: "⛈️",
    99: "⛈️",
}


def weather_code_emoji(code: int | None) -> str:
    if code is None:
        return "🌡️"
    return WMO_WEATHER_EMOJI.get(code, "🌡️")


def owm_weather_emoji(weather_id: int | None) -> str:
    if weather_id is None:
        return "🌡️"
    if 200 <= weather_id <= 232:
        return "⛈️"
    if 300 <= weather_id <= 321:
        return "🌦️"
    if 500 <= weather_id <= 531:
        return "🌧️"
    if 600 <= weather_id <= 622:
        return "❄️"
    if 701 <= weather_id <= 781:
        return "🌫️"
    if weather_id == 800:
        return "☀️"
    if weather_id == 801:
        return "🌤️"
    if weather_id == 802:
        return "⛅"
    if weather_id in (803, 804):
        return "☁️"
    return "🌡️"
