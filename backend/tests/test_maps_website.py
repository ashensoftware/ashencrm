"""Tests for Maps website extraction helpers."""

from backend.core.maps_website import (
    unwrap_google_nav_href,
    website_plausible_for_business,
)


def test_unwrap_google_nav_href():
    wrapped = "https://www.google.com/url?q=https%3A%2F%2Fexample.com%2Ffoo&sa=D"
    assert unwrap_google_nav_href(wrapped).startswith("https://example.com")


def test_plausible_agendapro_wrong_business():
    bad = "https://barberiarand.site.agendapro.com/co/sucursal/105283"
    assert website_plausible_for_business(bad, "Go Barber Shop") is False


def test_plausible_own_domain():
    ok = "https://gobarbershop.co/"
    assert website_plausible_for_business(ok, "Go Barber Shop") is True


def test_plausible_short_name_skips_strict():
    assert website_plausible_for_business("https://x.com/a", "Ab") is True
