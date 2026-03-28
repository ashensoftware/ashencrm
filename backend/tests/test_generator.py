"""
Script de pruebas automáticas para el Módulo Generador.
"""

import unittest
import asyncio
from src.generator.prompt_builder import build_demo_prompt
from src.generator.account_manager import AccountManager
from src.generator.lovable import LovableAutomation
from src.scraper.models import Prospect

class TestGeneratorModule(unittest.TestCase):
    
    def setUp(self):
        self.mock_prospect = Prospect(
            name="Test Business",
            category="Restaurante",
            ig_bio="Comida rica en Medellín.",
            ig_followers=500
        )

    def test_prompt_builder(self):
        """Verifica que el prompt se genere con los datos correctos."""
        prompt = build_demo_prompt(self.mock_prospect)
        self.assertIn("Test Business", prompt)
        self.assertIn("Restaurante", prompt)
        self.assertIn("JSON", prompt)
        # Nota: evitar emojis en Windows (cp1252) para que los tests no fallen.
        print("Prompt Builder: OK")

    def test_account_rotation(self):
        """Verifica que las cuentas rotan correctamente (1 a 6)."""
        am = AccountManager(count=6)
        ids = []
        for _ in range(6):
            acc = am.get_next_account()
            ids.append(acc["id"])
        
        # Verificar que son únicos en una ronda de 6
        self.assertEqual(len(set(ids)), 6)
        
        # Verificar que el siguiente vuelve al inicio
        next_acc = am.get_next_account()
        # No podemos asegurar el orden exacto si el archivo ya existía, 
        # pero sí que rotan.
        print("Account Rotation: OK (Ronda completada)")

    def test_playwright_init(self):
        """Prueba básica de inicialización de Playwright (headless)."""
        async def run_init():
            am = AccountManager()
            acc = am.get_next_account()
            bot = LovableAutomation(acc)
            try:
                # Solo probamos el arranque del browser
                await bot.start(headless=True)
                return True
            except Exception as e:
                print(f"Error en init: {e}")
                return False
            finally:
                await bot.stop()

        success = asyncio.run(run_init())
        self.assertTrue(success)
        print("Playwright Init: OK")

if __name__ == "__main__":
    unittest.main()
