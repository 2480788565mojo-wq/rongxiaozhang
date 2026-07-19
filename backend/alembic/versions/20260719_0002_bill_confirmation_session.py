"""Add idempotency key for bill confirmation requests."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260719_0002"
down_revision: str | None = "20260715_0001"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "bills",
        sa.Column("confirmation_session_id", sa.String(64), nullable=True),
    )
    op.create_unique_constraint(
        "uk_bill_creator_ledger_confirmation_session",
        "bills",
        ["creator_id", "ledger_id", "confirmation_session_id"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uk_bill_creator_ledger_confirmation_session",
        "bills",
        type_="unique",
    )
    op.drop_column("bills", "confirmation_session_id")
