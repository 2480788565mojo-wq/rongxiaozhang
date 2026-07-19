from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Category, CategoryType
from app.schemas.category import CategoryCreate, CategoryUpdate


async def list_categories(
    db: AsyncSession,
    user_id: int,
    ledger_id: int,
    category_type: CategoryType | None = None,
) -> list[Category]:
    conditions = [Category.user_id == user_id, Category.ledger_id == ledger_id]
    if category_type is not None:
        conditions.append(Category.type == category_type)
    result = await db.execute(
        select(Category)
        .where(*conditions)
        .order_by(Category.type, Category.parent_name, Category.sort, Category.created_at)
    )
    return list(result.scalars().all())


async def create_category(
    db: AsyncSession,
    user_id: int,
    payload: CategoryCreate,
) -> Category:
    parent_name = payload.parent_name.strip()
    name = payload.name.strip()
    exists = await db.scalar(
        select(Category.id).where(
            Category.user_id == user_id,
            Category.ledger_id == payload.ledger_id,
            Category.type == CategoryType(payload.type),
            Category.parent_name == parent_name,
            Category.name == name,
        )
    )
    if exists is not None:
        raise ValueError("同名分类已存在")
    category = Category(
        user_id=user_id,
        ledger_id=payload.ledger_id,
        type=CategoryType(payload.type),
        parent_name=parent_name,
        name=name,
        icon=payload.icon,
        sort=payload.sort,
    )
    db.add(category)
    await db.flush()
    return category


async def get_category(
    db: AsyncSession,
    category_id: int,
    user_id: int,
) -> Category | None:
    result = await db.execute(
        select(Category).where(
            Category.id == category_id,
            Category.user_id == user_id,
        )
    )
    return result.scalar_one_or_none()


async def update_category(
    db: AsyncSession,
    category: Category,
    payload: CategoryUpdate,
) -> Category:
    old_name = category.name
    changes = payload.model_dump(exclude_unset=True)
    for field, value in changes.items():
        if isinstance(value, str):
            value = value.strip()
        setattr(category, field, value)
    if not category.parent_name and category.name != old_name:
        children = await db.execute(
            select(Category).where(
                Category.user_id == category.user_id,
                Category.ledger_id == category.ledger_id,
                Category.type == category.type,
                Category.parent_name == old_name,
            )
        )
        for child in children.scalars().all():
            child.parent_name = category.name
    await db.flush()
    return category


async def delete_category(db: AsyncSession, category: Category) -> None:
    if not category.parent_name:
        children = await db.execute(
            select(Category).where(
                Category.user_id == category.user_id,
                Category.ledger_id == category.ledger_id,
                Category.type == category.type,
                Category.parent_name == category.name,
            )
        )
        for child in children.scalars().all():
            await db.delete(child)
    await db.delete(category)
    await db.flush()
