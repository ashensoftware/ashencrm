import unittest
import time
from pathlib import Path

from src.database.db import Database
from src.scraper.models import Prospect


class TestDatabaseExports(unittest.TestCase):
    def setUp(self):
        self.db_path = Path("data/test_exports.db")
        if self.db_path.exists():
            self.db_path.unlink()
        self.db = Database(db_path=self.db_path)

        self.db.insert_prospect(
            Prospect(
                name="Export Test",
                category="cafe",
                address="Calle 1",
                city="Medellín",
                phone="3001234567",
            )
        )

    def tearDown(self):
        # En Windows puede quedar un lock breve; reintentar cleanup.
        for _ in range(10):
            try:
                if self.db_path.exists():
                    self.db_path.unlink()
                break
            except PermissionError:
                time.sleep(0.1)

    def test_export_json_and_csv(self):
        json_path = Path("data/test_export.json")
        csv_path = Path("data/test_export.csv")

        if json_path.exists():
            json_path.unlink()
        if csv_path.exists():
            csv_path.unlink()

        self.db.export_json(filepath=json_path)
        self.db.export_csv(filepath=csv_path)

        self.assertTrue(json_path.exists())
        self.assertTrue(csv_path.exists())


if __name__ == "__main__":
    unittest.main()

