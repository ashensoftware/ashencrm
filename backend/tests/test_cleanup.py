"""Limpiezas D9 y deduplicación con direcciones sucias del scraper."""

import pytest

from backend.domain.cleanup import (
    clean_address,
    extract_google_place_id,
    plausible_reviews_count,
    split_legacy_photo,
)
from backend.domain.prospect import Prospect


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Barbería · Cra. 76 #26-20", "Cra. 76 #26-20"),
        ("Peluquería ·  · Domicilios, Calle 9b sur #79a 221", "Domicilios, Calle 9b sur #79a 221"),
        ("Medellín", "Medellín"),
        (
            "Dog + Cat Vet  4.2Hospital veterinario · Cl. 2 Sur #67 - 250 interior 106Abierto"
            " · Cierra a las 8 p.m. · 316 3208639Indicaciones",
            "Cl. 2 Sur #67 - 250 interior 106",
        ),
        ("Clínica · Cra 76 # 32 D - 22, Cl 32D #11Abierto las 24 horas", "Cra 76 # 32 D - 22, Cl 32D #11"),
        ("Taller ·  · Cra 77 #29-11", "Cra 77 #29-11"),
        ("", ""),
        (None, ""),
    ],
)
def test_clean_address(raw, expected):
    assert clean_address(raw) == expected
    assert clean_address(clean_address(raw)) == expected  # idempotente


def test_place_id_reviews_and_photo_rules():
    url = "https://www.google.com/maps/place/X/data=!4m7!3m6!1s0x0:0x0!8m2!3d6.2!4d-75.5!16s%2Fg%2F1!19sChIJa-b_C123!20m1"
    assert extract_google_place_id(url) == "ChIJa-b_C123"
    assert extract_google_place_id("https://maps.google.com/?q=cafe") is None
    assert plausible_reviews_count(8969) == 8969
    assert plausible_reviews_count(50_001) is None
    assert plausible_reviews_count(None) is None
    assert split_legacy_photo("https://lh5.googleusercontent.com/p/abc") == ("", "https://lh5.googleusercontent.com/p/abc")
    assert split_legacy_photo("data/screenshots/demo.png") == ("data/screenshots/demo.png", None)


def test_rescrape_with_dirty_address_dedupes_and_updates(prospect_repo):
    dirty = "Barbería ·  · Cra. 76 #26-20"
    p = Prospect(
        name="Barbería Uno",
        category="barberia",
        address=dirty,
        reviews_count=120_000,
        maps_url="https://www.google.com/maps/place/x/data=!19sChIJzz9",
        screenshot_path="https://lh5.googleusercontent.com/p/foto",
    )
    assert prospect_repo.insert_prospect(p) is True
    stored = prospect_repo.get_prospects()[0]
    assert stored.address == "Cra. 76 #26-20"
    assert stored.reviews_count is None
    assert stored.screenshot_path == ""
    # Un re-scrape trae la misma dirección sucia: no duplica y las búsquedas casan.
    assert prospect_repo.exists_by_name_and_address(p.name, dirty) is True
    assert prospect_repo.insert_prospect(p) is False
    prospect_repo.update_status(p.name, dirty, "ready")
    assert prospect_repo.get_prospects()[0].status == "ready"
    with prospect_repo._conn() as conn:
        row = conn.execute("SELECT google_place_id, legacy_photo_url FROM prospects").fetchone()
    assert row == {"google_place_id": "ChIJzz9", "legacy_photo_url": "https://lh5.googleusercontent.com/p/foto"}


def test_exact_stored_address_wins_over_cleaned_twin(prospect_repo):
    """Duplicado importado con dirección original: actualizarlo no debe tocar a su gemelo limpio."""
    prospect_repo.insert_prospect(Prospect(name="Gemelo", category="cafe", address="Cra. 1 #2-3"))
    raw = "Cafetería · Cra. 1 #2-3"
    with prospect_repo._conn() as conn:
        conn.execute(
            "INSERT INTO prospects (name, category, address) VALUES ('Gemelo', 'cafe', %s)", (raw,)
        )
    prospect_repo.update_status("Gemelo", raw, "rejected")
    by_address = {p.address: p.status for p in prospect_repo.get_prospects()}
    assert by_address == {"Cra. 1 #2-3": "scraped", raw: "rejected"}
