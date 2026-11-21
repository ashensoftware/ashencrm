import pytest

from backend.domain.prospect import Prospect, ProspectStatus


@pytest.fixture
def repo(prospect_repo):
    return prospect_repo

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


def test_exists_by_name_and_address(repo):
    p = Prospect(name="Dup Check", category="cafe", address="Calle 1 #2")
    assert repo.exists_by_name_and_address("Dup Check", "Calle 1 #2") is False
    assert repo.insert_prospect(p) is True
    assert repo.exists_by_name_and_address("Dup Check", "Calle 1 #2") is True
    assert repo.exists_by_name_and_address("Dup Check", "Otra") is False


def test_delete_prospect_by_id(repo):
    p = Prospect(name="To Delete", category="cafe", address="X")
    assert repo.insert_prospect(p) is True
    rows = repo.get_prospects()
    pid = rows[0].id
    assert pid is not None
    assert repo.delete_prospect_by_id(pid) is True
    assert repo.delete_prospect_by_id(pid) is False
    assert len(repo.get_prospects()) == 0


def test_update_status(repo):
    p = Prospect(name="Test Update", category="otros", address="123")
    repo.insert_prospect(p)
    
    repo.update_status("Test Update", "123", ProspectStatus.WAITING)
    
    prospects = repo.get_prospects()
    assert prospects[0].status == ProspectStatus.WAITING.value
