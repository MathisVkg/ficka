"""Belgian identifiers: normalize, validate, format.

Each `normalize_*` function returns the stored form or raises `IdentifierError` with a
message that says what is wrong. `format_*` returns the grouped display form.
"""

import re


class IdentifierError(ValueError):
    pass


_SEPARATORS = re.compile(r"[\s.\-/+]")


def _compact(value: str) -> str:
    return _SEPARATORS.sub("", value).upper()


# --- VAT numbers ---------------------------------------------------------------------------


def normalize_vat_number(value: str) -> str:
    """'BE 0123.456.749', 'be0123456749' or '0123456749' -> 'BE0123456749'.

    Belgian numbers are checked (10 digits, first 0 or 1, mod-97 check). Numbers with
    another country prefix are kept as given (upper case, letters and digits only).
    """
    compact = _compact(value)
    if not compact:
        raise IdentifierError("Enter a VAT number.")
    if compact.isdigit():
        compact = "BE" + compact
    if not re.fullmatch(r"[A-Z]{2}[A-Z0-9]+", compact):
        raise IdentifierError(
            "A VAT number starts with a country code (e.g. BE) followed by letters or digits."
        )
    country, number = compact[:2], compact[2:]
    if country != "BE":
        return compact
    if not number.isdigit() or len(number) != 10:
        raise IdentifierError("A Belgian VAT number has 10 digits after BE.")
    if number[0] not in "01":
        raise IdentifierError("A Belgian VAT number starts with 0 or 1 after BE.")
    if 97 - int(number[:8]) % 97 != int(number[8:]):
        raise IdentifierError("This Belgian VAT number has an invalid check number.")
    return compact


def format_vat_number(value: str) -> str:
    """'BE0123456749' -> 'BE 0123.456.749' (other countries: 'FR 12345678901')."""
    if re.fullmatch(r"BE\d{10}", value):
        n = value[2:]
        return f"BE {n[:4]}.{n[4:7]}.{n[7:]}"
    return f"{value[:2]} {value[2:]}" if len(value) > 2 else value


# --- IBAN ----------------------------------------------------------------------------------

_IBAN_LENGTHS = {"BE": 16, "NL": 18, "LU": 20, "FR": 27, "DE": 22}


def normalize_iban(value: str) -> str:
    """Any spacing or case -> 'BE71096123456769'; ISO 13616 mod-97 check."""
    compact = re.sub(r"\s", "", value).upper()
    if not compact:
        raise IdentifierError("Enter an IBAN.")
    if not re.fullmatch(r"[A-Z]{2}\d{2}[A-Z0-9]{8,30}", compact):
        raise IdentifierError(
            "An IBAN starts with a country code and 2 check digits, then letters and digits."
        )
    expected = _IBAN_LENGTHS.get(compact[:2])
    if expected is not None and len(compact) != expected:
        raise IdentifierError(f"A {compact[:2]} IBAN has {expected} characters.")
    rearranged = compact[4:] + compact[:4]
    digits = "".join(str(int(ch, 36)) for ch in rearranged)
    if int(digits) % 97 != 1:
        raise IdentifierError("This IBAN has an invalid check number.")
    return compact


def format_iban(value: str) -> str:
    return " ".join(value[i : i + 4] for i in range(0, len(value), 4))


# --- Structured reference ------------------------------------------------------------------


def structured_reference_check(first_ten: str) -> int:
    remainder = int(first_ten) % 97
    return remainder or 97


def normalize_structured_reference(value: str) -> str:
    """'+++090/9337/55493+++' or '090933755493' -> '090933755493' (mod-97 check)."""
    compact = _compact(value)
    if not compact:
        raise IdentifierError("Enter a structured reference.")
    if not compact.isdigit() or len(compact) != 12:
        raise IdentifierError("A structured reference has 12 digits, like +++090/9337/55493+++.")
    if structured_reference_check(compact[:10]) != int(compact[10:]):
        raise IdentifierError("This structured reference has an invalid check number.")
    return compact


def format_structured_reference(value: str) -> str:
    return f"+++{value[:3]}/{value[3:7]}/{value[7:]}+++"
