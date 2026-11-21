"""6. Recognition. No document content is ever stored here."""

import enum
from datetime import datetime

from sqlalchemy import CheckConstraint, Index, Integer, Text, UniqueConstraint
from sqlmodel import SQLModel

from app.models.base import (
    StrEnumText,
    UtcTimestamp,
    column,
    created_at_column,
    enum_check,
    id_column,
    range_check,
    updated_at_column,
)


class JobStatus(enum.StrEnum):
    QUEUED = "queued"
    PROCESSING = "processing"
    READY = "ready"
    FAILED = "failed"
    EXPIRED = "expired"
    RESOLVED = "resolved"


class DetectedType(enum.StrEnum):
    PEPPOL_UBL = "peppol_ubl"
    FACTUR_X = "factur_x"
    PDF_TEXT = "pdf_text"
    IMAGE = "image"


class PatternKind(enum.StrEnum):
    LABEL = "label"
    REGEX = "regex"
    ZONE = "zone"


class RecognitionJob(SQLModel, table=True):
    __tablename__ = "recognition_job"
    __table_args__ = (
        enum_check("status", JobStatus),
        enum_check("detected_type", DetectedType),
        range_check("overall_confidence", 0, 100),
        CheckConstraint(
            "status NOT IN ('resolved', 'expired') OR (temp_path IS NULL AND result_json IS NULL)",
            name="closed_job_has_no_content",
        ),
        Index("ix_job_status_expiry", "status", "expires_at"),
    )

    # Random UUID, also the temporary file name.
    id: str | None = column(Text, primary_key=True, nullable=True)
    company_id: int = column(Integer, nullable=False, foreign_key="company.id", ondelete="CASCADE")
    status: JobStatus = column(
        StrEnumText(JobStatus), nullable=False, server_default="'queued'", default=JobStatus.QUEUED
    )
    file_hash: str = column(Text, nullable=False)
    mime_type: str = column(Text, nullable=False)
    detected_type: DetectedType | None = column(StrEnumText(DetectedType), nullable=True)
    extractor: str | None = column(Text, nullable=True)  # 'ubl', 'pdfplumber', 'tesseract', ...
    temp_path: str | None = column(Text, nullable=True)  # cleared when the file is deleted
    result_json: str | None = column(Text, nullable=True)  # cleared on resolve
    overall_confidence: int | None = column(Integer, nullable=True)
    duration_ms: int | None = column(Integer, nullable=True)
    error: str | None = column(Text, nullable=True)
    entry_id: int | None = column(
        Integer, nullable=True, foreign_key="entry.id", ondelete="SET NULL"
    )
    created_at: datetime = created_at_column()
    updated_at: datetime = updated_at_column()
    expires_at: datetime = column(UtcTimestamp, nullable=False)


class RecognitionPattern(SQLModel, table=True):
    """Supplier memory: how to find a field on this counterparty's documents."""

    __tablename__ = "recognition_pattern"
    __table_args__ = (
        enum_check("kind", PatternKind),
        UniqueConstraint("counterparty_id", "field", "kind", "value"),
    )

    id: int | None = id_column()
    counterparty_id: int = column(
        Integer, nullable=False, foreign_key="counterparty.id", ondelete="CASCADE"
    )
    field: str = column(Text, nullable=False)  # 'invoice_number', 'total_gross', ...
    kind: PatternKind = column(StrEnumText(PatternKind), nullable=False)
    value: str = column(Text, nullable=False)  # label text, a regex, or a zone JSON
    hits: int = column(Integer, nullable=False, server_default="0", default=0)
    misses: int = column(Integer, nullable=False, server_default="0", default=0)
    last_used_at: datetime | None = column(UtcTimestamp, nullable=True)
    created_at: datetime = created_at_column()


class FieldCorrection(SQLModel, table=True):
    """What the user changed between proposal and confirmation."""

    __tablename__ = "field_correction"
    __table_args__ = (
        range_check("proposed_confidence", 0, 100),
        Index("ix_correction_field", "company_id", "field"),
    )

    id: int | None = id_column()
    company_id: int = column(Integer, nullable=False, foreign_key="company.id", ondelete="CASCADE")
    counterparty_id: int | None = column(
        Integer, nullable=True, foreign_key="counterparty.id", ondelete="SET NULL"
    )
    entry_id: int | None = column(
        Integer, nullable=True, foreign_key="entry.id", ondelete="SET NULL"
    )
    field: str = column(Text, nullable=False)
    proposed_value: str | None = column(Text, nullable=True)
    final_value: str | None = column(Text, nullable=True)
    proposed_confidence: int | None = column(Integer, nullable=True)
    field_source: str | None = column(Text, nullable=True)  # 'xml', 'text', 'ocr', 'memory', ...
    created_at: datetime = created_at_column()
