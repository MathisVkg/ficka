"""The one place that knows what "today" is.

Business rules that depend on the date (overdue, "this month") read it from here, as
a FastAPI dependency, so tests can freeze it with `app.dependency_overrides`.
"""

from datetime import date, datetime
from typing import Annotated
from zoneinfo import ZoneInfo

from fastapi import Depends

from app.config import get_settings


def today() -> date:
    """Today's date in the company's timezone (Europe/Brussels by default)."""
    return datetime.now(ZoneInfo(get_settings().timezone)).date()


def get_today() -> date:
    return today()


Today = Annotated[date, Depends(get_today)]
