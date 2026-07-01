from __future__ import annotations

import json
from typing import Any

from flask import flash, redirect, request, url_for
from flask_admin import expose
from flask_admin.model.helpers import get_mdict_item_or_list
from flask_login import current_user
from markupsafe import Markup, escape
from werkzeug.wrappers.response import Response
from wtforms import PasswordField, validators

from app.admin_auth import SecureBaseView, SecureModelView
from app.extensions import db
from app.models import AppSettings, City
from app.services.geocoding import GeocodingError
from app.services.weather import ensure_city_coordinates
from app.services.weather_codes import weather_code_label


def _city_weather_context(city: City) -> dict[str, Any]:
    records = list(city.weather_records)[:100]
    chronological = list(reversed(records))
    chart_data = {
        "labels": [r.display_time.strftime("%Y-%m-%d %H:%M") for r in chronological],
        "temperatures": [r.temperature_c for r in chronological],
        "humidity": [r.humidity_percent for r in chronological],
        "wind": [r.wind_speed_ms for r in chronological],
        "snow_depth": [r.snow_depth_m for r in chronological],
        "pressure": [r.pressure_mmhg for r in chronological],
    }
    return {
        "city": city,
        "records": records,
        "chart_data_json": json.dumps(chart_data),
        "default_interval": AppSettings.get_singleton().default_check_interval_minutes,
    }


class UserAdmin(SecureModelView):
    column_list = ["id", "username", "created_at"]
    column_searchable_list = ["username"]
    column_sortable_list = ["id", "username", "created_at"]
    column_default_sort = ("id", False)
    column_exclude_list = ["password_hash"]
    form_excluded_columns = ["password_hash"]

    column_labels = {
        "id": "ID",
        "username": "Username",
        "created_at": "Created",
    }

    form_columns = ["username", "password", "password_confirm"]
    form_args = {
        "username": {"label": "Username"},
    }

    form_extra_fields = {
        "password": PasswordField("Password"),
        "password_confirm": PasswordField("Confirm password"),
    }

    can_view_details = True
    page_size = 25

    def create_form(self, obj: Any = None) -> Any:
        form = super().create_form(obj)
        form.password.validators = [
            validators.DataRequired(message="Password is required."),
        ]
        form.password_confirm.validators = [
            validators.DataRequired(),
            validators.EqualTo("password", message="Passwords do not match."),
        ]
        return form

    def edit_form(self, obj: Any = None) -> Any:
        form = super().edit_form(obj)
        form.password.validators = [validators.Optional()]
        form.password_confirm.validators = [
            validators.Optional(),
            validators.EqualTo("password", message="Passwords do not match."),
        ]
        return form

    def on_model_change(self, form: Any, model: Any, is_created: bool) -> None:
        if form.password.data:
            model.set_password(form.password.data)

    def delete_model(self, model: Any) -> Any:
        if model.id == current_user.id:
            flash("Cannot delete the current user.", "error")
            return False
        return super().delete_model(model)


class CityAdmin(SecureModelView):
    column_list = [
        "id",
        "name",
        "country",
        "geocoded_name",
        "latitude",
        "longitude",
        "check_interval_minutes",
        "last_checked_at",
        "created_at",
    ]
    column_searchable_list = ["name", "country", "geocoded_name"]
    column_filters = ["name", "country"]
    column_sortable_list = ["id", "name", "created_at", "last_checked_at"]
    column_default_sort = ("id", False)

    column_labels = {
        "id": "ID",
        "name": "Name",
        "country": "Country",
        "geocoded_name": "Geocoded name",
        "latitude": "Latitude",
        "longitude": "Longitude",
        "check_interval_minutes": "Check interval (min)",
        "last_checked_at": "Last checked",
        "created_at": "Created",
    }

    form_columns = [
        "name",
        "country",
        "latitude",
        "longitude",
        "check_interval_minutes",
    ]
    form_excluded_columns = ["geocoded_name"]
    form_args = {
        "name": {"label": "Name", "validators": [validators.Optional()]},
        "country": {"label": "Country", "validators": [validators.Optional()]},
        "latitude": {"label": "Latitude", "validators": [validators.Optional()]},
        "longitude": {"label": "Longitude", "validators": [validators.Optional()]},
        "check_interval_minutes": {"label": "Check interval (minutes)"},
    }

    can_view_details = True
    page_size = 25
    details_template = "admin/city_detail.html"

    def validate_form(self, form: Any) -> bool:
        if not super().validate_form(form):
            return False

        has_name = bool(form.name.data and str(form.name.data).strip())
        has_country = bool(form.country.data and str(form.country.data).strip())
        has_latitude = form.latitude.data not in (None, "")
        has_longitude = form.longitude.data not in (None, "")

        has_name_location = has_name and has_country
        has_coordinate_location = has_latitude and has_longitude

        if has_name_location and has_coordinate_location:
            flash(
                "Specify either name and country, or latitude and longitude.",
                "error",
            )
            return False

        if not has_name_location and not has_coordinate_location:
            flash(
                "Specify either name and country, or latitude and longitude.",
                "error",
            )
            return False

        if has_name != has_country:
            flash("Name and country must both be provided.", "error")
            return False

        if has_latitude != has_longitude:
            flash("Latitude and longitude must both be provided.", "error")
            return False

        return True

    def on_model_change(self, form: Any, model: City, is_created: bool) -> None:
        from app.services.geocoding import GeocodingError, reverse_geocode

        has_name = bool(form.name.data and str(form.name.data).strip())
        has_country = bool(form.country.data and str(form.country.data).strip())
        has_latitude = form.latitude.data not in (None, "")
        has_longitude = form.longitude.data not in (None, "")

        if has_name and has_country:
            model.name = str(form.name.data).strip()
            model.country = str(form.country.data).strip()
            model.latitude = None
            model.longitude = None
            model.geocoded_name = None
            return

        if has_latitude and has_longitude:
            model.latitude = float(form.latitude.data)
            model.longitude = float(form.longitude.data)
            model.name = None
            model.country = None
            try:
                model.geocoded_name = reverse_geocode(model.latitude, model.longitude)
            except GeocodingError as exc:
                raise validators.ValidationError(f"Failed to geocode coordinates: {exc}") from exc

    @expose("/details/", methods=("GET",))
    def details_view(self) -> Any:
        return_url = self.get_url(".index_view")

        if not self.can_view_details:
            return redirect(return_url)

        city_id = get_mdict_item_or_list(request.args, "id")
        if city_id is None:
            return redirect(return_url)

        city = self.get_one(city_id)
        if city is None:
            flash("Record does not exist.", "error")
            return redirect(return_url)

        return self.render(
            self.details_template,
            model=city,
            return_url=return_url,
            **_city_weather_context(city),
        )

    @expose("/fetch-weather/", methods=["POST"])
    def fetch_weather_now(self) -> Response:
        from app.services.weather import WeatherFetchError, fetch_weather_for_city

        return_url = self.get_url(".index_view")
        city_id = get_mdict_item_or_list(request.args, "id")
        if city_id is None:
            flash("City not found.", "error")
            return redirect(return_url)

        city = db.session.get(City, int(city_id))
        if city is None:
            flash("City not found.", "error")
            return redirect(return_url)

        try:
            fetch_weather_for_city(city)
            flash("Weather data fetched.", "success")
        except WeatherFetchError as exc:
            flash(f"Failed to fetch weather: {exc}", "danger")

        return redirect(self.get_url(".details_view", id=city_id))


def _weather_record_city_link(_view: Any, _context: Any, model: Any, _name: str) -> Markup:
    if model.city is None:
        return Markup(f"<span>#{model.city_id}</span>")
    city_url = url_for("admin_cities.details_view", id=model.city.id)
    return Markup(f'<a href="{city_url}">{escape(model.city.display_name)}</a>')


class WeatherRecordAdmin(SecureModelView):
    column_list = [
        "id",
        "city_id",
        "recorded_at",
        "observed_at_local",
        "temperature_c",
        "dew_point_c",
        "humidity_percent",
        "pressure_mmhg",
        "wind_speed_ms",
        "apparent_temperature_c",
        "weather_code",
        "uv_index",
        "precipitation_mm",
        "snow_depth_m",
    ]
    column_filters = ["city_id", "recorded_at"]
    column_sortable_list = ["id", "recorded_at", "temperature_c"]
    column_default_sort = ("recorded_at", True)

    column_formatters = {
        "city_id": _weather_record_city_link,
    }
    column_formatters_detail = {
        "city_id": _weather_record_city_link,
    }

    column_labels = {
        "id": "ID",
        "city_id": "City",
        "recorded_at": "Recorded at (UTC)",
        "observed_at_local": "Observed at (local)",
        "temperature_c": "Temperature (°C)",
        "dew_point_c": "Dew point (°C)",
        "humidity_percent": "Humidity (%)",
        "pressure_mmhg": "Pressure (mmHg)",
        "wind_speed_ms": "Wind speed (m/s)",
        "apparent_temperature_c": "Feels like (°C)",
        "weather_code": "Weather code",
        "uv_index": "UV index (daily max)",
        "precipitation_mm": "Precipitation (mm)",
        "snow_depth_m": "Snow depth (m)",
    }

    can_create = False
    can_edit = False
    can_view_details = True
    page_size = 25


class AppSettingsAdmin(SecureModelView):
    column_list = ["id", "default_check_interval_minutes", "updated_at"]
    column_sortable_list = ["id", "default_check_interval_minutes", "updated_at"]
    column_default_sort = ("id", False)

    column_labels = {
        "id": "ID",
        "default_check_interval_minutes": "Default check interval (min)",
        "updated_at": "Updated",
    }

    form_columns = ["default_check_interval_minutes"]
    form_args = {
        "default_check_interval_minutes": {"label": "Default check interval (minutes)"},
    }

    can_create = False
    can_delete = False
    can_view_details = True
    page_size = 25

    def get_query(self) -> Any:
        AppSettings.get_singleton()
        return super().get_query()


class ToolsAdmin(SecureBaseView):
    @expose("/")
    def index(self) -> Any:
        from app.models import City, User, WeatherRecord

        return self.render(
            "admin/tools.html",
            cities_count=City.query.count(),
            weather_records_count=WeatherRecord.query.count(),
            users_count=User.query.count(),
        )

    @expose("/fetch-weather/", methods=["POST"])
    def fetch_weather(self) -> Response:
        from app.services.weather import fetch_due_cities

        records = fetch_due_cities()
        flash(f"Fetched weather for {len(records)} cities.", "success")
        return redirect(url_for(".index"))

    @expose("/seed-cities/", methods=["POST"])
    def seed_cities(self) -> Response:
        from app.services.city_service import seed_test_cities

        category, message = seed_test_cities()
        flash(message, category)
        return redirect(url_for(".index"))

    @expose("/clear-cities/", methods=["POST"])
    def clear_cities(self) -> Response:
        from app.services.city_service import clear_cities_table

        category, message = clear_cities_table()
        flash(message, category)
        return redirect(url_for(".index"))

    @expose("/clear-weather/", methods=["POST"])
    def clear_weather(self) -> Response:
        from app.services.weather import clear_weather_records

        category, message = clear_weather_records()
        flash(message, category)
        return redirect(url_for(".index"))

    @expose("/seed-users/", methods=["POST"])
    def seed_users(self) -> Response:
        from app.services.user_service import seed_admin_user

        category, message = seed_admin_user()
        flash(message, category)
        return redirect(url_for(".index"))

    @expose("/clear-users/", methods=["POST"])
    def clear_users(self) -> Response:
        from app.services.user_service import clear_users_table

        category, message = clear_users_table()
        flash(message, category)
        return redirect(url_for(".index"))


class WeatherMapAdmin(SecureBaseView):
    @expose("/")
    def index(self) -> Any:
        cities_with_weather = (
            City.query.join(City.weather_records).distinct().order_by(City.id.asc()).all()
        )

        map_points: list[dict[str, Any]] = []
        records_without_coordinates = 0
        for city in cities_with_weather:
            if not city.weather_records:
                continue

            latest = city.weather_records[0]
            try:
                latitude, longitude = ensure_city_coordinates(city)
            except GeocodingError:
                records_without_coordinates += 1
                continue

            map_points.append(
                {
                    "city_id": city.id,
                    "city_name": city.display_name,
                    "latitude": latitude,
                    "longitude": longitude,
                    "temperature_c": latest.temperature_c,
                    "weather_label": weather_code_label(latest.weather_code),
                    "recorded_at": latest.display_time.strftime("%Y-%m-%d %H:%M"),
                    "details_url": url_for("admin_cities.details_view", id=city.id),
                }
            )

        db.session.commit()

        return self.render(
            "admin/weather_map.html",
            map_points=map_points,
            records_with_coordinates=len(map_points),
            records_without_coordinates=records_without_coordinates,
            total_records=len(cities_with_weather),
        )


class SchedulerAdmin(SecureBaseView):
    @expose("/")
    def index(self) -> Any:
        from app.scheduler import get_running_job_ids, get_scheduler

        scheduler = get_scheduler()
        jobs = scheduler.get_jobs() if scheduler else []

        return self.render(
            "admin/scheduler.html",
            jobs=jobs,
            running_job_ids=get_running_job_ids(),
            scheduler_enabled=scheduler is not None,
        )

    @expose("/pause/<job_id>", methods=["POST"])
    def pause_job(self, job_id: str) -> Response:
        from app.scheduler import get_scheduler

        scheduler = get_scheduler()
        if scheduler:
            try:
                scheduler.pause_job(job_id)
                flash(f"Job {job_id} paused successfully.", "success")
            except Exception as e:
                from app.memory_log import log_app_error

                log_app_error("scheduler.pause", f"Failed to pause job {job_id}: {e}", e)
                flash(f"Failed to pause job {job_id}: {e}", "danger")
        else:
            flash("Scheduler is not enabled.", "danger")

        return redirect(url_for(".index"))

    @expose("/resume/<job_id>", methods=["POST"])
    def resume_job(self, job_id: str) -> Response:
        from app.scheduler import get_scheduler

        scheduler = get_scheduler()
        if scheduler:
            try:
                scheduler.resume_job(job_id)
                flash(f"Job {job_id} resumed successfully.", "success")
            except Exception as e:
                from app.memory_log import log_app_error

                log_app_error("scheduler.resume", f"Failed to resume job {job_id}: {e}", e)
                flash(f"Failed to resume job {job_id}: {e}", "danger")
        else:
            flash("Scheduler is not enabled.", "danger")

        return redirect(url_for(".index"))

    @expose("/remove/<job_id>", methods=["POST"])
    def remove_job(self, job_id: str) -> Response:
        from app.scheduler import get_scheduler

        scheduler = get_scheduler()
        if scheduler:
            try:
                scheduler.remove_job(job_id)
                flash(f"Job {job_id} removed successfully.", "success")
            except Exception as e:
                from app.memory_log import log_app_error

                log_app_error("scheduler.remove", f"Failed to remove job {job_id}: {e}", e)
                flash(f"Failed to remove job {job_id}: {e}", "danger")
        else:
            flash("Scheduler is not enabled.", "danger")

        return redirect(url_for(".index"))


class WeatherApiLogAdmin(SecureBaseView):
    @expose("/")
    def index(self) -> Any:
        from app.memory_log import get_weather_api_requests

        return self.render(
            "admin/weather_api_log.html",
            requests=get_weather_api_requests(),
        )


class AppErrorLogAdmin(SecureBaseView):
    @expose("/")
    def index(self) -> Any:
        from app.memory_log import get_app_errors

        return self.render(
            "admin/app_error_log.html",
            errors=get_app_errors(),
        )
