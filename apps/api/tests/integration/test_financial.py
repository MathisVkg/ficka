import os
from datetime import UTC, date, datetime, timedelta

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.models import Entry

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Requires migrated PostgreSQL"
)


@pytest.fixture
def http():
    from app.main import create_app

    engine = create_engine(get_settings().connection_url)
    with engine.connect() as connection:
        transaction = connection.begin()
        with Session(bind=connection, join_transaction_mode="create_savepoint") as session:
            app = create_app()
            app.dependency_overrides[get_session] = lambda: session
            with TestClient(app) as client:
                yield client, session
        transaction.rollback()
    engine.dispose()


def create(client, path="income", **overrides):
    response = client.post(
        "/api/v1/" + path,
        json={
            "title": "Consulting",
            "amount": "121.00",
            "vat_rate": "21",
            "entry_date": "2026-01-10",
            **overrides,
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


@pytest.mark.parametrize("path", ["income", "expenses"])
def test_crud_status_dates_and_soft_delete(http, path):
    client, session = http
    entry = create(client, path)
    assert entry["amount"] == "121.00"
    assert entry["vat_amount"] == "21.00"
    assert entry["amount_excluding_vat"] == "100.00"
    assert entry["status"] == "draft"
    assert entry["payment_date"] == entry["entry_date"]
    assert datetime.fromisoformat(entry["created_at"].replace("Z", "+00:00")).tzinfo is not None
    url = f"/api/v1/{path}/{entry['id']}"
    for status in ["pending", "paid", "draft"]:
        result = client.patch(url, json={"status": status, "payment_date": "2026-01-15"})
        assert result.status_code == 200, result.text
        assert result.json()["status"] == status
    result = client.patch(url, json={"entry_date": "2026-01-11", "title": "Updated"})
    assert result.json()["payment_date"] == "2026-01-15"
    assert result.json()["title"] == "Updated"
    assert client.get(url).status_code == 200
    assert client.delete(url).status_code == 204
    assert client.get(url).status_code == 404
    assert client.patch(url, json={"title": "Resurrect"}).status_code == 404
    assert client.get("/api/v1/" + path).json()["total"] == 0
    stored = session.scalar(select(Entry).where(Entry.title == "Updated"))
    assert stored is not None and stored.deleted_at is not None
    assert stored.deleted_at.astimezone(UTC).date() == date.today()


def test_endpoint_separation_and_invalid_input(http):
    client, _ = http
    entry = create(client)
    other = "/api/v1/expenses/" + entry["id"]
    assert client.get(other).status_code == 404
    assert client.patch(other, json={"title": "Wrong type"}).status_code == 404
    assert client.delete(other).status_code == 404
    for invalid in [
        {"amount": 1.1},
        {"amount": "-1"},
        {"status": "due"},
        {"entry_date": "not-a-date"},
        {"currency": "ZZZ"},
    ]:
        response = client.post(
            "/api/v1/income", json={"title": "Invalid", "amount": "10", **invalid}
        )
        assert response.status_code == 422
        assert response.json()["error"]["code"] == "validation_error"
    future = (date.today() + timedelta(days=2)).isoformat()
    assert (
        client.patch(
            "/api/v1/income/" + entry["id"],
            json={
                "status": "paid",
                "payment_date": future,
            },
        ).status_code
        == 422
    )


def test_vat_override_and_recalculation(http):
    client, _ = http
    entry = create(client, vat_amount="15.50")
    url = "/api/v1/income/" + entry["id"]
    assert entry["vat_overridden"] is True
    assert client.patch(url, json={"amount": "242"}).json()["vat_amount"] == "15.50"
    assert client.patch(url, json={"vat_amount": None}).json()["vat_amount"] == "42.00"
    assert client.patch(url, json={"amount": "121"}).json()["vat_amount"] == "21.00"
    assert client.patch(url, json={"vat_amount": "122"}).status_code == 422
    assert client.patch(url, json={"amount": None}).status_code == 422
    assert client.get(url).json()["amount"] == "121.00"


def test_category_lifecycle_and_cross_type_validation(http):
    client, _ = http
    category = client.post(
        "/api/v1/categories", json={"name": "  Consulting   work ", "type": "income"}
    )
    assert category.status_code == 201
    cat = category.json()
    assert cat["name"] == "Consulting work"
    assert (
        client.post(
            "/api/v1/categories", json={"name": "CONSULTING work", "type": "income"}
        ).status_code
        == 409
    )
    assert (
        client.post(
            "/api/v1/categories", json={"name": "Consulting work", "type": "expense"}
        ).status_code
        == 201
    )
    entry = create(client, category_id=cat["id"])
    assert (
        client.post(
            "/api/v1/expenses", json={"title": "Wrong", "amount": "1", "category_id": cat["id"]}
        ).status_code
        == 422
    )
    cat_url = "/api/v1/categories/" + cat["id"]
    assert (
        client.patch(cat_url, json={"name": "Consulting renamed", "active": False}).status_code
        == 200
    )
    entry_url = "/api/v1/income/" + entry["id"]
    assert client.get(entry_url).json()["category"]["name"] == "Consulting renamed"
    assert client.patch(entry_url, json={"notes": "Keep historical category"}).status_code == 200
    assert (
        client.post(
            "/api/v1/income", json={"title": "Archived", "amount": "1", "category_id": cat["id"]}
        ).status_code
        == 422
    )
    assert client.patch(cat_url, json={"type": "expense"}).status_code == 422
    assert client.patch(cat_url, json={"active": True}).json()["active"] is True


def test_filters_sorting_and_pagination(http):
    client, _ = http
    category = client.post(
        "/api/v1/categories", json={"name": "Filter category", "type": "income"}
    ).json()
    for index in range(23):
        create(
            client,
            title=f"Invoice {index:02d}",
            amount=str(index + 1),
            status="pending" if index % 2 else "draft",
            category_id=category["id"],
            entry_date=f"2026-01-{index + 1:02d}",
        )
    first = client.get(
        "/api/v1/income", params={"page_size": 10, "sort": "amount", "direction": "asc"}
    ).json()
    second = client.get(
        "/api/v1/income", params={"page_size": 10, "page": 2, "sort": "amount", "direction": "asc"}
    ).json()
    assert first["total"] == 23 and len(first["items"]) == 10
    assert first["items"][0]["amount"] == "1.00"
    assert second["items"][0]["amount"] == "11.00"
    filtered = client.get(
        "/api/v1/income",
        params={
            "date_from": "2026-01-05",
            "date_to": "2026-01-10",
            "status": "pending",
            "category_id": category["id"],
            "search": "invoice",
        },
    ).json()
    assert filtered["total"] == 3
    assert client.get("/api/v1/income", params={"search": "%"}).json()["total"] == 0
    assert client.get("/api/v1/income", params={"page_size": 101}).status_code == 422
    assert client.get("/api/v1/income", params={"sort": "amount;DROP"}).status_code == 422
    assert (
        client.get(
            "/api/v1/income", params={"date_from": "2026-02-01", "date_to": "2026-01-01"}
        ).status_code
        == 422
    )
