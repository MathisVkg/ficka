"""Payment status: derived from payments, never stored (docs/database.md).

    paid_total = SUM(payment.amount_cents)
    if paid_total >= total_gross_cents   -> paid
    elif paid_total > 0                  -> partial  (overdue if due_date < today)
    elif due_date < today                -> overdue
    else                                 -> unpaid

`payment_status_expr()` is the one SQL expression used by every query (list, filter,
sort, detail). `payment_status()` is the same rule in plain Python; the tests check
that both always agree.
"""

import enum
from datetime import date

from sqlalchemy import and_, case, func
from sqlalchemy.sql.elements import ColumnElement
from sqlmodel import col, select

from app.models import Entry, Payment


class PaymentStatus(enum.StrEnum):
    UNPAID = "unpaid"
    PARTIAL = "partial"
    PAID = "paid"
    OVERDUE = "overdue"


def paid_cents_expr() -> ColumnElement[int]:
    """SUM of the entry's payments (0 without payments), correlated to `entry`."""
    return (
        select(func.coalesce(func.sum(Payment.amount_cents), 0))
        .where(Payment.entry_id == Entry.id)
        .correlate(Entry)
        .scalar_subquery()
    )


def payment_status_expr(today: date, paid: ColumnElement[int] | None = None) -> ColumnElement[str]:
    paid = paid if paid is not None else paid_cents_expr()
    overdue = and_(col(Entry.due_date).is_not(None), col(Entry.due_date) < today)
    return case(
        (paid >= Entry.total_gross_cents, PaymentStatus.PAID.value),
        (and_(paid > 0, overdue), PaymentStatus.OVERDUE.value),
        (paid > 0, PaymentStatus.PARTIAL.value),
        (overdue, PaymentStatus.OVERDUE.value),
        else_=PaymentStatus.UNPAID.value,
    )


def payment_status(
    gross_cents: int, paid_cents: int, due_date: date | None, today: date
) -> PaymentStatus:
    overdue = due_date is not None and due_date < today
    if paid_cents >= gross_cents:
        return PaymentStatus.PAID
    if paid_cents > 0:
        return PaymentStatus.OVERDUE if overdue else PaymentStatus.PARTIAL
    return PaymentStatus.OVERDUE if overdue else PaymentStatus.UNPAID
