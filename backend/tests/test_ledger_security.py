from types import SimpleNamespace

from app.api.v1.ledgers import ledger_to_out
from app.models import LedgerRole, LedgerType


def ledger_with_viewer_role(role: LedgerRole):
    viewer = SimpleNamespace(user_id=7, role=role, user=SimpleNamespace(nickname="用户", avatar_url=None))
    return SimpleNamespace(
        id=1,
        name="共享账本",
        type=LedgerType.SHARED,
        owner_id=7,
        invite_code="safe-code",
        settle_strategy="equal",
        created_at=None,
        members=[viewer],
    )


def test_regular_member_does_not_receive_invite_code():
    output = ledger_to_out(ledger_with_viewer_role(LedgerRole.MEMBER), 7)
    assert output.invite_code is None


def test_owner_receives_invite_code():
    output = ledger_to_out(ledger_with_viewer_role(LedgerRole.OWNER), 7)
    assert output.invite_code == "safe-code"
