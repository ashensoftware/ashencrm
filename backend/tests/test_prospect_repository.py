import pytest
from pathlib import Path
from backend.domain.prospect import Prospect, ProspectStatus
from backend.infrastructure.persistence.prospect_repository import ProspectRepository

@pytest.fixture
def repo(tmp_path):
    db_path = tmp_path / "test_prospects.db"
    return ProspectRepository(db_path=db_path)

def test_insert_and_get_prospect(repo):
    p = Prospect(
        name="Test Cafe",
        category="cafe",
        city="Medellin",
        phone="3000000000",
        website="https://example.com"
    )
    assert repo.insert_prospect(p) is True

    # Duplicate should fail
    assert repo.insert_prospect(p) is False

    prospects = repo.get_prospects()
    assert len(prospects) == 1
    assert prospects[0].name == "Test Cafe"
    assert prospects[0].status == ProspectStatus.SCRAPED.value

def test_update_status(repo):
    p = Prospect(name="Test Update", category="otros", address="123")
    repo.insert_prospect(p)
    
    repo.update_status("Test Update", "123", ProspectStatus.WAITING)
    
    prospects = repo.get_prospects()
    assert prospects[0].status == ProspectStatus.WAITING.value
