from decimal import Decimal
from typing import TYPE_CHECKING, Any

from sqlalchemy import BigInteger, ForeignKey, Integer, JSON, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PRIMARY_KEY, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ledger import Ledger
    from app.models.user import User


class Budget(TimestampMixin, Base):
    __tablename__ = "budgets"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "year",
            "month",
            "ledger_id",
            name="uk_user_ym_ledger",
        ),
    )

    id: Mapped[int] = mapped_column(BIGINT_PRIMARY_KEY, primary_key=True, autoincrement=True)
    ledger_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("ledgers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    month: Mapped[int] = mapped_column(Integer, nullable=False)
    total_budget: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    category_budgets: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=dict,
    )

    ledger: Mapped["Ledger"] = relationship(back_populates="budgets")
    user: Mapped["User"] = relationship(foreign_keys=[user_id])
