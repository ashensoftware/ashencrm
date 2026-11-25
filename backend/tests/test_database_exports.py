from backend.scraper.models import Prospect


def test_export_json_and_csv(prospect_repo, tmp_path):
    prospect_repo.insert_prospect(
        Prospect(
            name="Export Test",
            category="cafe",
            address="Calle 1",
            city="Medellín",
            phone="3001234567",
        )
    )
    json_path = tmp_path / "test_export.json"
    csv_path = tmp_path / "test_export.csv"
    prospect_repo.export_json(filepath=json_path)
    prospect_repo.export_csv(filepath=csv_path)
    assert json_path.exists()
    assert csv_path.exists()
    assert "Export Test" in json_path.read_text(encoding="utf-8")
