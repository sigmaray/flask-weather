"""Add snow depth to weather records

Revision ID: 002_add_snow_depth
Revises: 001_initial
Create Date: 2026-06-26

"""

import sqlalchemy as sa
from alembic import op

revision = "002_add_snow_depth"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("weather_records", sa.Column("snow_depth_m", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("weather_records", "snow_depth_m")
