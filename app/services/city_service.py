from __future__ import annotations

from app.extensions import db
from app.models import City

TEST_CITIES: list[tuple[str, str]] = [
    ("Berlin", "Germany"),
    ("Paris", "France"),
    ("London", "United Kingdom"),
    ("Tokyo", "Japan"),
    ("New York", "United States"),
]


def seed_test_cities() -> tuple[str, str]:
    """Create default test cities if the database has no cities."""
    if City.query.count() > 0:
        return ("info", "Cities already exist in the database.")

    for city_name, country in TEST_CITIES:
        db.session.add(City(name=city_name, country=country))
    db.session.commit()
    return ("success", f"Added {len(TEST_CITIES)} test cities.")
