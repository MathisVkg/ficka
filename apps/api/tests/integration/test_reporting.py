import os
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.db.session import get_session
from app.models import Entry

pytestmark = pytest.mark.skipif(
    os.getenv("RUN_DB_TESTS") != "1", reason="Requires migrated PostgreSQL"
)
JAN = "date_from=2026-01-01&date_to=2026-01-31"


@pytest.fixture
def reports():
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


def seed(
    session,
    kind="income",
    amount="121",
    status="paid",
    entry="2026-01-01",
    payment="2026-01-01",
    vat="0",
    currency="EUR",
    category=None,
    deleted=False,
):
    value = Entry(
        type=kind,
        title="Reporting test",
        amount=Decimal(amount),
        status=status,
        entry_date=date.fromisoformat(entry),
        payment_date=date.fromisoformat(payment),
        vat_rate=Decimal("21"),
        vat_amount=Decimal(vat),
        vat_overridden=True,
        country="BE",
        currency=currency,
        category_id=category,
        deleted_at=datetime.now(UTC) if deleted else None,
    )
    session.add(value)
    session.flush()
    return value


def scenario(session):
    seed(session, entry="2025-12-31", vat="20", category="00000000-0000-0000-0000-000000000001")
    seed(
        session,
        "expense",
        "60.50",
        entry="2026-01-02",
        payment="2026-01-31",
        vat="10.50",
        category="00000000-0000-0000-0000-000000000004",
    )
    seed(
        session, amount="242", status="pending", entry="2026-01-03", payment="2026-01-15", vat="42"
    )
    seed(
        session, "expense", "12.10", "pending", entry="2026-01-04", payment="2026-02-01", vat="2.10"
    )
    seed(session, amount="999", status="draft", vat="100")
    seed(session, "expense", "1000", vat="100", deleted=True)
    seed(session, amount="100", vat="21", currency="USD")
    seed(session, "expense", "200", "pending", vat="30", currency="USD")
    seed(session, amount="0.10", vat="0")
    seed(session, amount="0.20", vat="0")


def get(client, endpoint, query=JAN):
    response = client.get("/api/v1/reports/" + endpoint + ("?" + query if query else ""))
    assert response.status_code == 200, response.text
    return response.json()


def test_summary_status_payment_dates_currency_and_recorded_vat(reports):
    client, session = reports
    scenario(session)
    result = get(client, "summary")
    assert result["actual"] == {
        "income": "121.30",
        "expenses": "60.50",
        "net": "60.80",
        "entry_count": 4,
    }
    assert result["expected"] == {
        "income": "242.00",
        "expenses": "0.00",
        "net": "242.00",
        "entry_count": 1,
    }
    assert result["vat"]["output"] == "42.00"
    assert result["vat"]["input"] == "12.60"
    assert result["vat"]["difference"] == "29.40"
    assert result["vat"]["date_basis"] == "entry_date"
    assert result["non_eur_excluded_count"] == 2
    assert result["vat"]["non_eur_excluded_count"] == 2
    december = get(client, "summary", "date_from=2025-12-01&date_to=2025-12-31")
    assert december["actual"]["income"] == "0.00"
    assert december["vat"]["output"] == "20.00"  # recorded override, not a recomputed rate


def test_cash_zero_months_and_expected_separation(reports):
    client, session = reports
    scenario(session)
    query = "date_from=2026-01-01&date_to=2026-03-31"
    actual = get(client, "cash-flow", query)
    assert len(actual["items"]) == 3
    assert actual["items"][0]["income"] == "121.30"
    assert actual["items"][1]["income"] == actual["items"][1]["expenses"] == "0.00"
    assert actual["items"][2]["entry_count"] == 0
    assert actual["non_eur_excluded_count"] == 1
    expected = get(client, "cash-flow", query + "&basis=expected")
    assert expected["items"][0]["income"] == "242.00"
    assert expected["items"][1]["expenses"] == "12.10"
    assert expected["non_eur_excluded_count"] == 1


def test_week_month_boundaries_and_timezone_independence(reports):
    client, session = reports
    seed(session, amount="0.10", entry="2025-12-31", payment="2025-12-31")
    seed(session, amount="0.20", payment="2026-01-01")
    query = "date_from=2025-12-29&date_to=2026-01-04&grouping=week"
    session.execute(text("SET LOCAL TIME ZONE 'Pacific/Kiritimati'"))
    first = get(client, "cash-flow", query)
    session.execute(text("SET LOCAL TIME ZONE 'America/Los_Angeles'"))
    second = get(client, "cash-flow", query)
    assert first == second
    assert first["items"][0]["bucket_start"] == "2025-12-29"
    assert first["items"][0]["income"] == "0.30"
    monthly = get(client, "cash-flow", "date_from=2025-12-31&date_to=2026-01-01")
    assert [item["income"] for item in monthly["items"]] == ["0.10", "0.20"]
    assert monthly["items"][0]["date_from"] == "2025-12-31"


def test_categories_uncategorized_archived_and_percentages(reports):
    client, session = reports
    cat = "00000000-0000-0000-0000-000000000004"
    client.patch("/api/v1/categories/" + cat, json={"active": False})
    seed(session, "expense", "1", category=cat)
    seed(session, "expense", "1")
    seed(session, "expense", "1", category="00000000-0000-0000-0000-000000000005")
    seed(session, "expense", "50", status="pending")
    seed(session, "expense", "80", deleted=True)
    seed(session, "expense", "90", currency="GBP")
    result = get(client, "expense-categories")
    assert result["total"] == "3.00"
    assert result["entry_count"] == 3
    assert result["non_eur_excluded_count"] == 1
    assert sum(Decimal(row["percentage"]) for row in result["items"]) == Decimal("100")
    assert "Uncategorized" in [row["name"] for row in result["items"]]
    assert any(row["active"] is False for row in result["items"])
    seed(session, amount="12.34")
    income = get(client, "income-categories")
    assert income["total"] == "12.34"
    assert income["items"][0]["percentage"] == "100.00"


def test_vat_calendar_quarters_and_leap_day(reports):
    client, session = reports
    for entry, vat in [
        ("2024-02-29", "1.01"),
        ("2024-03-31", "2.02"),
        ("2024-04-01", "3.03"),
        ("2024-12-31", "4.04"),
        ("2025-01-01", "5.05"),
    ]:
        seed(session, amount="100", entry=entry, payment="2026-01-01", vat=vat)
    seed(session, "expense", "100", entry="2024-04-01", vat="1.01", status="pending")
    seed(session, amount="100", entry="2024-03-31", vat="50", status="draft")
    seed(session, amount="100", entry="2024-03-31", vat="50", deleted=True)
    seed(session, amount="100", entry="2024-03-31", vat="50", currency="USD")
    result = get(client, "vat", "year=2024")
    assert [quarter["output"] for quarter in result["quarters"]] == ["3.03", "3.03", "0.00", "4.04"]
    assert result["quarters"][1]["input"] == "1.01"
    assert result["output"] == "10.10"
    assert result["difference"] == "9.09"
    assert result["non_eur_excluded_count"] == 1
    assert result["quarters"][0]["date_to"] == "2024-03-31"


def test_pending_scope_overdue_ordering_pagination_and_type(reports):
    client, session = reports
    for day in ["2026-01-01", "2026-01-10", "2026-02-01"]:
        seed(session, "expense", "10", "pending", payment=day)
    seed(session, amount="4", status="pending", payment="2026-01-05")
    seed(session, "expense", "100", "pending", currency="USD")
    seed(session, "expense", "100", "draft")
    seed(session, "expense", "100", "pending", deleted=True)
    result = get(client, "pending", JAN + "&as_of=2026-01-10&page_size=2")
    assert result["income"] == "4.00" and result["expenses"] == "20.00"
    assert result["total"] == 3 and result["overdue_count"] == 2
    assert result["items"][0]["payment_date"] == "2026-01-01"
    assert result["items"][0]["overdue"] is True
    assert (
        get(client, "pending", JAN + "&as_of=2026-01-10&page=2&page_size=2")["items"][0]["overdue"]
        is False
    )
    all_entries = get(client, "pending", "scope=all&type=expense")
    assert all_entries["total"] == 3 and all_entries["date_from"] is None
    assert all_entries["expenses"] == "30.00"
    assert all_entries["non_eur_excluded_count"] == 1


def test_empty_and_genuine_zero_net(reports):
    client, session = reports
    assert get(client, "summary")["actual"]["income"] == "0.00"
    assert get(client, "expense-categories")["items"] == []
    assert get(client, "cash-flow")["entry_count"] == 0
    assert len(get(client, "vat", "year=2026")["quarters"]) == 4
    assert get(client, "pending")["total"] == 0
    seed(session, amount="0.10")
    seed(session, "expense", "0.10")
    result = get(client, "summary")
    assert result["actual"]["net"] == "0.00" and result["actual"]["entry_count"] == 2


@pytest.mark.parametrize(
    "endpoint,query",
    [
        ("summary", "date_from=2026-01-01"),
        ("summary", "date_to=2026-01-01"),
        ("summary", "date_from=2026-02-01&date_to=2026-01-01"),
        ("summary", "date_from=2000-01-01&date_to=2026-01-01"),
        ("summary", "date_from=2026-02-30&date_to=2026-03-01"),
        ("cash-flow", JAN + "&grouping=day"),
        ("cash-flow", JAN + "&basis=draft"),
        ("vat", "year=2101"),
        ("pending", JAN + "&scope=all"),
        ("pending", "page=0"),
        ("pending", "page_size=101"),
        ("pending", "type=other"),
    ],
)
def test_invalid_queries(reports, endpoint, query):
    client, _ = reports
    response = client.get("/api/v1/reports/" + endpoint + "?" + query)
    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_error"


def test_aggregate_query_counts_no_n_plus_one(reports):
    client, session = reports
    scenario(session)
    queries = []

    def capture(connection, cursor, statement, parameters, context, many):
        if statement.lstrip().upper().startswith("SELECT"):
            queries.append(statement)

    connection = session.get_bind()
    event.listen(connection, "before_cursor_execute", capture)
    try:
        get(client, "summary")
        assert len(queries) == 1
        queries.clear()
        get(client, "expense-categories")
        assert len(queries) == 1
        queries.clear()
        get(client, "pending")
        assert len(queries) == 2
    finally:
        event.remove(connection, "before_cursor_execute", capture)
