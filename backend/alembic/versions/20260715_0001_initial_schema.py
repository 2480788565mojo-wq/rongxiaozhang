"""Create the initial Rongxiaozhang v2 schema.

Revision ID: 20260715_0001
Revises:
Create Date: 2026-07-15
"""
from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "20260715_0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column]:
    return [
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("openid", sa.String(64), nullable=False),
        sa.Column("nickname", sa.String(64), nullable=True),
        sa.Column("avatar_url", sa.String(512), nullable=True),
        sa.Column("default_ledger_id", sa.BigInteger(), nullable=True),
        *_timestamps(),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("openid"),
    )
    op.create_index("ix_users_default_ledger_id", "users", ["default_ledger_id"])

    op.create_table(
        "ledgers",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("name", sa.String(80), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=False),
        sa.Column("invite_code", sa.String(32), nullable=True),
        sa.Column("settle_strategy", sa.String(32), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["owner_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("invite_code"),
    )
    op.create_index("ix_ledgers_owner_id", "ledgers", ["owner_id"])
    op.create_index("ix_ledgers_invite_code", "ledgers", ["invite_code"])

    op.create_table(
        "ledger_members",
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("ledger_id", "user_id"),
    )

    op.create_table(
        "accounts",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("type", sa.String(32), nullable=False),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("balance", sa.Numeric(14, 2), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "ledger_id", "name", name="uk_account_user_ledger_name"
        ),
    )
    op.create_index("ix_accounts_user_id", "accounts", ["user_id"])
    op.create_index("ix_accounts_ledger_id", "accounts", ["ledger_id"])

    op.create_table(
        "categories",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("parent_name", sa.String(64), nullable=False),
        sa.Column("name", sa.String(64), nullable=False),
        sa.Column("icon", sa.String(64), nullable=True),
        sa.Column("sort", sa.Integer(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id",
            "ledger_id",
            "type",
            "parent_name",
            "name",
            name="uk_category_scope_name",
        ),
    )
    op.create_index("ix_categories_user_id", "categories", ["user_id"])
    op.create_index("ix_categories_ledger_id", "categories", ["ledger_id"])

    op.create_table(
        "bills",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("creator_id", sa.BigInteger(), nullable=False),
        sa.Column("type", sa.String(16), nullable=False),
        sa.Column("amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("category", sa.String(64), nullable=False),
        sa.Column("subcategory", sa.String(64), nullable=True),
        sa.Column("account", sa.String(64), nullable=True),
        sa.Column("note", sa.String(256), nullable=True),
        sa.Column("bill_date", sa.Date(), nullable=False),
        sa.Column("raw_input", sa.Text(), nullable=True),
        sa.Column("ai_parsed", sa.Boolean(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["creator_id"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_bills_creator_id", "bills", ["creator_id"])
    op.create_index("ix_bills_bill_date", "bills", ["bill_date"])
    op.create_index("idx_ledger_date", "bills", ["ledger_id", "bill_date"])
    op.create_index(
        "idx_ledger_category", "bills", ["ledger_id", "category", "bill_date"]
    )

    op.create_table(
        "bill_shares",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("bill_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("share_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("settled", sa.Boolean(), nullable=False),
        sa.Column("settled_at", sa.Date(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(["bill_id"], ["bills.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("bill_id", "user_id", name="uk_bill_user"),
    )
    op.create_index("ix_bill_shares_bill_id", "bill_shares", ["bill_id"])
    op.create_index("ix_bill_shares_user_id", "bill_shares", ["user_id"])

    op.create_table(
        "budgets",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("year", sa.Integer(), nullable=False),
        sa.Column("month", sa.Integer(), nullable=False),
        sa.Column("total_budget", sa.Numeric(14, 2), nullable=True),
        sa.Column("category_budgets", sa.JSON(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "user_id", "year", "month", "ledger_id", name="uk_user_ym_ledger"
        ),
    )
    op.create_index("ix_budgets_ledger_id", "budgets", ["ledger_id"])
    op.create_index("ix_budgets_user_id", "budgets", ["user_id"])

    op.create_table(
        "insights",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("report_type", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("key_findings", sa.JSON(), nullable=True),
        sa.Column("suggested_actions", sa.JSON(), nullable=True),
        sa.Column(
            "generated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_user_type", "insights", ["user_id", "report_type", "generated_at"]
    )

    op.create_table(
        "chat_history",
        sa.Column("id", sa.BigInteger(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("ledger_id", sa.BigInteger(), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("role", sa.String(16), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["ledger_id"], ["ledgers.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_history_user_id", "chat_history", ["user_id"])
    op.create_index("ix_chat_history_ledger_id", "chat_history", ["ledger_id"])
    op.create_index("ix_chat_history_session_id", "chat_history", ["session_id"])


def downgrade() -> None:
    op.drop_table("chat_history")
    op.drop_table("insights")
    op.drop_table("budgets")
    op.drop_table("bill_shares")
    op.drop_table("bills")
    op.drop_table("categories")
    op.drop_table("accounts")
    op.drop_table("ledger_members")
    op.drop_table("ledgers")
    op.drop_table("users")
