import pytest
from fastapi.testclient import TestClient

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_register_and_login_contributor(client: TestClient):
    # Register contributor
    reg_payload = {
        "email": "contributor@example.com",
        "password": "securepassword123",
        "role": "contributor",
        "display_name": "DataCreator"
    }
    reg_res = client.post("/api/v1/auth/register", json=reg_payload)
    assert reg_res.status_code == 201
    user_data = reg_res.json()
    assert user_data["email"] == "contributor@example.com"
    assert user_data["role"] == "contributor"
    assert user_data["contributor_profile"]["display_name"] == "DataCreator"

    # Login
    login_payload = {
        "email": "contributor@example.com",
        "password": "securepassword123"
    }
    login_res = client.post("/api/v1/auth/login", json=login_payload)
    assert login_res.status_code == 200
    tokens = login_res.json()
    assert "access_token" in tokens
    assert "refresh_token" in tokens

    # Get Me
    headers = {"Authorization": f"Bearer {tokens['access_token']}"}
    me_res = client.get("/api/v1/auth/me", headers=headers)
    assert me_res.status_code == 200
    assert me_res.json()["email"] == "contributor@example.com"

def test_token_refresh(client: TestClient):
    # Register agency
    reg_payload = {
        "email": "agency@example.com",
        "password": "agencypassword123",
        "role": "agency",
        "company_name": "Insight Corp"
    }
    client.post("/api/v1/auth/register", json=reg_payload)

    # Login
    login_res = client.post("/api/v1/auth/login", json={"email": "agency@example.com", "password": "agencypassword123"})
    refresh_token = login_res.json()["refresh_token"]

    # Refresh
    refresh_res = client.post("/api/v1/auth/refresh", json={"refresh_token": refresh_token})
    assert refresh_res.status_code == 200
    new_tokens = refresh_res.json()
    assert "access_token" in new_tokens
    assert "refresh_token" in new_tokens

def test_seeded_categories(client: TestClient):
    response = client.get("/api/v1/categories")
    assert response.status_code == 200
    categories = response.json()
    assert len(categories) >= 11 # 11 seed domains
    domain_names = [c["name"] for c in categories]
    assert "Physics" in domain_names
    assert "Business" in domain_names
    assert "Food" in domain_names

    # Check Physics subcategories
    physics = next(c for c in categories if c["name"] == "Physics")
    assert len(physics["subcategories"]) >= 5
    sub_names = [s["name"] for s in physics["subcategories"]]
    assert "Mechanics" in sub_names
    assert "Quantum" in sub_names
