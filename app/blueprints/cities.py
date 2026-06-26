from __future__ import annotations

import json

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask.typing import ResponseReturnValue
from flask_login import login_required

from app.extensions import db
from app.models import AppSettings, City
from app.services.geocoding import GeocodingError, geocode_city
from app.services.weather import WeatherFetchError, fetch_weather_for_city

cities_bp = Blueprint("cities", __name__, url_prefix="/cities")


@cities_bp.route("/")
@login_required
def list_cities() -> ResponseReturnValue:
    cities = City.query.order_by(City.name).all()
    default_interval = AppSettings.get_singleton().default_check_interval_minutes
    return render_template(
        "cities/list.html",
        cities=cities,
        default_interval=default_interval,
    )


def _parse_check_interval(interval_raw: str, errors: list[str]) -> int | None:
    if not interval_raw:
        return None
    try:
        interval = int(interval_raw)
    except ValueError:
        errors.append("Check interval must be an integer.")
        return None
    if interval < 1:
        errors.append("Check interval must be at least 1 minute.")
        return None
    return interval


def _form_values() -> dict[str, str]:
    return {
        "name": request.form.get("name", "").strip(),
        "latitude": request.form.get("latitude", "").strip(),
        "longitude": request.form.get("longitude", "").strip(),
        "country": request.form.get("country", "").strip(),
        "city": request.form.get("city", "").strip(),
        "check_interval_minutes": request.form.get("check_interval_minutes", "").strip(),
    }


@cities_bp.route("/add", methods=["GET", "POST"])
@login_required
def add_city() -> ResponseReturnValue:
    default_interval = AppSettings.get_singleton().default_check_interval_minutes
    location_mode = request.values.get("location_mode", "country_city")
    form = _form_values() if request.method == "POST" else {
        "name": "",
        "latitude": "",
        "longitude": "",
        "country": "",
        "city": "",
        "check_interval_minutes": "",
    }

    if request.method == "POST":
        errors: list[str] = []
        interval = _parse_check_interval(form["check_interval_minutes"], errors)
        name = form["name"]
        lat: float | None = None
        lon: float | None = None

        if location_mode == "country_city":
            if not form["country"]:
                errors.append("Country is required.")
            if not form["city"]:
                errors.append("City is required.")
            if not errors:
                try:
                    name, lat, lon = geocode_city(form["city"], form["country"])
                except GeocodingError as exc:
                    errors.append(str(exc))
        else:
            if not name:
                errors.append("Name is required.")
            try:
                lat = float(form["latitude"])
                lon = float(form["longitude"])
            except ValueError:
                errors.append("Latitude and longitude must be valid numbers.")

        if errors:
            for error in errors:
                flash(error, "danger")
        else:
            assert lat is not None and lon is not None
            city = City(
                name=name,
                latitude=lat,
                longitude=lon,
                check_interval_minutes=interval,
            )
            db.session.add(city)
            db.session.commit()
            flash(f"City {name!r} added.", "success")
            return redirect(url_for("cities.list_cities"))

    return render_template(
        "cities/add.html",
        default_interval=default_interval,
        location_mode=location_mode,
        form=form,
    )


@cities_bp.route("/<int:city_id>")
@login_required
def city_detail(city_id: int) -> ResponseReturnValue:
    city = db.get_or_404(City, city_id)
    records = list(city.weather_records)[:100]
    chart_data = {
        "labels": [r.recorded_at.strftime("%Y-%m-%d %H:%M") for r in reversed(records)],
        "temperatures": [r.temperature_c for r in reversed(records)],
        "humidity": [r.humidity_percent for r in reversed(records)],
        "wind": [r.wind_speed_ms for r in reversed(records)],
    }
    return render_template(
        "cities/detail.html",
        city=city,
        records=records,
        chart_data_json=json.dumps(chart_data),
        default_interval=AppSettings.get_singleton().default_check_interval_minutes,
    )


@cities_bp.route("/<int:city_id>/fetch", methods=["POST"])
@login_required
def fetch_now(city_id: int) -> ResponseReturnValue:
    city = db.get_or_404(City, city_id)
    try:
        fetch_weather_for_city(city)
        flash("Weather data fetched.", "success")
    except WeatherFetchError as exc:
        flash(f"Failed to fetch weather: {exc}", "danger")
    return redirect(url_for("cities.city_detail", city_id=city_id))
