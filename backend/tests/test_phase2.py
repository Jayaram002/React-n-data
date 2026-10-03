import io
import pytest
from PIL import Image
import pandas as pd
from fastapi.testclient import TestClient

def get_auth_headers(client: TestClient, email: str, role: str = "contributor"):
    client.post("/api/v1/auth/register", json={
        "email": email,
        "password": "password123",
        "role": role,
        "display_name": "TestUser"
    })
    login_res = client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
    token = login_res.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

def create_dummy_image(color=(255, 0, 0), size=(100, 100)) -> bytes:
    img = Image.new("RGB", size, color=color)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

def test_image_upload_and_preview(client: TestClient):
    headers = get_auth_headers(client, "artist1@example.com", "contributor")
    image_bytes = create_dummy_image(color=(50, 100, 150), size=(200, 150))

    files = {"file": ("test_art.png", image_bytes, "image/png")}
    data = {
        "title": "Cosmic Nebulae Image",
        "description": "High resolution astronomical rendering",
        "ai_training_allowed": "true",
        "consent_agreed": "true",
        "consent_version": "1.0"
    }

    response = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    assert response.status_code == 201
    upload = response.json()
    assert upload["title"] == "Cosmic Nebulae Image"
    assert upload["status"] in ["uploaded", "analyzed"]
    
    file_info = upload["file_info"]
    assert file_info["data_type"] == "image"
    assert file_info["width"] == 200
    assert file_info["height"] == 150
    assert file_info["phash"] is not None
    assert len(file_info["phash"]) > 0

    # Test preview endpoint
    preview_res = client.get(f"/api/v1/uploads/{upload['id']}/preview", headers=headers)
    assert preview_res.status_code == 200
    assert preview_res.headers["content-type"] == "image/jpeg"

def test_duplicate_image_detection(client: TestClient):
    headers1 = get_auth_headers(client, "user1@example.com", "contributor")
    headers2 = get_auth_headers(client, "user2@example.com", "contributor")

    image_bytes = create_dummy_image(color=(120, 200, 80), size=(128, 128))

    # User 1 uploads image
    data1 = {
        "title": "Original Image",
        "description": "First upload by user 1",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }
    res1 = client.post("/api/v1/uploads", headers=headers1, data=data1, files={"file": ("img1.png", image_bytes, "image/png")})
    assert res1.status_code == 201

    # User 2 uploads exact same image
    data2 = {
        "title": "Duplicate Image",
        "description": "Second upload by user 2",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }
    res2 = client.post("/api/v1/uploads", headers=headers2, data=data2, files={"file": ("img2.png", image_bytes, "image/png")})
    assert res2.status_code == 201
    upload2 = res2.json()
    assert upload2["status"] == "flagged"

def test_tabular_csv_upload_and_preview(client: TestClient):
    headers = get_auth_headers(client, "data_scientist@example.com", "contributor")

    # Create CSV dataset with columns
    df = pd.DataFrame({
        "velocity": [12.5, 15.0, 18.2, 22.1, 25.4, 30.0],
        "temperature": [300.0, 310.5, 320.0, 325.2, 330.1, 340.0],
        "sensor_id": [1, 2, 3, 4, 5, 6],
        "active": [True, True, False, True, True, False]
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    files = {"file": ("physics_sensors.csv", csv_bytes, "text/csv")}
    data = {
        "title": "Physics Sensor Velocity Dataset",
        "description": "Velocity and temperature measurements from mechanics lab",
        "ai_training_allowed": "true",
        "consent_agreed": "true"
    }

    response = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    assert response.status_code == 201
    upload = response.json()
    assert upload["status"] in ["uploaded", "analyzed"]
    
    file_info = upload["file_info"]
    assert file_info["data_type"] == "tabular"
    assert file_info["row_count"] == 6
    assert file_info["content_hash"] is not None
    assert file_info["signature_hash"] is not None
    
    schema = file_info["column_schema"]
    assert len(schema["columns"]) == 4
    col_names = [c["name"] for c in schema["columns"]]
    assert "velocity" in col_names
    assert "temperature" in col_names

    # Check safe preview endpoint
    preview_res = client.get(f"/api/v1/uploads/{upload['id']}/preview", headers=headers)
    assert preview_res.status_code == 200
    preview_json = preview_res.json()
    assert len(preview_json["sample_rows"]) == 5 # First 5 rows

def test_pii_detection_in_tabular_data(client: TestClient):
    headers = get_auth_headers(client, "analyst@example.com", "contributor")

    # Create dataset containing PII emails & phone numbers
    df = pd.DataFrame({
        "customer_id": [101, 102, 103],
        "email": ["alice@company.com", "bob@example.com", "charlie@web.com"],
        "phone": ["(555) 234-5678", "(555) 987-6543", "(555) 345-6789"],
        "score": [88, 92, 79]
    })
    csv_bytes = df.to_csv(index=False).encode("utf-8")

    files = {"file": ("customers_with_pii.csv", csv_bytes, "text/csv")}
    data = {
        "title": "Customer Marketing Leads",
        "description": "Leads dataset with emails and phone numbers",
        "ai_training_allowed": "false",
        "consent_agreed": "true"
    }

    response = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    assert response.status_code == 201
    upload = response.json()
    # Should be flagged due to PII detection
    assert upload["status"] == "flagged"

    # Preview should have masked PII values
    preview_res = client.get(f"/api/v1/uploads/{upload['id']}/preview", headers=headers)
    preview_json = preview_res.json()
    for row in preview_json["sample_rows"]:
        assert "[MASKED_EMAIL]" in row["email"]

def test_consent_declaration_required(client: TestClient):
    headers = get_auth_headers(client, "creator@example.com", "contributor")
    image_bytes = create_dummy_image()

    files = {"file": ("art.png", image_bytes, "image/png")}
    data = {
        "title": "Sample Art",
        "description": "Sample description",
        "ai_training_allowed": "true",
        "consent_agreed": "false" # Not agreed
    }

    response = client.post("/api/v1/uploads", headers=headers, data=data, files=files)
    assert response.status_code == 400
    assert "consent" in response.json()["detail"].lower()
