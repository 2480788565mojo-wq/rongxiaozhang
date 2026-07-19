from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import (
    BigInteger,
    DateTime,
    Enum as SqlEnum,
    ForeignKey,
    Index,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PRIMARY_KEY, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ledger import Ledger
    from app.models.user import User


class ReportType(str, Enum):
    WEEKLY = "weekly"
    MONTHLY = "monthly"
    ON_DEMAND = "on_demand"


class ChatRole(str, Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"


class Insight(Base):
    __tablename__ = "insights"
    __table_args__ = (
        Index("idx_user_type", "user_id", "report_type", "generated_at"),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    ledger_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ledgers.id", ondelete="CASCADE"),
        nullable=False,
    )
    report_type: Mapped[ReportType] = mapped_column(
        SqlEnum(ReportType, native_enum=False, length=20),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    key_findings: Mapped[list[Any] | None] = mapped_column(JSON)
    suggested_actions: Mapped[list[Any] | None] = mapped_column(JSON)
    generated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
    )

    user: Mapped["User"] = relationship(back_populates="insights")
    ledger: Mapped["Ledger"] = relationship(back_populates="insights")


class ChatHistory(TimestampMixin, Base):
    __tablename__ = "chat_history"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    ledger_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ledgers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    session_id: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    role: Mapped[ChatRole] = mapped_column(
        SqlEnum(ChatRole, native_enum=False, length=16),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)

    user: Mapped["User"] = relationship(back_populates="chat_history")
    ledger: Mapped["Ledger"] = relationship(back_populates="chat_history")
