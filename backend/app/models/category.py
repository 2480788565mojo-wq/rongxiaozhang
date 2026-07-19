from enum import Enum
from typing import TYPE_CHECKING

from sqlalchemy import (
    BigInteger,
    Enum as SqlEnum,
    ForeignKey,
    Integer,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BIGINT_PRIMARY_KEY, Base, TimestampMixin

if TYPE_CHECKING:
    from app.models.ledger import Ledger
    from app.models.user import User


class CategoryType(str, Enum):
    EXPENSE = "expense"
    INCOME = "income"


class Category(TimestampMixin, Base):
    __tablename__ = "categories"
    __table_args__ = (
        UniqueConstraint(
            "user_id",
            "ledger_id",
            "type",
            "parent_name",
            "name",
            name="uk_category_scope_name",
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
    type: Mapped[CategoryType] = mapped_column(
        SqlEnum(CategoryType, native_enum=False, length=16),
        nullable=False,
    )
    parent_name: Mapped[str] = mapped_column(String(64), nullable=False, default="")
    name: Mapped[str] = mapped_column(String(64), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(64))
    sort: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    user: Mapped["User"] = relationship(back_populates="categories")
    ledger: Mapped["Ledger"] = relationship(back_populates="categories")
