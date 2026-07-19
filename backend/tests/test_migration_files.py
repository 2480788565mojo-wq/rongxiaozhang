import ast
from pathlib import Path


def test_initial_migration_is_complete_and_valid_python():
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260715_0001_initial_schema.py"
    )
    source = migration.read_text(encoding="utf-8")
    ast.parse(source)
    expected_tables = {
        "users",
        "ledgers",
        "ledger_members",
        "accounts",
        "categories",
        "bills",
        "bill_shares",
        "budgets",
        "insights",
        "chat_history",
    }
    for table in expected_tables:
        assert f'op.create_table(\n        "{table}"' in source


def test_alembic_environment_files_exist():
    backend = Path(__file__).parents[1]
    assert (backend / "alembic.ini").is_file()
    assert (backend / "alembic" / "env.py").is_file()
    assert (backend / "alembic" / "script.py.mako").is_file()


def test_bill_confirmation_idempotency_migration_is_valid():
    migration = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20260719_0002_bill_confirmation_session.py"
    )
    source = migration.read_text(encoding="utf-8")
    ast.parse(source)
    assert 'down_revision: str | None = "20260715_0001"' in source
    assert "confirmation_session_id" in source
    assert "uk_bill_creator_ledger_confirmation_session" in source
