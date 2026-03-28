"""
Construcción de mensajes WhatsApp: plantillas desde BD (Administración) + placeholders.
"""

from __future__ import annotations

from backend.domain.prospect import Prospect

# Si no hay BD o plantilla `first_contact`, se usa este texto (mismos placeholders).
_FALLBACK_TEMPLATE = """
Hola, equipo de *{name}*! 👋

He estado siguiendo su trabajo en Instagram y me encanta lo que están haciendo en el sector de *{category}*. 🚀

Sin embargo, he notado que aún no tienen una presencia web optimizada para captar clientes en Google. Me tomé la libertad de diseñarles una propuesta visual de cómo podría verse su nueva página web:

✨ **Ver Demo Personalizada:** {demo_url}

Diseñé esto pensando en la estética minimalista y moderna que su marca merece.

¿Les gustaría que charláramos 5 minutos sobre cómo esto podría ayudarles a escalar sus ventas este mes?

¡Quedo atento! 😊
""".strip()


def render_whatsapp_template(template: str, prospect: Prospect) -> str:
    """
    Sustituye placeholders en el texto. Usa llaves simples: {name}, {city}, etc.

    Placeholders soportados:
        name, first_name, category, city, address, phone, followers,
        instagram, instagram_handle, demo_url, website, rating, reviews_count,
        email, bio, notes, maps_url
    """
    p = prospect
    name = (p.name or "").strip()
    parts = name.split()
    first_name = parts[0] if parts else ""
    website = (p.website or p.ig_website or "").strip()
    bio = (p.ig_bio or "").strip()
    if len(bio) > 320:
        bio = bio[:317] + "..."

    mapping = {
        "name": name,
        "first_name": first_name,
        "category": (p.category or "").strip(),
        "city": (p.city or "").strip(),
        "address": (p.address or "").strip(),
        "phone": (p.get_best_phone() or "").strip(),
        "followers": str(p.ig_followers or 0),
        "instagram": (p.instagram_url or "").strip(),
        "instagram_handle": (p.instagram_handle or "").strip(),
        "demo_url": (p.demo_url or "").strip(),
        "website": website,
        "rating": str(p.rating if p.rating is not None else 0),
        "reviews_count": str(p.reviews_count or 0),
        "email": (p.ig_email or "").strip(),
        "bio": bio,
        "notes": (p.notes or "").strip(),
        "maps_url": (p.maps_url or "").strip(),
    }

    out = template
    for key, val in mapping.items():
        out = out.replace("{" + key + "}", val)
    return out


def build_whatsapp_message(prospect: Prospect, db=None) -> str:
    """
    Mensaje listo para enviar. Usa la plantilla con id `first_contact` desde app_settings
    si existe; si no, la primera plantilla; si falla, plantilla integrada con placeholders.
    """
    template: str | None = None
    if db is not None:
        try:
            from backend.services.app_settings_service import typed_public_settings

            data = typed_public_settings(db)
            templates = data.get("whatsapp_templates") or []
            if isinstance(templates, list):
                tpl = next(
                    (
                        t
                        for t in templates
                        if isinstance(t, dict) and t.get("id") == "first_contact"
                    ),
                    None,
                )
                if tpl is None and templates:
                    first = templates[0]
                    tpl = first if isinstance(first, dict) else None
                if tpl and (tpl.get("template") or "").strip():
                    template = tpl["template"].strip()
        except Exception:
            template = None

    if not template:
        template = _FALLBACK_TEMPLATE

    return render_whatsapp_template(template, prospect)


if __name__ == "__main__":
    mock_p = Prospect(
        name="Café Central",
        category="Cafetería",
        demo_url="https://demo-cafe.lovable.app",
    )
    print("--- MENSAJE PARA WHATSAPP ---")
    print(build_whatsapp_message(mock_p))
