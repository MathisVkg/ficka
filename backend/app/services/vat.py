"""VAT arithmetic and rate lookup. Integers only: amounts in cents, rates in basis points.

The same algorithm lives in the frontend (`#lib/money.ts`) for the live preview; both
run the same test vectors. The server's result is authoritative.

- Net mode:   vat = round_half_up(net * rate_bp, 10000); gross = net + vat
- Gross mode: net = round_half_up(gross * 10000, 10000 + rate_bp); vat = gross - net
              (the gross the user typed is kept exactly)
- No rate:    vat = 0, net = gross
- Manual VAT: the given VAT is kept; net mode gross = net + vat, gross mode net = gross - vat
"""

from dataclasses import dataclass
from datetime import date

from sqlmodel import Session, col, or_, select

from app.models import VatRate

MAX_AMOUNT_CENTS = 10**12  # 10 000 000 000,00 €: far above any real invoice


class VatError(ValueError):
    """A line whose amounts can't be computed; `field` names the offending input."""

    def __init__(self, field: str, message: str) -> None:
        super().__init__(message)
        self.field = field
        self.message = message


def round_half_up(numerator: int, denominator: int) -> int:
    """numerator / denominator rounded half up, for numerator >= 0 and denominator > 0."""
    if numerator < 0 or denominator <= 0:
        raise ValueError("round_half_up expects numerator >= 0 and denominator > 0")
    return (2 * numerator + denominator) // (2 * denominator)


@dataclass(frozen=True)
class LineAmounts:
    net_cents: int
    vat_cents: int
    gross_cents: int


def compute_line(
    amount_cents: int,
    rate_bp: int | None,
    *,
    amounts_include_vat: bool,
    vat_manual: bool = False,
    vat_cents: int | None = None,
) -> LineAmounts:
    """Net, VAT and gross for one line. `amount_cents` is the net, or the gross in gross mode."""
    amount_field = "gross_cents" if amounts_include_vat else "net_cents"
    if amount_cents < 0:
        raise VatError(amount_field, "Amounts can't be negative.")
    if amount_cents > MAX_AMOUNT_CENTS:
        raise VatError(amount_field, "This amount is too large.")
    if rate_bp is not None and not 0 <= rate_bp <= 10000:
        raise VatError("vat_rate_bp", "The VAT rate must be between 0 and 100 %.")

    if rate_bp is None:
        if vat_manual and vat_cents:
            raise VatError("vat_cents", "A line without a VAT rate can't have VAT.")
        return LineAmounts(amount_cents, 0, amount_cents)

    if vat_manual:
        if vat_cents is None:
            raise VatError("vat_cents", "Enter the VAT amount.")
        if vat_cents < 0:
            raise VatError("vat_cents", "The VAT amount can't be negative.")
        if amounts_include_vat:
            if vat_cents > amount_cents:
                raise VatError("vat_cents", "The VAT can't be more than the total amount.")
            return LineAmounts(amount_cents - vat_cents, vat_cents, amount_cents)
        if vat_cents > MAX_AMOUNT_CENTS:
            raise VatError("vat_cents", "This amount is too large.")
        return LineAmounts(amount_cents, vat_cents, amount_cents + vat_cents)

    if amounts_include_vat:
        net = round_half_up(amount_cents * 10000, 10000 + rate_bp)
        return LineAmounts(net, amount_cents - net, amount_cents)
    vat = round_half_up(amount_cents * rate_bp, 10000)
    return LineAmounts(amount_cents, vat, amount_cents + vat)


def rates_valid_on(session: Session, country_code: str, on: date) -> list[VatRate]:
    """The VAT rates of a country valid on a date, highest first."""
    return list(
        session.exec(
            select(VatRate)
            .where(
                VatRate.country_code == country_code,
                col(VatRate.valid_from) <= on,
                or_(col(VatRate.valid_to).is_(None), col(VatRate.valid_to) >= on),
            )
            .order_by(col(VatRate.rate_bp).desc())
        ).all()
    )


def valid_rate_set(session: Session, country_code: str, on: date) -> set[int]:
    return {rate.rate_bp for rate in rates_valid_on(session, country_code, on)}


def known_rate_set(session: Session, country_code: str) -> set[int]:
    """Every rate the country has ever had (for defaults that aren't tied to a date)."""
    return set(session.exec(select(VatRate.rate_bp).where(VatRate.country_code == country_code)))
