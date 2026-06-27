from __future__ import annotations

from app.extensions import db
from app.models import City

TEST_CITIES: list[tuple[str, str]] = [
    ("Berlin", "Germany"),
    ("Paris", "France"),
    ("London", "United Kingdom"),
    ("Tokyo", "Japan"),
    ("New York", "United States"),
    ("Vorkuta", "Russia"),
    ("Queenstown", "New Zealand"),
    ("Smolensk", "Russia"),
    ("Moscow", "Russia"),
    ("Minsk", "Belarus"),
]


def seed_test_cities() -> tuple[str, str]:
    """Create default test cities if the database has no cities."""
    if City.query.count() > 0:
        return ("info", "Cities already exist in the database.")

    for city_name, country in TEST_CITIES:
        db.session.add(City(name=city_name, country=country))
    db.session.commit()
    return ("success", f"Added {len(TEST_CITIES)} test cities.")


def clear_cities_table() -> tuple[str, str]:
    """Delete all cities (and their weather records). Returns (flash category, message)."""
    count = City.query.count()
    if count == 0:
        return ("info", "No cities to delete.")

    City.query.delete()
    db.session.commit()
    return ("success", f"Deleted {count} city/cities.")
