"""Financial entries and reusable categories, preserving the 0001 foundation."""

from uuid import UUID

import sqlalchemy as sa
from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    categories = op.create_table(
        "categories",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("name_key", sa.String(200), nullable=False),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("color", sa.String(7), nullable=True),
        sa.Column("active", sa.Boolean(), nullable=False, server_default="true"),
        sa.UniqueConstraint("type", "name_key", name="uq_categories_type_name_key"),
        sa.CheckConstraint("type IN ('income', 'expense')", name="ck_categories_type"),
    )
    op.create_table(
        "financial_entries",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("type", sa.String(10), nullable=False),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("category_id", sa.Uuid(), sa.ForeignKey("categories.id", ondelete="RESTRICT")),
        sa.Column("counterparty", sa.String(200)),
        sa.Column("entry_date", sa.Date(), nullable=False),
        sa.Column("payment_date", sa.Date(), nullable=False),
        sa.Column("status", sa.String(10), nullable=False),
        sa.Column("vat_rate", sa.Numeric(7, 4), nullable=False),
        sa.Column("vat_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("vat_overridden", sa.Boolean(), nullable=False),
        sa.Column("notes", sa.Text()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column("deleted_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("type IN ('income', 'expense')", name="ck_entries_type"),
        sa.CheckConstraint("status IN ('draft', 'pending', 'paid')", name="ck_entries_status"),
        sa.CheckConstraint("amount > 0", name="ck_entries_positive_amount"),
        sa.CheckConstraint("vat_rate >= 0 AND vat_rate <= 100", name="ck_entries_vat_rate"),
        sa.CheckConstraint(
            "vat_amount >= 0 AND vat_amount <= amount", name="ck_entries_vat_amount"
        ),
    )
    op.create_index(
        "ix_entries_type_deleted_date", "financial_entries", ["type", "deleted_at", "entry_date"]
    )
    op.create_index("ix_entries_category", "financial_entries", ["category_id"])
    suggestions = [
        ("income", "Services", "#7250c9"),
        ("income", "Product sales", "#25856a"),
        ("income", "Other income", None),
        ("expense", "Office & supplies", "#d37569"),
        ("expense", "Software", "#7250c9"),
        ("expense", "Travel", "#b08a48"),
        ("expense", "Professional services", None),
        ("expense", "Other expenses", None),
    ]
    op.bulk_insert(
        categories,
        [
            {
                "id": UUID(int=index + 1),
                "name": name,
                "name_key": name.casefold(),
                "type": kind,
                "color": color,
                "active": True,
            }
            for index, (kind, name, color) in enumerate(suggestions)
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_entries_category", table_name="financial_entries")
    op.drop_index("ix_entries_type_deleted_date", table_name="financial_entries")
    op.drop_table("financial_entries")
    op.drop_table("categories")
