"""Drop dew point from OpenWeatherMap records

Revision ID: 011_drop_owm_dew_point
Revises: 010_drop_owm_uv_index
Create Date: 2026-07-02

"""

import sqlalchemy as sa
from alembic import op

revision = "011_drop_owm_dew_point"
down_revision = "010_drop_owm_uv_index"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.drop_column("owm_weather_records", "dew_point_c")


def downgrade() -> None:
    op.add_column(
        "owm_weather_records",
        sa.Column("dew_point_c", sa.Float(), nullable=True),
    )
