from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, Enum as SqlEnum, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PRIMARY_KEY, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.bill import Bill
    from app.models.budget import Budget
    from app.models.category import Category
    from app.models.insight import ChatHistory, Insight
    from app.models.user import User


class LedgerType(str, Enum):
    PERSONAL = "personal"
    SHARED = "shared"


class LedgerRole(str, Enum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class Ledger(TimestampMixin, Base):
    __tablename__ = "ledgers"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    type: Mapped[LedgerType] = mapped_column(
        SqlEnum(LedgerType, native_enum=False, length=16),
        nullable=False,
        default=LedgerType.PERSONAL,
    )
    owner_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    invite_code: Mapped[str | None] = mapped_column(
        String(32),
        unique=True,
        index=True,
    )
    settle_strategy: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="equal",
    )

    owner: Mapped["User"] = relationship(
        back_populates="owned_ledgers",
        foreign_keys=[owner_id],
    )
    members: Mapped[list["LedgerMember"]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
    )
    bills: Mapped[list["Bill"]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
    )
    budgets: Mapped[list["Budget"]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
    )
    chat_history: Mapped[list["ChatHistory"]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
    )
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
    )
    categories: Mapped[list["Category"]] = relationship(
        back_populates="ledger",
        cascade="all, delete-orphan",
    )


class LedgerMember(Base):
    __tablename__ = "ledger_members"

    ledger_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ledgers.id", ondelete="CASCADE"),
        primary_key=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )
    role: Mapped[LedgerRole] = mapped_column(
        SqlEnum(LedgerRole, native_enum=False, length=16),
        nullable=False,
        default=LedgerRole.MEMBER,
    )

    ledger: Mapped[Ledger] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="ledger_memberships")
