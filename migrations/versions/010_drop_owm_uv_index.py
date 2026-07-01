"""Drop UV index from OpenWeatherMap records

Revision ID: 010_drop_owm_uv_index
Revises: 009_extended_weather_fields
Create Date: 2026-07-02

"""

import sqlalchemy as sa
from alembic import op

revision = "010_drop_owm_uv_index"
down_revision = "009_extended_weather_fields"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("owm_weather_records", "uv_index")


def downgrade() -> None:
    op.add_column(
        "owm_weather_records",
        sa.Column("uv_index", sa.Float(), nullable=True),
    )
