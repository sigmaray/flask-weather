import os
import shutil

from app.extensions import db
from app.factory import create_app
from app.models import City
from app.services.city_service import TEST_CITIES
from app.services.weather import fetch_weather_for_city
from app.vcr_setup import vcr_context


def main():
    if os.path.exists("e2e/e2e_cassettes"):
        shutil.rmtree("e2e/e2e_cassettes")

    app = create_app(
        {
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "TESTING": True,
            "INTERNAL_SCHEDULER_ENABLED": False,
        }
    )

    with app.app_context():
        db.create_all()

        cities = []
        for name, country in TEST_CITIES:
            city = City(name=name, country=country)
            db.session.add(city)
            cities.append(city)
        db.session.commit()

        os.environ["USE_VCR"] = "true"
        vcr_context.start()

        print("Fetching weather for all cities to record cassette...")
        for city in cities:
            print(f"Fetching {city.name}...")
            try:
                fetch_weather_for_city(city)
            except Exception as e:
                print(f"Warning: failed to fetch for {city.name}: {e}")

        vcr_context.stop()
        print("Cassette recorded successfully.")


if __name__ == "__main__":
    main()
