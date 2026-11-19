import json
import pytest
from app import create_app

@pytest.fixture()
def client(tmp_path):
    app = create_app({"TESTING": True, "API_TOKEN": "test-token", "STATE_FILE": str(tmp_path / "state.json")})
    return app.test_client()

def headers(): return {"X-API-Key": "test-token"}

def create_session(client, label="Bench A"):
    response = client.post("/api/sessions", headers=headers(), json={"label": label, "source": "pytest", "simulated": False})
    assert response.status_code == 201
    return response.get_json()["data"]["id"]

def test_health_is_public(client):
    assert client.get("/api/health").get_json()["data"]["status"] == "healthy"

def test_sensitive_api_requires_token(client):
    assert client.get("/api/sessions").status_code == 401
    assert client.get("/api/sessions", headers=headers()).status_code == 200

def test_sessions_are_isolated(client):
    first, second = create_session(client, "First"), create_session(client, "Second")
    response = client.post(f"/api/sessions/{first}/events", headers=headers(), json={"type": "device.connected", "message": "Authorized device online", "status": "success"})
    assert response.status_code == 201
    assert len(client.get(f"/api/sessions/{first}", headers=headers()).get_json()["data"]["events"]) == 1
    assert client.get(f"/api/sessions/{second}", headers=headers()).get_json()["data"]["events"] == []

def test_telemetry_rejects_sensitive_fields(client):
    session_id = create_session(client)
    response = client.post(f"/api/sessions/{session_id}/telemetry", headers=headers(), json={"deviceId": "esp32", "metrics": {"password": "nope"}})
    assert response.status_code == 422

def test_evidence_is_metadata_only(client):
    session_id = create_session(client)
    response = client.post(f"/api/sessions/{session_id}/evidence", headers=headers(), json={"name": "capture.json", "kind": "telemetry-export", "sizeBytes": 42, "sha256": "a" * 64})
    assert response.status_code == 201
    assert "content" not in response.get_json()["data"]

def test_persistence_and_delete(tmp_path):
    path = tmp_path / "state.json"
    first = create_app({"TESTING": True, "API_TOKEN": "test-token", "STATE_FILE": str(path)}).test_client()
    session_id = create_session(first)
    second = create_app({"TESTING": True, "API_TOKEN": "test-token", "STATE_FILE": str(path)}).test_client()
    assert second.get(f"/api/sessions/{session_id}", headers=headers()).status_code == 200
    assert second.delete(f"/api/sessions/{session_id}", headers=headers()).status_code == 200
    assert json.loads(path.read_text(encoding="utf-8"))["sessions"] == []
