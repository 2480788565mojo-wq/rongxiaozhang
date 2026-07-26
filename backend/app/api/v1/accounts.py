from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, DBSession, require_ledger_access
from app.schemas.account import AccountCreate, AccountOut, AccountUpdate
from app.services.account_service import (
    create_account,
    delete_account,
    get_account,
    list_accounts,
    update_account,
)


router = APIRouter()


@router.get("", response_model=list[AccountOut])
async def read_accounts(
    user: CurrentUser,
    db: DBSession,
    ledger_id: int = Query(default=1, gt=0),
) -> list[AccountOut]:
    await require_ledger_access(db, ledger_id, user.id)
    accounts = await list_accounts(db, user.id, ledger_id)
    return [AccountOut.model_validate(account) for account in accounts]


@router.post("", response_model=AccountOut, status_code=status.HTTP_201_CREATED)
async def add_account(
    payload: AccountCreate,
    user: CurrentUser,
    db: DBSession,
) -> AccountOut:
    await require_ledger_access(db, payload.ledger_id, user.id)
    try:
        account = await create_account(db, user.id, payload)
    except ValueError as exc:
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    await db.commit()
    return AccountOut.model_validate(account)


@router.put("/{account_id}", response_model=AccountOut)
async def edit_account(
    account_id: int,
    payload: AccountUpdate,
    user: CurrentUser,
    db: DBSession,
) -> AccountOut:
    account = await get_account(db, account_id, user.id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账户不存在")
    await update_account(db, account, payload)
    await db.commit()
    return AccountOut.model_validate(account)


@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_account(
    account_id: int,
    user: CurrentUser,
    db: DBSession,
) -> Response:
    account = await get_account(db, account_id, user.id)
    if account is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "账户不存在")
    await delete_account(db, account)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
