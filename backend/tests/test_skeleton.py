"""Skeleton health tests — prove the app boots before any detector exists."""
from fastapi.testclient import TestClient

from app.main import create_app

client = TestClient(create_app())


def test_health_ok():
    assert client.get("/health").status_code == 200


def test_analysis_status():
    assert client.get("/api/v1/analysis/status").status_code == 200
