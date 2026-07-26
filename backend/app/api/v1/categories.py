from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, DBSession, require_ledger_access
from app.models import CategoryType
from app.schemas.category import CategoryCreate, CategoryOut, CategoryUpdate
from app.services.category_service import (
    create_category,
    delete_category,
    get_category,
    list_categories,
    update_category,
)


router = APIRouter()


@router.get("", response_model=list[CategoryOut])
async def read_categories(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int = Query(default=1, gt=0),
    type: str | None = Query(default=None, pattern="^(expense|income)$"),
) -> list[CategoryOut]:
    await require_ledger_access(db, ledger_id, user.id)
    category_type = CategoryType(type) if type else None
    categories = await list_categories(db, user.id, ledger_id, category_type)
    return [CategoryOut.model_validate(category) for category in categories]


@router.post("", response_model=CategoryOut, status_code=status.HTTP_201_CREATED)
async def add_category(
    payload: CategoryCreate,
    user: CurrentUser,
    db: DBSession,
) -> CategoryOut:
    await require_ledger_access(db, payload.ledger_id, user.id)
    try:
        category = await create_category(db, user.id, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await db.commit()
    return CategoryOut.model_validate(category)


@router.put("/{category_id}", response_model=CategoryOut)
async def edit_category(
    category_id: int,
    payload: CategoryUpdate,
    user: CurrentUser,
    db: DBSession,
) -> CategoryOut:
    category = await get_category(db, category_id, user.id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "分类不存在")
    await update_category(db, category, payload)
    await db.commit()
    return CategoryOut.model_validate(category)


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_category(
    category_id: int,
    user: CurrentUser,
    db: DBSession,
) -> Response:
    category = await get_category(db, category_id, user.id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "分类不存在")
    await delete_category(db, category)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
