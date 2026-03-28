import unittest

from backend.outreach.whatsapp import WhatsAppAutomation
from backend.outreach.message_builder import build_whatsapp_message, render_whatsapp_template
from backend.scraper.models import Prospect


class TestOutreachModule(unittest.TestCase):
    def test_phone_normalization_colombia(self):
        wa = WhatsAppAutomation()
        self.assertEqual(wa._normalize_phone("300 123 4567"), "573001234567")
        self.assertEqual(wa._normalize_phone("+57 300-123-4567"), "573001234567")

    def test_build_send_url_encodes_message(self):
        wa = WhatsAppAutomation()
        url = wa._build_send_url("3001234567", "Hola equipo! Demo: https://x.y")
        self.assertIn("phone=573001234567", url)
        # Debe codificar espacios/signos.
        self.assertIn("Hola%20equipo%21%20Demo%3A%20https%3A%2F%2Fx.y", url)

    def test_message_builder_contains_demo(self):
        p = Prospect(name="Negocio X", category="cafe", demo_url="https://demo.example")
        msg = build_whatsapp_message(p)
        self.assertIn("Negocio X", msg)
        self.assertIn("https://demo.example", msg)

    def test_render_whatsapp_template_placeholders(self):
        p = Prospect(
            name="Café Norte",
            category="cafe",
            city="Medellín",
            address="Calle 10",
            demo_url="https://demo.example/x",
            ig_followers=1200,
            instagram_handle="@cafenorte",
            rating=4.5,
            reviews_count=88,
        )
        tpl = "Hola {first_name} — {name} en {city}. IG {instagram_handle}, {followers} seguidores. Demo: {demo_url}"
        out = render_whatsapp_template(tpl, p)
        self.assertIn("Café", out)
        self.assertIn("Medellín", out)
        self.assertIn("@cafenorte", out)
        self.assertIn("1200", out)
        self.assertIn("https://demo.example/x", out)


if __name__ == "__main__":
    unittest.main()

