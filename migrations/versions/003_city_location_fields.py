"""Add country and geocoded_name to cities

Revision ID: 003_city_location_fields
Revises: 002_add_snow_depth
Create Date: 2026-06-26

"""

import sqlalchemy as sa
from alembic import op

revision = "003_city_location_fields"
down_revision = "002_add_snow_depth"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("cities", sa.Column("country", sa.String(length=120), nullable=True))
    op.add_column(
        "cities", sa.Column("geocoded_name", sa.String(length=200), nullable=True)
    )
    op.alter_column("cities", "name", existing_type=sa.String(length=120), nullable=True)
    op.alter_column("cities", "latitude", existing_type=sa.Float(), nullable=True)
    op.alter_column("cities", "longitude", existing_type=sa.Float(), nullable=True)

    conn = op.get_bind()
    cities = conn.execute(
        sa.text("SELECT id, name, latitude, longitude FROM cities")
    ).fetchall()
    for city_id, name, latitude, longitude in cities:
        if name and ", " in name:
            city_name, country = name.split(", ", 1)
            conn.execute(
                sa.text(
                    "UPDATE cities SET name = :name, country = :country, "
                    "latitude = NULL, longitude = NULL WHERE id = :id"
                ),
                {"name": city_name, "country": country, "id": city_id},
            )
        elif latitude is not None and longitude is not None:
            conn.execute(
                sa.text(
                    "UPDATE cities SET geocoded_name = :geocoded_name, "
                    "name = NULL, country = NULL WHERE id = :id"
                ),
                {"geocoded_name": name, "id": city_id},
            )


def downgrade() -> None:
    conn = op.get_bind()
    cities = conn.execute(
        sa.text(
            "SELECT id, name, country, geocoded_name, latitude, longitude FROM cities"
        )
    ).fetchall()
    for city_id, name, country, geocoded_name, latitude, longitude in cities:
        if name and country:
            display_name = f"{name}, {country}"
            conn.execute(
                sa.text(
                    "UPDATE cities SET name = :name, latitude = 0, longitude = 0 "
                    "WHERE id = :id"
                ),
                {"name": display_name, "id": city_id},
            )
        elif geocoded_name:
            conn.execute(
                sa.text(
                    "UPDATE cities SET name = :name, latitude = :latitude, "
                    "longitude = :longitude WHERE id = :id"
                ),
                {
                    "name": geocoded_name,
                    "latitude": latitude if latitude is not None else 0,
                    "longitude": longitude if longitude is not None else 0,
                    "id": city_id,
                },
            )
        elif latitude is not None and longitude is not None:
            conn.execute(
                sa.text(
                    "UPDATE cities SET name = :name WHERE id = :id"
                ),
                {"name": f"{latitude:.4f}, {longitude:.4f}", "id": city_id},
            )

    op.alter_column("cities", "longitude", existing_type=sa.Float(), nullable=False)
    op.alter_column("cities", "latitude", existing_type=sa.Float(), nullable=False)
    op.alter_column("cities", "name", existing_type=sa.String(length=120), nullable=False)
    op.drop_column("cities", "geocoded_name")
    op.drop_column("cities", "country")
