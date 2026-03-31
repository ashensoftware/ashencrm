"""App settings: env defaults merged with SQLite overrides."""

from __future__ import annotations

import json
from typing import Any

from backend.config.settings import settings

SETTING_KEYS = frozenset(
    {
        "default_city",
        "default_scrape_limit",
        "map_center_lat",
        "map_center_lng",
        "map_zoom",
        "ig_min_delay",
        "ig_max_delay",
        "max_results_per_category",
        "scraper_headless",
        "whatsapp_min_delay",
        "whatsapp_max_delay",
        "whatsapp_max_daily",
        "whatsapp_phone",
        "lovable_timeout",
        "lovable_headless",
        "whatsapp_templates",
        "client_preferences",
    }
)

_DEFAULT_CLIENT_PREFERENCES: dict[str, Any] = {
    "default_currency": "COP",
    "quote_footer_note": "",
}

_DEFAULT_TEMPLATES: list[dict[str, str]] = [
    {
        "id": "gpt_hero",
        "name": "GPT Hero inicial",
        "kind": "gpt",
        "audience": "ia",
        "template": (
            "Actúa como Ashen Software, una empresa de desarrollo web enfocada en crear landing pages visuales para negocios locales.\n\n"
            "Necesito generar ÚNICAMENTE la primera sección (hero / vista inicial) para:\n"
            "- Negocio: {name}\n"
            "- Categoría: {category}\n"
            "- Dirección: {address}\n"
            "- Instagram: {instagram}\n"
            "- Google Maps: {maps_url}\n\n"
            "IMPORTANTE:\n"
            "- SOLO generar la landing inicial (hero).\n"
            "- NO crear más secciones.\n"
            "- NO agregar funcionalidades adicionales.\n"
            "- Debe ser ideal para screenshot visual.\n\n"
            "La hero debe incluir:\n"
            "1) Fondo visual impactante acorde al negocio.\n"
            "2) Título principal claro con el nombre del negocio.\n"
            "3) Subtítulo corto orientado a propuesta de valor.\n"
            "4) 2 botones visibles (solo visuales): 'Pedir por WhatsApp' y 'Ver Menú/Servicios'.\n"
            "5) Estilo moderno, limpio, profesional, con jerarquía tipográfica clara.\n"
            "6) Línea breve inferior con ubicación y horario.\n\n"
            "Entrega:\n"
            "1) Copy final del hero (H1, subtítulo, línea inferior, CTA1, CTA2)\n"
            "2) Dirección visual (paleta, tipografía, estilo fondo/botones)\n"
            "3) Prompt final para Lovable (bloque único listo para copiar)."
        ),
    },
    {
        "id": "first_contact",
        "name": "Primer contacto (envío con demo)",
        "kind": "whatsapp",
        "audience": "cliente",
        "template": (
            "Hola {first_name}, vimos *{name}* en {city} ({category}). "
            "Tienen ~{followers} seguidores en IG {instagram_handle}. "
            "Les dejamos una demo: {demo_url}\n"
            "¿Les interesa una llamada de 10 min?"
        ),
    },
    {
        "id": "demo_followup",
        "name": "Seguimiento demo",
        "kind": "whatsapp",
        "audience": "cliente",
        "template": (
            "Hola equipo de {name}, ¿qué tal? "
            "¿Pudieron ver la demo? {demo_url}\n"
            "Cualquier duda, estamos en {phone}."
        ),
    },
    {
        "id": "direct_offer",
        "name": "Oferta directa",
        "kind": "whatsapp",
        "audience": "cliente",
        "template": (
            "Hola {name}, ayudamos a negocios como el suyo en {category} ({address}). "
            "Rating {rating}★ ({reviews_count} reseñas). "
            "¿Les gustaría una propuesta sin compromiso?"
        ),
    },
]

DEFAULT_WHATSAPP_TEMPLATES_JSON = json.dumps(_DEFAULT_TEMPLATES, ensure_ascii=False)


def _defaults_as_strings() -> dict[str, str]:
    s = settings
    return {
        "default_city": s.scraper.city,
        "default_scrape_limit": "20",
        "map_center_lat": "6.2442",
        "map_center_lng": "-75.5812",
        "map_zoom": "13",
        "ig_min_delay": str(s.scraper.ig_min_delay),
        "ig_max_delay": str(s.scraper.ig_max_delay),
        "max_results_per_category": str(s.scraper.max_results_per_category),
        "scraper_headless": "true" if s.scraper.headless else "false",
        "whatsapp_min_delay": str(s.outreach.whatsapp_min_delay),
        "whatsapp_max_delay": str(s.outreach.whatsapp_max_delay),
        "whatsapp_max_daily": str(s.outreach.whatsapp_max_daily),
        "whatsapp_phone": s.outreach.whatsapp_phone,
        "lovable_timeout": str(s.generator.lovable_timeout),
        "lovable_headless": "true" if s.generator.lovable_headless else "false",
        "whatsapp_templates": DEFAULT_WHATSAPP_TEMPLATES_JSON,
        "client_preferences": json.dumps(_DEFAULT_CLIENT_PREFERENCES, ensure_ascii=False),
    }


def _merged_strings(db) -> dict[str, str]:
    base = _defaults_as_strings()
    base.update(db.get_app_settings_raw())
    return base


def _parse_bool(v: str) -> bool:
    return str(v).lower() in ("1", "true", "yes", "on")


def typed_public_settings(db) -> dict[str, Any]:
    m = _merged_strings(db)
    templates_raw = m.get("whatsapp_templates") or DEFAULT_WHATSAPP_TEMPLATES_JSON
    try:
        templates = json.loads(templates_raw)
        if not isinstance(templates, list):
            templates = json.loads(DEFAULT_WHATSAPP_TEMPLATES_JSON)
    except json.JSONDecodeError:
        templates = json.loads(DEFAULT_WHATSAPP_TEMPLATES_JSON)

    return {
        "default_city": m["default_city"],
        "default_scrape_limit": int(float(m["default_scrape_limit"])),
        "map_center_lat": float(m["map_center_lat"]),
        "map_center_lng": float(m["map_center_lng"]),
        "map_zoom": int(float(m["map_zoom"])),
        "ig_min_delay": float(m["ig_min_delay"]),
        "ig_max_delay": float(m["ig_max_delay"]),
        "max_results_per_category": int(float(m["max_results_per_category"])),
        "scraper_headless": _parse_bool(m["scraper_headless"]),
        "whatsapp_min_delay": int(float(m["whatsapp_min_delay"])),
        "whatsapp_max_delay": int(float(m["whatsapp_max_delay"])),
        "whatsapp_max_daily": int(float(m["whatsapp_max_daily"])),
        "whatsapp_phone": m["whatsapp_phone"],
        "lovable_timeout": int(float(m["lovable_timeout"])),
        "lovable_headless": _parse_bool(m["lovable_headless"]),
        "whatsapp_templates": templates,
        "client_preferences": _parse_client_preferences(m.get("client_preferences")),
    }


def _parse_client_preferences(raw: str | None) -> dict[str, Any]:
    if not raw or not str(raw).strip():
        return dict(_DEFAULT_CLIENT_PREFERENCES)
    try:
        d = json.loads(raw)
        if not isinstance(d, dict):
            return dict(_DEFAULT_CLIENT_PREFERENCES)
        out = dict(_DEFAULT_CLIENT_PREFERENCES)
        out.update({k: v for k, v in d.items() if k in _DEFAULT_CLIENT_PREFERENCES})
        return out
    except json.JSONDecodeError:
        return dict(_DEFAULT_CLIENT_PREFERENCES)


def patch_body_to_storage(body: dict[str, Any]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in body.items():
        if k not in SETTING_KEYS:
            continue
        if k == "whatsapp_templates":
            if not isinstance(v, list):
                raise ValueError("whatsapp_templates debe ser un arreglo")
            out[k] = json.dumps(v, ensure_ascii=False)
        elif k == "client_preferences":
            if not isinstance(v, dict):
                raise ValueError("client_preferences debe ser un objeto")
            merged = dict(_DEFAULT_CLIENT_PREFERENCES)
            merged.update({kk: vv for kk, vv in v.items() if kk in _DEFAULT_CLIENT_PREFERENCES})
            out[k] = json.dumps(merged, ensure_ascii=False)
        elif isinstance(v, bool):
            out[k] = "true" if v else "false"
        else:
            out[k] = str(v).strip()
    return out


def scrape_runtime_options(db) -> dict[str, Any]:
    t = typed_public_settings(db)
    return {
        "scraper_headless": t["scraper_headless"],
        "default_city": t["default_city"],
        "default_scrape_limit": t["default_scrape_limit"],
    }
