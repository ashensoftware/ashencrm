import tempfile
import unittest
from pathlib import Path

from backend.database.db import Database
from backend.scraper.models import Prospect


class TestDatabaseExports(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory(ignore_cleanup_errors=True)
        root = Path(self._tmp.name)
        self.db_path = root / "test_exports.db"
        self.db = Database(db_path=self.db_path)
        self.json_path = root / "test_export.json"
        self.csv_path = root / "test_export.csv"

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
        self._tmp.cleanup()

    def test_export_json_and_csv(self):
        self.db.export_json(filepath=self.json_path)
        self.db.export_csv(filepath=self.csv_path)

        self.assertTrue(self.json_path.exists())
        self.assertTrue(self.csv_path.exists())


if __name__ == "__main__":
    unittest.main()

