from __future__ import annotations

from datetime import datetime

from flask_login import UserMixin
from werkzeug.security import check_password_hash, generate_password_hash

from app.extensions import db


class User(UserMixin, db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username!r}>"


class AppSettings(db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "app_settings"

    id = db.Column(db.Integer, primary_key=True)
    default_check_interval_minutes = db.Column(db.Integer, nullable=False, default=60)
    updated_at = db.Column(
        db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False
    )

    @classmethod
    def get_singleton(cls) -> AppSettings:
        settings = db.session.get(cls, 1)
        if settings is None:
            settings = cls(id=1, default_check_interval_minutes=60)
            db.session.add(settings)
            db.session.commit()
        return settings


class City(db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "cities"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=True)
    country = db.Column(db.String(120), nullable=True)
    latitude = db.Column(db.Float, nullable=True)
    longitude = db.Column(db.Float, nullable=True)
    geocoded_name = db.Column(db.String(200), nullable=True)
    check_interval_minutes = db.Column(db.Integer, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow, nullable=False)
    last_checked_at = db.Column(db.DateTime, nullable=True)

    weather_records = db.relationship(
        "WeatherRecord",
        back_populates="city",
        cascade="all, delete-orphan",
        order_by="desc(WeatherRecord.recorded_at)",
    )

    def has_name_location(self) -> bool:
        return bool(self.name and self.country)

    def has_coordinate_location(self) -> bool:
        return self.latitude is not None and self.longitude is not None

    @property
    def display_name(self) -> str:
        if self.name and self.country:
            return f"{self.name}, {self.country}"
        if self.geocoded_name:
            return str(self.geocoded_name)
        if self.has_coordinate_location():
            return f"{self.latitude:.4f}, {self.longitude:.4f}"
        if self.name:
            return str(self.name)
        return "Unknown"

    def effective_interval_minutes(self) -> int:
        if self.check_interval_minutes is not None:
            return int(self.check_interval_minutes)
        return int(AppSettings.get_singleton().default_check_interval_minutes)

    def __repr__(self) -> str:
        return f"<City {self.display_name!r}>"


class WeatherRecord(db.Model):  # type: ignore[name-defined,misc]
    __tablename__ = "weather_records"

    id = db.Column(db.Integer, primary_key=True)
    city_id = db.Column(db.Integer, db.ForeignKey("cities.id"), nullable=False, index=True)
    recorded_at = db.Column(db.DateTime, nullable=False, index=True)
    temperature_c = db.Column(db.Float, nullable=False)
    humidity_percent = db.Column(db.Float, nullable=True)
    wind_speed_ms = db.Column(db.Float, nullable=True)
    weather_code = db.Column(db.Integer, nullable=True)
    precipitation_mm = db.Column(db.Float, nullable=True)
    snow_depth_m = db.Column(db.Float, nullable=True)

    city = db.relationship("City", back_populates="weather_records")

    def __repr__(self) -> str:
        return f"<WeatherRecord city_id={self.city_id} at {self.recorded_at}>"
