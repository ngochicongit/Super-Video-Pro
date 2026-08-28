from newsvid.api import create_app
from fastapi.testclient import TestClient

def test_projects_and_service_api(tmp_path):
    client = TestClient(create_app(tmp_path))
    made = client.post("/projects", json={"name": "API demo"})
    assert made.status_code == 201
    project_id = made.json()["id"]
    assert client.get("/projects").status_code == 200
    assert client.get(f"/projects/{project_id}").status_code == 200
    assert client.post(f"/projects/{project_id}/render").json()["status"] == "accepted"
