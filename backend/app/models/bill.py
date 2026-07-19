from datetime import date
from decimal import Decimal
from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Boolean,
    Date,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PRIMARY_KEY, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ledger import Ledger
    from app.models.user import User


class BillType(str, Enum):
    EXPENSE = "expense"
    INCOME = "income"


class Bill(TimestampMixin, Base):
    __tablename__ = "bills"
    __table_args__ = (
        Index("idx_ledger_date", "ledger_id", "bill_date"),
        Index("idx_ledger_category", "ledger_id", "category", "bill_date"),
        UniqueConstraint(
            "creator_id",
            "ledger_id",
            "confirmation_session_id",
            name="uk_bill_creator_ledger_confirmation_session",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    ledger_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ledgers.id", ondelete="CASCADE"),
        nullable=False,
    )
    creator_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    type: Mapped[BillType] = mapped_column(
        SqlEnum(BillType, native_enum=False, length=16),
        nullable=False,
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    subcategory: Mapped[str | None] = mapped_column(String(64))
    account: Mapped[str | None] = mapped_column(String(64))
    note: Mapped[str | None] = mapped_column(String(256))
    bill_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    raw_input: Mapped[str | None] = mapped_column(Text)
    ai_parsed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    confirmation_session_id: Mapped[str | None] = mapped_column(String(64), nullable=True)

    ledger: Mapped["Ledger"] = relationship(back_populates="bills")
    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])
    shares: Mapped[list["BillShare"]] = relationship(
        back_populates="bill",
        cascade="all, delete-orphan",
    )


class BillShare(TimestampMixin, Base):
    __tablename__ = "bill_shares"
    __table_args__ = (UniqueConstraint("bill_id", "user_id", name="uk_bill_user"),)

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    bill_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("bills.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    share_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    settled: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    settled_at: Mapped[date | None] = mapped_column(Date)

    bill: Mapped[Bill] = relationship(back_populates="shares")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
