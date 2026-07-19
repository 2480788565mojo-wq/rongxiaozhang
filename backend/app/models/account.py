from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import BigInteger, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PRIMARY_KEY, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ledger import Ledger
    from app.models.user import User


class Account(TimestampMixin, Base):
    __tablename__ = "accounts"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "ledger_id",
            "name",
            name="uk_account_user_ledger_name",
        ),
    )

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
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    type: Mapped[str] = mapped_column(String(32), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64))
    balance: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
        default=0,
    )

    user: Mapped["User"] = relationship(back_populates="accounts")
    ledger: Mapped["Ledger"] = relationship(back_populates="accounts")
