"""SQL console helper on ProspectRepository."""

import tempfile
from pathlib import Path

import pytest

from backend.infrastructure.persistence.prospect_repository import ProspectRepository


@pytest.fixture()
def repo():
    # ignore_cleanup_errors: Windows puede retener el lock del .db un instante tras cerrar SQLite
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
        db_path = Path(tmp) / "t.db"
        r = ProspectRepository(db_path=db_path)
        yield r


def test_execute_sql_console_select(repo: ProspectRepository):
    out = repo.execute_sql_console("SELECT 1 AS n")
    assert out["kind"] == "select"
    assert out["columns"] == ["n"]
    assert out["rows"] == [{"n": 1}]
    assert out["truncated"] is False


def test_execute_sql_console_rejects_attach(repo: ProspectRepository):
    with pytest.raises(ValueError, match="no está permitida"):
        repo.execute_sql_console("ATTACH DATABASE 'x.db' AS x")


def test_execute_sql_console_mutate(repo: ProspectRepository):
    repo.execute_sql_console("CREATE TABLE t (id INTEGER)")
    out = repo.execute_sql_console("INSERT INTO t (id) VALUES (7)")
    assert out["kind"] == "mutate"
    assert out["rowcount"] == 1


def test_execute_sql_console_rejects_multiple_statements(repo: ProspectRepository):
    with pytest.raises(ValueError, match="Solo una sentencia"):
        repo.execute_sql_console("SELECT 1; SELECT 2")
