from unittest.mock import patch

import pytest

from backend.core.google_maps_url import (
    extract_lat_lng_from_text,
    extract_place_name,
    parse_google_maps_link,
    resolve_short_url,
)


def test_extract_place_name():
    u = "https://www.google.com/maps/place/Caf%C3%A9+Test/@6.2,-75.5,17z"
    assert extract_place_name(u) == "Café Test"


def test_extract_place_name_none():
    assert extract_place_name("https://www.google.com/maps/@6,6,15z") is None


def test_extract_place_name_empty_decoded():
    u = "https://www.google.com/maps/place/%20/@6.2,-75.5,17z"
    assert extract_place_name(u) is None


def test_extract_lat_lng_at_format():
    t = "https://www.google.com/maps/place/Foo/@6.2087634,-75.5675859,17z/data=abc"
    assert extract_lat_lng_from_text(t) == pytest.approx((6.2087634, -75.5675859))


def test_extract_lat_lng_at_end_slash():
    t = "https://www.google.com/maps/@-1.5,2.25/"
    assert extract_lat_lng_from_text(t) == pytest.approx((-1.5, 2.25))


def test_extract_lat_lng_fragment_hash():
    t = "https://www.google.com/maps/foo#data=!3d6.1!4d-75.2"
    assert extract_lat_lng_from_text(t) == pytest.approx((6.1, -75.2))


def test_extract_lat_lng_query_q():
    t = "https://www.google.com/maps?q=6.2%2C-75.55"
    assert extract_lat_lng_from_text(t) == pytest.approx((6.2, -75.55))


def test_extract_lat_lng_query_center():
    t = "https://www.google.com/maps?center=1%2C%202"
    assert extract_lat_lng_from_text(t) == pytest.approx((1.0, 2.0))


def test_extract_lat_lng_query_ll():
    t = "https://www.google.com/maps?ll=-3,4"
    assert extract_lat_lng_from_text(t) == pytest.approx((-3.0, 4.0))


def test_extract_lat_lng_query_ignored_when_no_match():
    t = "https://www.google.com/maps?q=notcoords"
    assert extract_lat_lng_from_text(t) is None


def test_extract_lat_lng_3d4d():
    t = "https://www.google.com/maps?data=!3m1!4b1!4m5!3m4!1s0x0:0x0!8m2!3d6.25!4d-75.58"
    r = extract_lat_lng_from_text(t)
    assert r is not None
    assert r[0] == pytest.approx(6.25)
    assert r[1] == pytest.approx(-75.58)


def test_parse_google_maps_link_without_network():
    u = "https://www.google.com/maps/place/Local+Demo/@4.6097102,-74.0817492,15z"
    out = parse_google_maps_link(u)
    assert out["latitude"] == pytest.approx(4.6097102)
    assert out["longitude"] == pytest.approx(-74.0817492)
    assert "Local Demo" in (out.get("suggested_display_name") or "")


def test_parse_prepends_https():
    out = parse_google_maps_link("www.google.com/maps/place/X/@2.0,-3.0,10z")
    assert out["latitude"] == pytest.approx(2.0)
    assert out["longitude"] == pytest.approx(-3.0)


def test_parse_empty_raises():
    with pytest.raises(ValueError, match="Pega"):
        parse_google_maps_link("  ")


def test_parse_bad_scheme_raises():
    with pytest.raises(ValueError, match="La URL debe ser http"):
        parse_google_maps_link("ftp://www.google.com/maps/@1,2,15z")


def test_parse_non_google_host_raises():
    with pytest.raises(ValueError, match="Google Maps"):
        parse_google_maps_link("https://example.com/maps/@1,2,15z")


class _UrlResp:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return "https://www.google.com/maps/place/Resolved/@5.0,-72.0,14z"


@patch("backend.core.google_maps_url.urlopen")
def test_resolve_short_url(mock_open):
    mock_open.return_value = _UrlResp()
    assert "5.0" in resolve_short_url("https://maps.app.goo.gl/abc")


@patch("backend.core.google_maps_url.urlopen")
def test_parse_short_link_resolves(mock_open):
    mock_open.return_value = _UrlResp()
    out = parse_google_maps_link("https://maps.app.goo.gl/short")
    assert out["latitude"] == pytest.approx(5.0)
    assert out["longitude"] == pytest.approx(-72.0)
    assert "Resolved" in (out.get("suggested_display_name") or "")


@patch("backend.core.google_maps_url.urlopen", side_effect=OSError("network down"))
def test_parse_short_link_resolve_fails(_mock_open):
    with pytest.raises(ValueError, match="No se pudo abrir"):
        parse_google_maps_link("https://maps.app.goo.gl/bad")


class _NoCoordResp:
    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def geturl(self):
        return "https://www.google.com/maps/place/OnlyName/"


@patch("backend.core.google_maps_url.urlopen")
def test_parse_resolved_still_no_coords(mock_open):
    mock_open.return_value = _NoCoordResp()
    with pytest.raises(ValueError, match="No se encontraron"):
        parse_google_maps_link("https://maps.app.goo.gl/nocoords")
