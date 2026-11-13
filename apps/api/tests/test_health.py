import os
from unittest.mock import Mock

os.environ.setdefault("DATABASE_URL", "postgresql+psycopg://test:test@localhost/test")
os.environ.setdefault("CORS_ORIGINS", '["http://localhost:3000"]')

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.db.session import get_session
from app.main import create_app


@pytest.fixture
def client():
    app = create_app()
    session = Mock()
    app.dependency_overrides[get_session] = lambda: session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client, session


def test_live(client):
    http, session = client
    response = http.get("/api/v1/health/live")
    assert response.json() == {"status": "alive"}
    session.execute.assert_not_called()


def test_ready(client):
    http, session = client
    response = http.get("/api/v1/health/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
    assert str(session.execute.call_args.args[0]) == "SELECT 1"


def test_unavailable(client):
    http, session = client
    session.execute.side_effect = OperationalError("secret", {}, Exception("secret"))
    response = http.get("/api/v1/health/ready")
    assert response.status_code == 503
    assert response.json()["error"]["code"] == "service_unavailable"
    assert response.json()["error"]["request_id"] == response.headers["x-request-id"]
    assert "secret" not in response.text


def test_errors_and_cors(client):
    http, _ = client
    assert http.get("/missing").json()["error"]["code"] == "http_error"
    allowed = http.get("/api/v1/health/live", headers={"Origin": "http://localhost:3000"})
    assert allowed.headers["access-control-allow-origin"] == "http://localhost:3000"
    denied = http.get("/api/v1/health/live", headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in denied.headers
