import os

import requests


BASE_URL = os.getenv("BASE_URL", "http://localhost:8000")


def test_healthcheck():
    response = requests.get(f"{BASE_URL}/healthcheck", timeout=10)
    assert response.status_code in {200, 503}
    assert "database" in response.json()
    assert "cache" in response.json()


def test_characters_endpoint():
    response = requests.get(f"{BASE_URL}/characters?page=1&limit=5&sort=id", timeout=30)
    assert response.status_code == 200
    payload = response.json()
    assert payload["page"] == 1
    assert payload["limit"] == 5
    assert "items" in payload
