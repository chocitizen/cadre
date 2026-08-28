import os
import json
import hashlib
from types import SimpleNamespace
from pathlib import Path
from tempfile import TemporaryDirectory

test_database_directory = TemporaryDirectory()
test_database_path = Path(test_database_directory.name) / "cadre.db"
os.environ["CADRE_DATABASE_URL"] = f"sqlite:///{test_database_path}"
os.environ["CADRE_OPERATIONS_STATE_PATH"] = str(Path(test_database_directory.name) / "operations.json")
api_tokens = {
    role: hashlib.sha256(f"cadre-test-token:{role}".encode()).hexdigest()
    for role in ("mission_control", "al", "invictus", "porter", "griot", "sentinel")
}
os.environ["CADRE_API_TOKENS_JSON"] = json.dumps(api_tokens)

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_core_crud():
    with TestClient(app) as client:
        mission_control = {"Authorization": f"Bearer {api_tokens['mission_control']}"}
        root = client.get("/")
        assert root.status_code == 200
        assert root.json()["system"] == "CADRE"

        docs = client.get("/docs")
        assert docs.status_code == 200

        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        assert client.get("/api/v1/operations/state").status_code == 401
        operations = client.get("/api/v1/operations/state", headers=mission_control)
        assert operations.status_code == 200
        assert operations.json()["system"] == "DEGRADED"
        assert operations.json()["deployment"] == "QUEUED"

        doctrine = client.get("/api/v1/doctrine", headers=mission_control)
        assert doctrine.status_code == 200
        assert any(x["key"] == "sovereignty" for x in doctrine.json())

        project = client.post("/api/v1/projects", headers=mission_control, json={
            "slug": "cadre-test",
            "name": "CADRE Test Project",
            "description": "M1 validation project"
        })
        assert project.status_code == 201
        project_id = project.json()["id"]

        brief = client.post("/api/v1/command-briefs", headers=mission_control, json={
            "project_id": project_id,
            "title": "Validate M1",
            "objective": "Prove project and command-brief persistence",
            "expected_outputs": ["validated core"],
            "validation_criteria": ["HTTP 201", "record persists"]
        })
        assert brief.status_code == 201
        assert brief.json()["project_id"] == project_id

        projects = client.get("/api/v1/projects", headers=mission_control)
        assert projects.status_code == 200
        assert any(item["id"] == project_id for item in projects.json())

        briefs = client.get("/api/v1/command-briefs", headers=mission_control)
        assert briefs.status_code == 200
        assert any(
            item["id"] == brief.json()["id"] and item["project_id"] == project_id
            for item in briefs.json()
        )


def test_api_roles_and_resource_bounds():
    with TestClient(app) as client:
        reader = {"Authorization": f"Bearer {api_tokens['invictus']}"}
        writer = {"Authorization": f"Bearer {api_tokens['al']}"}

        assert client.get("/api/v1/projects", headers=reader).status_code == 200
        denied = client.post(
            "/api/v1/projects",
            headers=reader,
            json={"slug": "forbidden", "name": "Forbidden"},
        )
        assert denied.status_code == 403

        oversized_field = client.post(
            "/api/v1/projects",
            headers=writer,
            json={"slug": "oversized", "name": "Oversized", "description": "x" * 50_001},
        )
        assert oversized_field.status_code == 422

        oversized_body = client.post(
            "/api/v1/projects",
            headers=writer,
            content=b"x" * 1_048_577,
        )
        assert oversized_body.status_code == 413

        def chunked_body():
            yield b"x" * 700_000
            yield b"x" * 700_000

        chunked = client.post("/api/v1/projects", headers=writer, content=chunked_body())
        assert chunked.status_code == 413
        assert client.get("/api/v1/projects?limit=101", headers=reader).status_code == 422
        assert client.get("/api/v1/projects?limit=1", headers=reader).status_code == 200


def test_duplicate_api_tokens_fail_closed(monkeypatch):
    from app.core import security

    duplicated = hashlib.sha256(b"duplicate-token").hexdigest()
    monkeypatch.setattr(
        security,
        "get_settings",
        lambda: SimpleNamespace(api_tokens_json=json.dumps({"invictus": duplicated, "mission_control": duplicated})),
    )
    with TestClient(app) as client:
        response = client.post(
            "/api/v1/projects",
            headers={"Authorization": f"Bearer {duplicated}"},
            json={"slug": "duplicate-identity", "name": "Duplicate Identity"},
        )
    assert response.status_code == 503
