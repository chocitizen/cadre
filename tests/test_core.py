import os
from pathlib import Path
from tempfile import TemporaryDirectory

test_database_directory = TemporaryDirectory()
test_database_path = Path(test_database_directory.name) / "cadre.db"
os.environ["CADRE_DATABASE_URL"] = f"sqlite:///{test_database_path}"

from fastapi.testclient import TestClient
from app.main import app


def test_health_and_core_crud():
    with TestClient(app) as client:
        root = client.get("/")
        assert root.status_code == 200
        assert root.json()["system"] == "CADRE"

        docs = client.get("/docs")
        assert docs.status_code == 200

        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        doctrine = client.get("/api/v1/doctrine")
        assert doctrine.status_code == 200
        assert any(x["key"] == "sovereignty" for x in doctrine.json())

        project = client.post("/api/v1/projects", json={
            "slug": "cadre-test",
            "name": "CADRE Test Project",
            "description": "M1 validation project"
        })
        assert project.status_code == 201
        project_id = project.json()["id"]

        brief = client.post("/api/v1/command-briefs", json={
            "project_id": project_id,
            "title": "Validate M1",
            "objective": "Prove project and command-brief persistence",
            "expected_outputs": ["validated core"],
            "validation_criteria": ["HTTP 201", "record persists"]
        })
        assert brief.status_code == 201
        assert brief.json()["project_id"] == project_id

        projects = client.get("/api/v1/projects")
        assert projects.status_code == 200
        assert any(item["id"] == project_id for item in projects.json())

        briefs = client.get("/api/v1/command-briefs")
        assert briefs.status_code == 200
        assert any(
            item["id"] == brief.json()["id"] and item["project_id"] == project_id
            for item in briefs.json()
        )
