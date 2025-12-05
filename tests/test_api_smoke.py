from fastapi.testclient import TestClient
from app.backend.main import app

client = TestClient(app)

def test_read_root():
    """Sprawdź czy główny endpoint działa"""
    response = client.get("/")
    assert response.status_code == 200

def test_health_check():
    """Sprawdź endpoint health check"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}
