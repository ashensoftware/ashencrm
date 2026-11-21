"""SQL console helper on ProspectRepository."""

import pytest

from backend.infrastructure.persistence.prospect_repository import ProspectRepository


@pytest.fixture()
def repo(prospect_repo):
    return prospect_repo


def test_execute_sql_console_select(repo: ProspectRepository):
    out = repo.execute_sql_console("SELECT 1 AS n")
    assert out["kind"] == "select"
    assert out["columns"] == ["n"]
    assert out["rows"] == [{"n": 1}]
    assert out["truncated"] is False


def test_execute_sql_console_select_after_line_comments(repo: ProspectRepository):
    sql = """-- Vista previa
-- otra línea
SELECT 2 AS x"""
    out = repo.execute_sql_console(sql)
    assert out["kind"] == "select"
    assert out["rows"] == [{"x": 2}]


def test_execute_sql_console_rejects_attach(repo: ProspectRepository):
    with pytest.raises(ValueError, match="Sentencia rechazada"):
        repo.execute_sql_console("ATTACH DATABASE 'x.db' AS x")


@pytest.mark.parametrize(
    "sql",
    [
        "CREATE TABLE t (id INTEGER)",
        "INSERT INTO prospects (name, category) VALUES ('x', 'y')",
        "UPDATE prospects SET notes = 'x'",
        "DELETE FROM prospects",
        "DROP TABLE prospects",
        "ALTER TABLE prospects ADD COLUMN extra TEXT",
        "PRAGMA writable_schema = ON",
        "VACUUM",
        "DETACH DATABASE main",
        "REPLACE INTO prospects (name, category) VALUES ('x', 'y')",
    ],
)
def test_execute_sql_console_rejects_writes(repo: ProspectRepository, sql: str):
    with pytest.raises(ValueError, match="Sentencia rechazada"):
        repo.execute_sql_console(sql)


def test_execute_sql_console_allows_delete_inside_a_string_literal(repo: ProspectRepository):
    out = repo.execute_sql_console("SELECT 'DELETE' AS verb")
    assert out["kind"] == "select"
    assert out["rows"] == [{"verb": "DELETE"}]


def test_execute_sql_console_explain_select(repo: ProspectRepository):
    out = repo.execute_sql_console("EXPLAIN SELECT 1")
    assert out["kind"] == "select"
    assert out["rows"]


def test_rejected_write_is_not_committed(repo: ProspectRepository):
    with pytest.raises(ValueError, match="Sentencia rechazada"):
        repo.execute_sql_console("CREATE TABLE leaked (id INTEGER)")
    out = repo.execute_sql_console(
        "SELECT table_name FROM information_schema.tables WHERE table_name = 'leaked'"
    )
    assert out["rows"] == []


def test_execute_sql_console_rejects_multiple_statements(repo: ProspectRepository):
    with pytest.raises(ValueError, match="Solo una sentencia"):
        repo.execute_sql_console("SELECT 1; SELECT 2")
