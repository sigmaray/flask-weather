import pytest
from flask import Flask
from flask.testing import FlaskClient

from app import create_app
from app.extensions import db
from app.models import AppSettings, User
from app.scheduler import get_scheduler


@pytest.fixture
def scheduler_app() -> Flask:
    application = create_app(
        {
            "TESTING": True,
            "SQLALCHEMY_DATABASE_URI": "sqlite:///:memory:",
            "WTF_CSRF_ENABLED": False,
            "SCHEDULER_ENABLED": True,
            "SECRET_KEY": "test-secret",
        }
    )
    with application.app_context():
        db.create_all()
        AppSettings.get_singleton()
        yield application
        db.session.remove()
        db.drop_all()


@pytest.fixture
def scheduler_client(scheduler_app: Flask) -> FlaskClient:
    return scheduler_app.test_client()


@pytest.fixture
def auth_scheduler_client(scheduler_client: FlaskClient, scheduler_app: Flask) -> FlaskClient:
    with scheduler_app.app_context():
        u = User(username="admin")
        u.set_password("admin")
        db.session.add(u)
        db.session.commit()
    scheduler_client.post(
        "/auth/login",
        data={"username": "admin", "password": "admin"},
        follow_redirects=True,
    )
    return scheduler_client


def test_scheduler_index(auth_scheduler_client: FlaskClient, scheduler_app: Flask):
    response = auth_scheduler_client.get("/admin/scheduler/")
    assert response.status_code == 200
    assert b"Background Tasks" in response.data
    assert b"fetch_weather" in response.data
    assert b"Running" in response.data or b"Paused" in response.data


def test_scheduler_pause_resume(auth_scheduler_client: FlaskClient, scheduler_app: Flask):
    # Ensure job is there
    with scheduler_app.app_context():
        scheduler = get_scheduler()
        assert scheduler is not None
        job = scheduler.get_job("fetch_weather")
        assert job is not None
        assert job.next_run_time is not None

    # Pause
    response = auth_scheduler_client.post(
        "/admin/scheduler/pause/fetch_weather", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"paused successfully" in response.data

    with scheduler_app.app_context():
        job = get_scheduler().get_job("fetch_weather")
        assert job.next_run_time is None

    # Resume
    response = auth_scheduler_client.post(
        "/admin/scheduler/resume/fetch_weather", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"resumed successfully" in response.data

    with scheduler_app.app_context():
        job = get_scheduler().get_job("fetch_weather")
        assert job.next_run_time is not None


def test_scheduler_remove(auth_scheduler_client: FlaskClient, scheduler_app: Flask):
    # Add a dummy job to remove
    with scheduler_app.app_context():
        scheduler = get_scheduler()
        scheduler.add_job(lambda: None, "interval", minutes=10, id="dummy_job")

    response = auth_scheduler_client.post(
        "/admin/scheduler/remove/dummy_job", follow_redirects=True
    )
    assert response.status_code == 200
    assert b"removed successfully" in response.data

    with scheduler_app.app_context():
        job = get_scheduler().get_job("dummy_job")
        assert job is None
