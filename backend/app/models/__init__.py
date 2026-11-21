"""SQLModel tables, one module per area. They mirror docs/schema.sql exactly.

Importing this package registers every table on `SQLModel.metadata`.
"""

from app.models.company import (
    AppUser,
    AuthSession,
    Company,
    CompanySettings,
    RecurringGenerationTiming,
    RecurringValidationMode,
    UserCompany,
    UserRole,
)
from app.models.ledger import Entry, EntryLine, EntrySource, EntryStatus, Payment, PaymentSource
from app.models.recognition import (
    DetectedType,
    FieldCorrection,
    JobStatus,
    PatternKind,
    RecognitionJob,
    RecognitionPattern,
)
from app.models.recurring import (
    AmountMode,
    OccurrenceStatus,
    RecurringOccurrence,
    RecurringTemplate,
    RecurringTemplateLine,
    RecurringTemplateVersion,
)
from app.models.reference import (
    Category,
    Counterparty,
    CounterpartyIban,
    CounterpartyRole,
    Direction,
)
from app.models.system import AppState, Notification, NotificationKind
from app.models.vat import VatCountry, VatRate

__all__ = [
    "AmountMode",
    "AppState",
    "AppUser",
    "AuthSession",
    "Category",
    "Company",
    "CompanySettings",
    "Counterparty",
    "CounterpartyIban",
    "CounterpartyRole",
    "DetectedType",
    "Direction",
    "Entry",
    "EntryLine",
    "EntrySource",
    "EntryStatus",
    "FieldCorrection",
    "JobStatus",
    "Notification",
    "NotificationKind",
    "OccurrenceStatus",
    "PatternKind",
    "Payment",
    "PaymentSource",
    "RecognitionJob",
    "RecognitionPattern",
    "RecurringGenerationTiming",
    "RecurringOccurrence",
    "RecurringTemplate",
    "RecurringTemplateLine",
    "RecurringTemplateVersion",
    "RecurringValidationMode",
    "UserCompany",
    "UserRole",
    "VatCountry",
    "VatRate",
]
