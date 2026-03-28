import unittest

from backend.outreach.whatsapp import WhatsAppAutomation
from backend.outreach.message_builder import build_whatsapp_message
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


if __name__ == "__main__":
    unittest.main()

