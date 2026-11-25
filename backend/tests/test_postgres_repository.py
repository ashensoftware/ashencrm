"""Comportamiento específico de Postgres: tipos, cola concurrente, pool acotado, consola."""

import threading

import psycopg
import pytest

from backend.domain.prospect import Prospect
from backend.infrastructure.persistence.platform_repository import PlatformRepository
from backend.workers.runner import process_once


def test_timestamps_round_trip_as_iso_strings_with_offset(prospect_repo):
    prospect_repo.insert_prospect(
        Prospect(name="Reloj", category="cafe", address="A", scraped_at="2026-03-31T15:46:15.177830")
    )
    p = prospect_repo.get_prospects()[0]
    # Texto ISO sin zona se lee como hora de Medellín y vuelve con el offset explícito.
    assert p.scraped_at == "2026-03-31T15:46:15.177830-05:00"
    assert p.contacted_at is None
    assert p.is_contacted is False


def test_patch_normalizes_sqlite_shaped_values(prospect_repo):
    prospect_repo.insert_prospect(Prospect(name="Norm", category="cafe", address="B"))
    prospect_repo.update_status("Norm", "B", "contacted", is_contacted=1, contacted_at="")
    p = prospect_repo.get_prospects()[0]
    assert p.status == "contacted"
    assert p.is_contacted is True
    assert p.contacted_at is None


def test_patch_rejects_unknown_columns(prospect_repo):
    prospect_repo.insert_prospect(Prospect(name="Safe", category="cafe", address="C"))
    with pytest.raises(ValueError, match="Columnas desconocidas"):
        prospect_repo.patch_prospect("Safe", "C", {"status = 'x' --": "y"})


def test_name_search_is_case_insensitive(prospect_repo):
    prospect_repo.insert_prospect(Prospect(name="Café Norte", category="cafe", address="D"))
    assert [p.name for p in prospect_repo.get_prospects(name_query="café")] == ["Café Norte"]


def test_null_reviews_count_does_not_break_scoring(prospect_repo):
    prospect_repo.insert_prospect(Prospect(name="Sin reseñas", category="cafe", address="E"))
    prospect_repo.patch_prospect("Sin reseñas", "E", {"reviews_count": None})
    p = prospect_repo.get_prospects()[0]
    assert p.reviews_count is None
    assert prospect_repo.compute_lead_score(p) == 0


def test_app_settings_keep_string_contract(prospect_repo):
    prospect_repo.upsert_app_settings(
        {"default_city": "Medellín", "map_zoom": "12", "whatsapp_templates": '[{"id": "a"}]'}
    )
    raw = prospect_repo.get_app_settings_raw()
    assert raw["default_city"] == "Medellín"
    assert raw["map_zoom"] == "12"
    assert raw["whatsapp_templates"] == '[{"id": "a"}]'
    with prospect_repo._conn() as conn:
        kinds = dict(
            (r["key"], r["t"])
            for r in conn.execute("SELECT key, jsonb_typeof(value) AS t FROM app_settings").fetchall()
        )
    assert kinds == {"default_city": "string", "map_zoom": "string", "whatsapp_templates": "array"}


def test_clients_and_meetings_round_trip(prospect_repo):
    prospect_repo.insert_prospect(Prospect(name="Cliente", category="spa", address="F", latitude=6.2, longitude=-75.5))
    client_id = prospect_repo.create_client_from_prospect_name("Cliente")
    prospect_repo.update_client(
        client_id,
        {"contract_required": 1, "estimated_delivery_at": "", "quote_amount": 1500000},
    )
    client = prospect_repo.get_client(client_id)
    assert client["contract_required"] is True
    assert client["estimated_delivery_at"] is None
    assert client["quote_amount"] == 1500000
    meeting_id = prospect_repo.insert_client_meeting(
        client_id, {"title": "Kickoff", "scheduled_at": "2026-12-01T15:00:00.000Z"}
    )
    meeting = prospect_repo.get_client_meeting(meeting_id)
    assert meeting["scheduled_at"] == "2026-12-01T10:00:00-05:00"
    assert prospect_repo.list_clients_map_markers()[0]["latitude"] == 6.2
    prospect_repo.delete_prospect_by_id(client["prospect_id"])
    assert prospect_repo.get_client(client_id)["prospect_id"] is None


def test_sql_console_write_is_blocked_by_the_database(prospect_repo):
    """Aunque el filtro de texto fallara, la transacción READ ONLY rechaza la escritura."""
    with prospect_repo._readonly_pool_or_main().connection() as conn:
        with pytest.raises(psycopg.errors.ReadOnlySqlTransaction):
            with conn.transaction(force_rollback=True):
                conn.execute("SET TRANSACTION READ ONLY")
                conn.execute("INSERT INTO category_catalog (name, label) VALUES ('x', 'y')")


def test_sql_console_reads_like_patterns(prospect_repo):
    out = prospect_repo.execute_sql_console("SELECT name FROM category_catalog WHERE name LIKE 'caf%'")
    assert out["rows"] == [{"name": "cafe"}]


def test_concurrent_claims_never_share_a_step(platform_repo):
    for i in range(6):
        platform_repo.create_run(
            campaign_id=f"c{i}",
            requested_by="operator",
            idempotency_key=None,
            config={},
            stages=("discover",),
        )
    claimed: list[str] = []
    barrier = threading.Barrier(6)

    def worker(n: int) -> None:
        barrier.wait()
        step = platform_repo.claim_step(f"w{n}", now=2_000_000_000)
        if step:
            claimed.append(step["id"])

    threads = [threading.Thread(target=worker, args=(n,)) for n in range(6)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(claimed) == len(set(claimed))
    assert len(claimed) >= 4  # el pool tiene 4 conexiones; ninguna espera más de 15 s


def test_pool_stays_bounded_after_many_worker_ticks(clean_db):
    store = PlatformRepository(pool=clean_db)
    for _ in range(40):
        assert process_once(store, "idle-worker") is None
    stats = clean_db.get_stats()
    assert stats["pool_size"] <= 4
    assert stats.get("requests_waiting", 0) == 0
    assert stats["pool_available"] == stats["pool_size"]
