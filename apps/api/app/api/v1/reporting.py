from datetime import date
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.session import get_session
from app.schemas.financial import EntryType, FinancialDate
from app.schemas.reporting import (
    CashFlowReport,
    CategoryReport,
    PendingReport,
    SummaryReport,
    VatReport,
)
from app.services import reporting as service

router = APIRouter(prefix="/reports", tags=["reports"])
DB = Annotated[Session, Depends(get_session)]


def period(date_from: FinancialDate | None = None, date_to: FinancialDate | None = None):
    return service.resolve_period(date_from, date_to)


Period = Annotated[tuple[date, date], Depends(period)]


@router.get("/summary", response_model=SummaryReport)
def summary(session: DB, dates: Period):
    return service.summary(session, *dates)


@router.get("/cash-flow", response_model=CashFlowReport)
def cash_flow(
    session: DB,
    dates: Period,
    grouping: Literal["month", "week"] = "month",
    basis: Literal["actual", "expected"] = "actual",
):
    return service.cash_flow(session, *dates, grouping, basis)


@router.get("/expense-categories", response_model=CategoryReport)
def expense_categories(session: DB, dates: Period):
    return service.categories(session, *dates, "expense")


@router.get("/income-categories", response_model=CategoryReport)
def income_categories(session: DB, dates: Period):
    return service.categories(session, *dates, "income")


@router.get("/pending", response_model=PendingReport)
def pending(
    session: DB,
    date_from: FinancialDate | None = None,
    date_to: FinancialDate | None = None,
    scope: Literal["period", "all"] = "period",
    as_of: FinancialDate | None = None,
    type: EntryType | None = None,
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = 20,
):
    if scope == "all":
        if date_from is not None or date_to is not None:
            raise HTTPException(422, "All-outstanding scope does not accept a date range")
        dates = (None, None)
    else:
        dates = service.resolve_period(date_from, date_to)
    return service.pending(session, *dates, scope, as_of or date.today(), type, page, page_size)


@router.get("/vat", response_model=VatReport)
def vat(session: DB, year: Annotated[int | None, Query(ge=1900, le=2100)] = None):
    return service.vat(session, year or date.today().year)
