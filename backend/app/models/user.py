from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PRIMARY_KEY, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.account import Account
    from app.models.category import Category
    from app.models.insight import ChatHistory, Insight
    from app.models.ledger import Ledger, LedgerMember


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    openid: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    nickname: Mapped[str | None] = mapped_column(String(64))
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    default_ledger_id: Mapped[int | None] = mapped_column(BigInteger, index=True)

    owned_ledgers: Mapped[list["Ledger"]] = relationship(
        back_populates="owner",
        foreign_keys="Ledger.owner_id",
    )
    ledger_memberships: Mapped[list["LedgerMember"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    insights: Mapped[list["Insight"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    chat_history: Mapped[list["ChatHistory"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    accounts: Mapped[list["Account"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
    categories: Mapped[list["Category"]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
