"""
Tests básicos para asegurar que los módulos se importan correctamente.
"""
import sys
from pathlib import Path

# Añadir raíz al path
sys.path.append(str(Path(__file__).parent.parent))

def test_imports():
    from backend.scraper.google_maps import GoogleMapsScraper
    from backend.scraper.instagram import InstagramChecker
    from backend.database.db import Database
    from config.settings import settings
    
    db = Database()
    assert db is not None
    assert settings.scraper.city == "Medellín"
    print("✅ Todos los módulos se importan correctamente.")

if __name__ == "__main__":
    test_imports()
