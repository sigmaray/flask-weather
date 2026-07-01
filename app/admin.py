from __future__ import annotations

from flask import Flask
from flask_admin import Admin

from app.admin_auth import SecureAdminIndexView
from app.admin_views import (
    AppErrorLogAdmin,
    AppSettingsAdmin,
    CityAdmin,
    OmWeatherRecordAdmin,
    OwmWeatherRecordAdmin,
    SchedulerAdmin,
    ToolsAdmin,
    UserAdmin,
    WeatherApiLogAdmin,
    WeatherMapAdmin,
)
from app.extensions import db
from app.models import AppSettings, City, OmWeatherRecord, OwmWeatherRecord, User


def init_admin(app: Flask) -> None:
    admin = Admin(
        app,
        name="Weather Admin",
        url="/admin",
        index_view=SecureAdminIndexView(),
    )
    admin.add_view(ToolsAdmin(name="Tools", endpoint="tools"))
    admin.add_view(UserAdmin(User, db.session, name="Users", endpoint="users"))
    admin.add_view(CityAdmin(City, db.session, name="Cities", endpoint="admin_cities"))
    admin.add_view(
        OmWeatherRecordAdmin(
            OmWeatherRecord,
            db.session,
            name="Weather (Open-Meteo)",
            endpoint="weather_records",
        )
    )
    admin.add_view(
        OwmWeatherRecordAdmin(
            OwmWeatherRecord,
            db.session,
            name="Weather (OpenWeatherMap)",
            endpoint="owm_weather_records",
        )
    )
    admin.add_view(
        AppSettingsAdmin(
            AppSettings,
            db.session,
            name="Settings",
            endpoint="app_settings",
        )
    )
    admin.add_view(SchedulerAdmin(name="Background Tasks", endpoint="scheduler"))
    admin.add_view(WeatherMapAdmin(name="Map", endpoint="weather_map"))
    admin.add_view(WeatherApiLogAdmin(name="API Requests", endpoint="weather_api_log"))
    admin.add_view(AppErrorLogAdmin(name="Error Log", endpoint="app_error_log"))
