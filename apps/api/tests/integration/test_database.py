import os

import pytest
from fastapi.testclient import TestClient


@pytest.mark.skipif(os.getenv("RUN_DB_TESTS") != "1", reason="Requires a live PostgreSQL database")
def test_real_readiness():
    from app.main import create_app

    with TestClient(create_app()) as client:
        response = client.get("/api/v1/health/ready")
        assert response.status_code == 200
        assert response.json() == {"status": "ready"}
