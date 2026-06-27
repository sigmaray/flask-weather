from __future__ import annotations

from datetime import datetime

import click
from flask import Flask

from app.extensions import db
from app.models import City, User
from app.services.city_service import seed_test_cities
from app.services.user_service import clear_users_table, seed_admin_user


def _format_datetime(value: datetime | None) -> str:
    if value is None:
        return "-"
    return value.strftime("%Y-%m-%d %H:%M:%S")


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, cell in enumerate(row):
            widths[index] = max(widths[index], len(cell))

    header_line = "  ".join(header.ljust(widths[index]) for index, header in enumerate(headers))
    separator = "  ".join("-" * width for width in widths)
    body = ["  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row)) for row in rows]
    return "\n".join([header_line, separator, *body])


def register_cli(app: Flask) -> None:
    @app.cli.command("users-create")
    def users_create() -> None:
        """Create a user (login only via CLI, not UI registration)."""
        username = click.prompt("Login", type=str).strip()
        if not username:
            click.echo("Login cannot be empty.")
            raise SystemExit(1)

        if User.query.filter_by(username=username).first():
            click.echo(f"User {username!r} already exists.")
            raise SystemExit(1)

        password = click.prompt("Password", hide_input=True)
        confirm = click.prompt("Confirm password", hide_input=True)
        if password != confirm:
            click.echo("Passwords do not match.")
            raise SystemExit(1)
        if not password:
            click.echo("Password cannot be empty.")
            raise SystemExit(1)

        user = User(username=username)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        click.echo(f"User {username!r} created.")

    @app.cli.command("users-clear")
    @click.option("--yes", "-y", is_flag=True, help="Skip confirmation.")
    def users_clear(yes: bool) -> None:
        """Delete all users."""
        count = User.query.count()
        if count == 0:
            click.echo("No users to delete.")
            return

        if not yes and not click.confirm(f"Delete all {count} user(s)?"):
            click.echo("Aborted.")
            raise SystemExit(1)

        _, message = clear_users_table()
        click.echo(message)

    @app.cli.command("users-show")
    def users_show() -> None:
        """List all users."""
        users = User.query.order_by(User.id).all()
        if not users:
            click.echo("No users.")
            return

        rows = [
            [str(user.id), user.username, _format_datetime(user.created_at)] for user in users
        ]
        click.echo(_format_table(["ID", "Username", "Created"], rows))

    @app.cli.command("cities-seed")
    def cities_seed() -> None:
        """Create test cities for local development."""
        _, message = seed_test_cities()
        click.echo(message)

    @app.cli.command("cities-show")
    def cities_show() -> None:
        """List all cities."""
        cities = City.query.order_by(City.id).all()
        if not cities:
            click.echo("No cities.")
            return

        rows = []
        for city in cities:
            interval = (
                str(city.check_interval_minutes)
                if city.check_interval_minutes is not None
                else f"default ({city.effective_interval_minutes()})"
            )
            rows.append(
                [
                    str(city.id),
                    city.name or "-",
                    city.country or "-",
                    city.geocoded_name or "-",
                    f"{city.latitude:.4f}" if city.latitude is not None else "-",
                    f"{city.longitude:.4f}" if city.longitude is not None else "-",
                    interval,
                    _format_datetime(city.last_checked_at),
                    _format_datetime(city.created_at),
                ]
            )
        click.echo(
            _format_table(
                [
                    "ID",
                    "Name",
                    "Country",
                    "Geocoded",
                    "Lat",
                    "Lon",
                    "Interval",
                    "Last checked",
                    "Created",
                ],
                rows,
            )
        )

    @app.cli.command("users-seed")
    def users_seed() -> None:
        """Create a test user for local development (admin / admin)."""
        _, message = seed_admin_user()
        click.echo(message)

    @app.cli.command("fetch-weather")
    def fetch_weather() -> None:
        """Fetch weather for all cities that are due."""
        from app.services.weather import fetch_due_cities

        records = fetch_due_cities()
        click.echo(f"Fetched weather for {len(records)} cities.")
