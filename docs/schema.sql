-- =====================================================================
-- Ficka — reference database schema (SQLite)
-- ---------------------------------------------------------------------
-- This file is the SPECIFICATION of the data model. The application
-- will create the real tables through SQLModel + Alembic migrations;
-- those must stay equivalent to this file.
--
-- Conventions
--   * Money        INTEGER cents            (1 512,50 € -> 151250)
--   * VAT rate     INTEGER basis points     (21 %       -> 2100), NULL = no VAT
--   * Dates        TEXT 'YYYY-MM-DD'
--   * Timestamps   TEXT ISO-8601 UTC        ('2026-11-21T16:40:00Z')
--   * Booleans     INTEGER 0 / 1
--   * Every business table carries company_id (multi-company foundation,
--     a single company in v1).
-- =====================================================================

PRAGMA foreign_keys = ON;

-- ---------------------------------------------------------------------
-- 1. Company, users, settings
-- ---------------------------------------------------------------------

CREATE TABLE company (
    id              INTEGER PRIMARY KEY,
    name            TEXT    NOT NULL,
    country_code    TEXT    NOT NULL DEFAULT 'BE' REFERENCES vat_country(code),
    vat_number      TEXT,                              -- normalized, e.g. 'BE0123456749'
    currency        TEXT    NOT NULL DEFAULT 'EUR',
    created_at      TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

CREATE TABLE company_settings (
    company_id                      INTEGER PRIMARY KEY REFERENCES company(id) ON DELETE CASCADE,
    recurring_generation_timing     TEXT    NOT NULL DEFAULT 'first_of_month'
                                    CHECK (recurring_generation_timing IN ('first_of_month', 'due_date')),
    recurring_validation_mode       TEXT    NOT NULL DEFAULT 'review'
                                    CHECK (recurring_validation_mode IN ('review', 'automatic')),
    amounts_include_vat_default     INTEGER NOT NULL DEFAULT 0 CHECK (amounts_include_vat_default IN (0, 1)),
    starting_balance_cents          INTEGER,           -- NULL = not configured
    starting_balance_date           TEXT,
    document_ttl_hours              INTEGER NOT NULL DEFAULT 24 CHECK (document_ttl_hours > 0),
    locale                          TEXT    NOT NULL DEFAULT 'en',
    updated_at                      TEXT    NOT NULL,
    CHECK ((starting_balance_cents IS NULL) = (starting_balance_date IS NULL))
);

CREATE TABLE app_user (
    id              INTEGER PRIMARY KEY,
    email           TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    password_hash   TEXT    NOT NULL,                  -- argon2id
    display_name    TEXT    NOT NULL,
    created_at      TEXT    NOT NULL,
    last_login_at   TEXT
);

-- Foundation only: v1 has one user, one company, role 'owner'.
CREATE TABLE user_company (
    user_id         INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    company_id      INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    role            TEXT    NOT NULL DEFAULT 'owner' CHECK (role IN ('owner')),
    PRIMARY KEY (user_id, company_id)
);

CREATE TABLE auth_session (
    id              TEXT    PRIMARY KEY,               -- hash of the session token, never the token itself
    user_id         INTEGER NOT NULL REFERENCES app_user(id) ON DELETE CASCADE,
    created_at      TEXT    NOT NULL,
    expires_at      TEXT    NOT NULL
);
CREATE INDEX ix_auth_session_user ON auth_session(user_id);

-- ---------------------------------------------------------------------
-- 2. VAT configuration (data, not code)
-- ---------------------------------------------------------------------

CREATE TABLE vat_country (
    code            TEXT    PRIMARY KEY,               -- ISO 3166-1 alpha-2
    name            TEXT    NOT NULL
);

CREATE TABLE vat_rate (
    id              INTEGER PRIMARY KEY,
    country_code    TEXT    NOT NULL REFERENCES vat_country(code),
    rate_bp         INTEGER NOT NULL CHECK (rate_bp BETWEEN 0 AND 10000),
    label           TEXT    NOT NULL,
    valid_from      TEXT    NOT NULL,
    valid_to        TEXT,                              -- NULL = still valid
    CHECK (valid_to IS NULL OR valid_to >= valid_from),
    UNIQUE (country_code, rate_bp, valid_from)
);

-- ---------------------------------------------------------------------
-- 3. Reference data: categories and counterparties
-- ---------------------------------------------------------------------

CREATE TABLE category (
    id                  INTEGER PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    direction           TEXT    NOT NULL CHECK (direction IN ('income', 'expense')),
    name                TEXT    NOT NULL,
    default_vat_rate_bp INTEGER CHECK (default_vat_rate_bp BETWEEN 0 AND 10000),  -- NULL = no VAT
    is_seeded           INTEGER NOT NULL DEFAULT 0 CHECK (is_seeded IN (0, 1)),   -- came with the install
    position            INTEGER NOT NULL DEFAULT 0,
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL,
    UNIQUE (company_id, direction, name)
);

CREATE TABLE counterparty (
    id                  INTEGER PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    name                TEXT    NOT NULL,
    role                TEXT    NOT NULL DEFAULT 'supplier' CHECK (role IN ('customer', 'supplier', 'both')),
    vat_number          TEXT,                          -- normalized, e.g. 'BE0123456749'
    default_category_id INTEGER REFERENCES category(id) ON DELETE SET NULL,
    default_vat_rate_bp INTEGER CHECK (default_vat_rate_bp BETWEEN 0 AND 10000),
    notes               TEXT,
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL
);
CREATE UNIQUE INDEX ux_counterparty_vat ON counterparty(company_id, vat_number) WHERE vat_number IS NOT NULL;
CREATE INDEX ix_counterparty_name ON counterparty(company_id, name COLLATE NOCASE);

CREATE TABLE counterparty_iban (
    id              INTEGER PRIMARY KEY,
    counterparty_id INTEGER NOT NULL REFERENCES counterparty(id) ON DELETE CASCADE,
    iban            TEXT    NOT NULL,                  -- normalized, no spaces, upper case
    UNIQUE (counterparty_id, iban)
);
CREATE INDEX ix_counterparty_iban ON counterparty_iban(iban);

-- ---------------------------------------------------------------------
-- 4. Ledger: entries, lines, payments
-- ---------------------------------------------------------------------

CREATE TABLE entry (
    id                      INTEGER PRIMARY KEY,
    company_id              INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    direction               TEXT    NOT NULL CHECK (direction IN ('income', 'expense')),
    status                  TEXT    NOT NULL DEFAULT 'confirmed' CHECK (status IN ('proposed', 'confirmed')),
    source                  TEXT    NOT NULL DEFAULT 'manual'
                            CHECK (source IN ('manual', 'recurring', 'document', 'bank')),
    invoice_date            TEXT    NOT NULL,
    due_date                TEXT,
    counterparty_id         INTEGER REFERENCES counterparty(id) ON DELETE SET NULL,
    category_id             INTEGER REFERENCES category(id) ON DELETE RESTRICT,  -- reassign before deleting a category
    description             TEXT,
    invoice_number          TEXT,
    structured_reference    TEXT,                      -- Belgian +++xxx/xxxx/xxxxx+++ stored as 12 digits
    currency                TEXT    NOT NULL DEFAULT 'EUR',
    amounts_include_vat     INTEGER NOT NULL DEFAULT 0 CHECK (amounts_include_vat IN (0, 1)),  -- input mode used
    -- Cached totals: ALWAYS recomputed from entry_line by the service layer, never typed in.
    total_net_cents         INTEGER NOT NULL DEFAULT 0,
    total_vat_cents         INTEGER NOT NULL DEFAULT 0,
    total_gross_cents       INTEGER NOT NULL DEFAULT 0,
    document_hash           TEXT,                      -- SHA-256 of the processed file (duplicate detection)
    document_location       TEXT,                      -- optional link/path to the user's own storage
    confirmed_at            TEXT,
    created_at              TEXT    NOT NULL,
    updated_at              TEXT    NOT NULL,
    CHECK (due_date IS NULL OR due_date >= invoice_date),
    CHECK (structured_reference IS NULL OR length(structured_reference) = 12),
    CHECK (total_gross_cents = total_net_cents + total_vat_cents),
    CHECK ((status = 'confirmed') = (confirmed_at IS NOT NULL))
);
CREATE INDEX ix_entry_company_date   ON entry(company_id, invoice_date);
CREATE INDEX ix_entry_company_status ON entry(company_id, status);
CREATE INDEX ix_entry_counterparty   ON entry(counterparty_id);
CREATE INDEX ix_entry_document_hash  ON entry(company_id, document_hash) WHERE document_hash IS NOT NULL;
CREATE INDEX ix_entry_invoice_number ON entry(company_id, counterparty_id, invoice_number) WHERE invoice_number IS NOT NULL;

CREATE TABLE entry_line (
    id              INTEGER PRIMARY KEY,
    entry_id        INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    position        INTEGER NOT NULL DEFAULT 0,
    description     TEXT,
    net_cents       INTEGER NOT NULL,
    vat_rate_bp     INTEGER CHECK (vat_rate_bp BETWEEN 0 AND 10000),  -- NULL = no VAT
    vat_cents       INTEGER NOT NULL DEFAULT 0,
    vat_manual      INTEGER NOT NULL DEFAULT 0 CHECK (vat_manual IN (0, 1)),  -- 1 = user or document set it, do not recalculate
    CHECK (vat_rate_bp IS NOT NULL OR vat_cents = 0)
);
CREATE INDEX ix_entry_line_entry ON entry_line(entry_id);

CREATE TABLE payment (
    id              INTEGER PRIMARY KEY,
    entry_id        INTEGER NOT NULL REFERENCES entry(id) ON DELETE CASCADE,
    paid_on         TEXT    NOT NULL,
    amount_cents    INTEGER NOT NULL CHECK (amount_cents > 0),
    source          TEXT    NOT NULL DEFAULT 'manual' CHECK (source IN ('manual', 'assumed', 'bank')),
    note            TEXT,
    created_at      TEXT    NOT NULL
);
CREATE INDEX ix_payment_entry ON payment(entry_id);
CREATE INDEX ix_payment_paid_on ON payment(paid_on);

-- ---------------------------------------------------------------------
-- 5. Recurring
-- ---------------------------------------------------------------------

CREATE TABLE recurring_template (
    id                  INTEGER PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    name                TEXT    NOT NULL,
    direction           TEXT    NOT NULL CHECK (direction IN ('income', 'expense')),
    counterparty_id     INTEGER REFERENCES counterparty(id) ON DELETE SET NULL,
    category_id         INTEGER REFERENCES category(id) ON DELETE RESTRICT,
    description         TEXT,
    interval_months     INTEGER NOT NULL DEFAULT 1 CHECK (interval_months BETWEEN 1 AND 120),  -- 1 monthly, 3 quarterly, 12 yearly
    due_day             INTEGER NOT NULL CHECK (due_day BETWEEN 1 AND 31),                 -- 31 = last day of month
    start_date          TEXT    NOT NULL,
    end_date            TEXT,
    max_occurrences     INTEGER CHECK (max_occurrences IS NULL OR max_occurrences > 0),
    amount_mode         TEXT    NOT NULL DEFAULT 'fixed' CHECK (amount_mode IN ('fixed', 'variable')),
    is_active           INTEGER NOT NULL DEFAULT 1 CHECK (is_active IN (0, 1)),
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL,
    CHECK (end_date IS NULL OR end_date >= start_date)
);

-- A price change creates a new version; past occurrences keep theirs.
CREATE TABLE recurring_template_version (
    id              INTEGER PRIMARY KEY,
    template_id     INTEGER NOT NULL REFERENCES recurring_template(id) ON DELETE CASCADE,
    effective_from  TEXT    NOT NULL,
    created_at      TEXT    NOT NULL,
    UNIQUE (template_id, effective_from)
);

CREATE TABLE recurring_template_line (
    id              INTEGER PRIMARY KEY,
    version_id      INTEGER NOT NULL REFERENCES recurring_template_version(id) ON DELETE CASCADE,
    position        INTEGER NOT NULL DEFAULT 0,
    description     TEXT,
    net_cents       INTEGER NOT NULL,
    vat_rate_bp     INTEGER CHECK (vat_rate_bp BETWEEN 0 AND 10000)  -- NULL = no VAT
);
CREATE INDEX ix_template_line_version ON recurring_template_line(version_id);

-- One row per (template, period): the idempotency guard.
CREATE TABLE recurring_occurrence (
    id              INTEGER PRIMARY KEY,
    template_id     INTEGER NOT NULL REFERENCES recurring_template(id) ON DELETE CASCADE,
    version_id      INTEGER NOT NULL REFERENCES recurring_template_version(id),
    period          TEXT    NOT NULL,                  -- 'YYYY-MM' of the due date
    due_date        TEXT    NOT NULL,
    status          TEXT    NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'generated', 'skipped')),
    entry_id        INTEGER UNIQUE REFERENCES entry(id) ON DELETE SET NULL,
    generated_at    TEXT,
    UNIQUE (template_id, period),
    CHECK (status <> 'generated' OR (generated_at IS NOT NULL AND entry_id IS NOT NULL))
);
CREATE INDEX ix_occurrence_due ON recurring_occurrence(status, due_date);

-- Deleting a generated entry marks its occurrence as skipped, so it is never regenerated.
CREATE TRIGGER trg_entry_delete_skips_occurrence
BEFORE DELETE ON entry
BEGIN
    UPDATE recurring_occurrence SET status = 'skipped', entry_id = NULL WHERE entry_id = OLD.id;
END;

-- ---------------------------------------------------------------------
-- 6. Recognition (no document content is ever stored here)
-- ---------------------------------------------------------------------

CREATE TABLE recognition_job (
    id                  TEXT    PRIMARY KEY,           -- random UUID, also the temp file name
    company_id          INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    status              TEXT    NOT NULL DEFAULT 'queued'
                        CHECK (status IN ('queued', 'processing', 'ready', 'failed', 'expired', 'resolved')),
    file_hash           TEXT    NOT NULL,
    mime_type           TEXT    NOT NULL,
    detected_type       TEXT    CHECK (detected_type IN ('peppol_ubl', 'factur_x', 'pdf_text', 'image')),
    extractor           TEXT,                          -- e.g. 'ubl', 'pdfplumber', 'tesseract', 'paddleocr', 'llm'
    temp_path           TEXT,                          -- cleared when the file is deleted
    result_json         TEXT,                          -- temporary: fields with value/confidence/source/bbox; cleared on resolve
    overall_confidence  INTEGER CHECK (overall_confidence BETWEEN 0 AND 100),
    duration_ms         INTEGER,
    error               TEXT,
    entry_id            INTEGER REFERENCES entry(id) ON DELETE SET NULL,  -- the proposal it created
    created_at          TEXT    NOT NULL,
    updated_at          TEXT    NOT NULL,
    expires_at          TEXT    NOT NULL,
    CHECK (status NOT IN ('resolved', 'expired') OR (temp_path IS NULL AND result_json IS NULL))
);
CREATE INDEX ix_job_status_expiry ON recognition_job(status, expires_at);

-- Supplier memory: how to find a field on this counterparty's documents.
CREATE TABLE recognition_pattern (
    id              INTEGER PRIMARY KEY,
    counterparty_id INTEGER NOT NULL REFERENCES counterparty(id) ON DELETE CASCADE,
    field           TEXT    NOT NULL,                  -- 'invoice_number', 'invoice_date', 'due_date', 'total_gross', ...
    kind            TEXT    NOT NULL CHECK (kind IN ('label', 'regex', 'zone')),
    value           TEXT    NOT NULL,                  -- label text ('Factuurnummer'), a regex, or a normalized zone JSON
    hits            INTEGER NOT NULL DEFAULT 0,
    misses          INTEGER NOT NULL DEFAULT 0,
    last_used_at    TEXT,
    created_at      TEXT    NOT NULL,
    UNIQUE (counterparty_id, field, kind, value)
);

-- What the user changed between proposal and confirmation: feeds memory and statistics.
CREATE TABLE field_correction (
    id                  INTEGER PRIMARY KEY,
    company_id          INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    counterparty_id     INTEGER REFERENCES counterparty(id) ON DELETE SET NULL,
    entry_id            INTEGER REFERENCES entry(id) ON DELETE SET NULL,
    field               TEXT    NOT NULL,
    proposed_value      TEXT,
    final_value         TEXT,
    proposed_confidence INTEGER CHECK (proposed_confidence BETWEEN 0 AND 100),
    field_source        TEXT,                          -- 'xml', 'text', 'ocr', 'memory', 'inferred', 'llm'
    created_at          TEXT    NOT NULL
);
CREATE INDEX ix_correction_field ON field_correction(company_id, field);

-- ---------------------------------------------------------------------
-- 7. Notifications and app state
-- ---------------------------------------------------------------------

-- Badges (proposal counts, overdue counts) are computed live; this table
-- only holds events worth telling the user once (toasts, small history).
CREATE TABLE notification (
    id              INTEGER PRIMARY KEY,
    company_id      INTEGER NOT NULL REFERENCES company(id) ON DELETE CASCADE,
    kind            TEXT    NOT NULL CHECK (kind IN (
                        'recurring_proposals', 'recurring_auto_created',
                        'document_ready', 'document_failed', 'document_expired')),
    payload_json    TEXT,
    read_at         TEXT,
    created_at      TEXT    NOT NULL
);
CREATE INDEX ix_notification_unread ON notification(company_id, read_at);

CREATE TABLE app_state (
    key             TEXT    PRIMARY KEY,               -- e.g. 'recurring.last_run_at', 'cleanup.last_run_at'
    value           TEXT    NOT NULL,
    updated_at      TEXT    NOT NULL
);

-- =====================================================================
-- Seed data
-- =====================================================================

INSERT INTO vat_country (code, name) VALUES ('BE', 'Belgium');

INSERT INTO vat_rate (country_code, rate_bp, label, valid_from) VALUES
    ('BE', 2100, 'Standard 21 %', '2000-01-01'),
    ('BE', 1200, 'Reduced 12 %',  '2000-01-01'),
    ('BE',  600, 'Reduced 6 %',   '2000-01-01'),
    ('BE',    0, 'Zero 0 %',      '2000-01-01');

-- Default categories are inserted by the install routine for each new company
-- (they need a company_id). Starting set, all editable — see docs/database.md.
