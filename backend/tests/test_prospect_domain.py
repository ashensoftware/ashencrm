"""Cobertura de métodos de dominio Prospect."""

import json

from backend.domain.prospect import Prospect, ProspectStatus


def test_post_init_sets_scraped_at_when_empty():
    p = Prospect(name="a", category="c", scraped_at="")
    assert p.scraped_at


def test_post_init_preserves_scraped_at():
    p = Prospect(name="a", category="c", scraped_at="2020-01-01T00:00:00")
    assert p.scraped_at == "2020-01-01T00:00:00"


def test_has_existing_website_false():
    p = Prospect(name="a", category="c", website="", ig_website="")
    assert p.has_existing_website() is False


def test_has_existing_website_from_ig():
    p = Prospect(name="a", category="c", ig_website="https://x.test")
    assert p.has_existing_website() is True


def test_get_best_phone_chain():
    assert Prospect(name="a", category="c", phone="1", ig_phone="2").get_best_phone() == "1"
    assert Prospect(name="a", category="c", phone="", ig_phone="2").get_best_phone() == "2"
    assert Prospect(name="a", category="c", phone="", ig_phone="").get_best_phone() == ""


def test_get_best_contact():
    p = Prospect(
        name="a",
        category="c",
        phone="",
        ig_phone="99",
        ig_email="e@test",
        instagram_url="https://ig/x",
    )
    assert p.get_best_contact() == {
        "phone": "99",
        "email": "e@test",
        "instagram": "https://ig/x",
    }


def test_to_json_roundtrip_keys():
    p = Prospect(name="n", category="cat", id=3, status=ProspectStatus.SCRAPED.value)
    data = json.loads(p.to_json())
    assert data["name"] == "n" and data["category"] == "cat" and data["id"] == 3
