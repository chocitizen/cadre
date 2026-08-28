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
    for role in ("founder", "mission_control", "al", "invictus", "porter", "griot", "sentinel")
}
os.environ["CADRE_API_TOKENS_JSON"] = json.dumps(api_tokens)
os.environ["CADRE_ADMIN_EMAILS"] = "admin@example.com"
os.environ["CADRE_EXPOSE_DEVELOPMENT_TOKENS"] = "true"

from fastapi.testclient import TestClient
from app.main import app


def test_railway_and_responsive_runtime_contracts():
    repository_root = Path(__file__).resolve().parents[1]
    dockerfile = (repository_root / "Dockerfile").read_text()
    index = (repository_root / "app/web/index.html").read_text()
    css = (repository_root / "app/web/static/app.css").read_text()
    javascript = (repository_root / "app/web/static/app.js").read_text()

    assert '${PORT:-8000}' in dockerfile
    assert "viewport-fit=cover" in index
    assert "env(safe-area-inset-bottom)" in css
    assert 'role: "button"' in javascript


def test_health_and_core_crud():
    with TestClient(app) as client:
        mission_control = {"Authorization": f"Bearer {api_tokens['mission_control']}"}
        root = client.get("/")
        assert root.status_code == 200
        assert "LANSEIR" in root.text

        favicon = client.get("/favicon.ico")
        assert favicon.status_code == 200
        assert favicon.headers["content-type"].startswith("image/svg+xml")

        docs = client.get("/docs")
        assert docs.status_code == 200

        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"

        assert client.get("/api/v1/gateway/commands").status_code == 401
        command_registry = client.get("/api/v1/gateway/commands", headers=mission_control)
        assert command_registry.status_code == 200
        assert any(item["key"] == "actively_advance" for item in command_registry.json()["commands"])
        gateway_status = client.post(
            "/api/v1/gateway/resolve",
            headers=mission_control,
            json={"raw_input": "Status"},
        )
        assert gateway_status.status_code == 200
        assert gateway_status.json()["status"] == "completed"
        assert gateway_status.json()["active_context"]["active_project"]["slug"] == "lanseir-platform"

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

        unverified_completion = client.post("/api/v1/command-briefs", headers=mission_control, json={
            "project_id": project_id,
            "title": "Reject status-only completion",
            "objective": "Prove completion is evidence-gated",
            "validation_criteria": ["mission evidence verified"],
            "status": "completed",
        })
        assert unverified_completion.status_code == 409

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
        reader = {"Authorization": f"Bearer {api_tokens['griot']}"}
        writer = {"Authorization": f"Bearer {api_tokens['al']}"}
        founder = {"Authorization": f"Bearer {api_tokens['founder']}"}

        assert client.get("/api/v1/projects", headers=reader).status_code == 200
        denied = client.post(
            "/api/v1/projects",
            headers=reader,
            json={"slug": "forbidden", "name": "Forbidden"},
        )
        assert denied.status_code == 403
        assert client.post(
            "/api/v1/projects",
            headers=founder,
            json={"slug": "founder-direct-write", "name": "Founder Direct Write"},
        ).status_code == 403
        assert client.post(
            "/api/v1/gateway/resolve",
            headers=founder,
            json={"raw_input": "Status"},
        ).status_code == 200

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


def test_admin_promotion_and_canonical_content_are_explicitly_gated():
    with TestClient(app) as client:
        mission_control = {"Authorization": f"Bearer {api_tokens['mission_control']}"}
        signup = client.post(
            "/api/v1/auth/signup",
            json={
                "email": "admin@example.com",
                "password": "MajesticPass123",
                "display_name": "Verified Administrator",
            },
        )
        assert signup.status_code == 201
        signup_payload = signup.json()
        assert signup_payload["user"]["role"] == "member"
        assert client.get("/api/v1/admin/audit").status_code == 403

        verified = client.post(
            "/api/v1/auth/verify",
            json={"token": signup_payload["development_token"]},
        )
        assert verified.status_code == 200
        assert client.get("/api/v1/admin/audit").status_code == 403

        promoted = client.post(
            f"/api/v1/identity/admins/{signup_payload['user']['id']}",
            headers=mission_control,
        )
        assert promoted.status_code == 200
        assert promoted.json()["role"] == "admin"
        assert client.get("/api/v1/admin/audit").status_code == 200

        library = client.get("/api/v1/library")
        assert library.status_code == 200
        book_id = library.json()[0]["id"]
        canonical_body = "Approved canonical chapter text."
        body_sha = hashlib.sha256(canonical_body.encode()).hexdigest()
        source = client.post(
            "/api/v1/content-sources",
            headers=mission_control,
            json={
                "book_id": book_id,
                "source_locator": "vault://VESSEL/canonical-manuscript.md",
                "manifest_sha256": hashlib.sha256(b"canonical-manifest").hexdigest(),
                "chapter_hashes": {"1": body_sha},
                "approval_receipt": "registry://approval/vessel-test",
            },
        )
        assert source.status_code == 201

        csrf = signup_payload["csrf_token"]
        admin_headers = {"X-CSRF-Token": csrf}
        mismatch = client.post(
            f"/api/v1/admin/books/{book_id}/chapters",
            headers=admin_headers,
            json={
                "source_id": source.json()["id"],
                "title": "Chapter One",
                "position": 1,
                "body": "Regenerated or substituted text.",
            },
        )
        assert mismatch.status_code == 409

        chapter = client.post(
            f"/api/v1/admin/books/{book_id}/chapters",
            headers=admin_headers,
            json={
                "source_id": source.json()["id"],
                "title": "Chapter One",
                "position": 1,
                "body": canonical_body,
            },
        )
        assert chapter.status_code == 201
        assert chapter.json()["sha256"] == body_sha
        published = client.put(
            f"/api/v1/admin/books/{book_id}/state",
            headers=admin_headers,
            json={"state": "available"},
        )
        assert published.status_code == 200
        assert published.json()["state"] == "available"


def test_member_journey_is_persistent_sequential_and_portable():
    password = "PrivatePassage42"
    with TestClient(app) as client:
        signup = client.post(
            "/api/v1/auth/signup",
            json={"email": "member@example.com", "password": password, "display_name": "Captain"},
        )
        assert signup.status_code == 201
        assert signup.json()["user"]["role"] == "member"
        write = {"X-CSRF-Token": signup.json()["csrf_token"]}

        profile = client.patch("/api/v1/me", headers=write, json={"display_name": "Captain Cho"})
        assert profile.status_code == 200
        assert profile.json()["display_name"] == "Captain Cho"

        entry = client.post(
            "/api/v1/captains-log",
            headers=write,
            json={"title": "Present reality", "body": "The course remains mine.", "prompt": "What is true?"},
        )
        assert entry.status_code == 201
        assert client.get("/api/v1/captains-log?query=course").json()[0]["id"] == entry.json()["id"]

        voyage = client.get("/api/v1/voyages").json()[0]
        enrolled = client.post(f"/api/v1/voyages/{voyage['id']}/enroll", headers=write)
        assert enrolled.status_code == 201
        lessons = enrolled.json()["lessons"]
        ahead = client.put(
            f"/api/v1/voyages/{voyage['id']}/lessons/{lessons[1]['id']}/reflection",
            headers=write,
            json={"body": "Attempted out of sequence", "complete": True},
        )
        assert ahead.status_code == 409
        result = None
        for lesson in lessons:
            result = client.put(
                f"/api/v1/voyages/{voyage['id']}/lessons/{lesson['id']}/reflection",
                headers=write,
                json={"body": f"Reflection for {lesson['title']}", "complete": True},
            )
            assert result.status_code == 200
        assert result is not None
        assert result.json()["enrollment"]["status"] == "completed"
        assert result.json()["enrollment"]["current_lesson_id"] is None

        conversation = client.post(
            "/api/v1/ai/conversations",
            headers=write,
            json={"title": "Course reflection", "context_kind": "general", "context_id": None},
        )
        answer = client.post(
            f"/api/v1/ai/conversations/{conversation.json()['id']}/messages",
            headers=write,
            json={"content": "Help me see the next controlled action."},
        )
        assert answer.status_code == 201
        assert answer.json()["run"]["status"] == "completed"
        assert answer.json()["run"]["provider"] == "local"

        exported = client.get("/api/v1/me/export")
        assert exported.status_code == 200
        assert exported.json()["account"]["display_name"] == "Captain Cho"
        assert exported.json()["captains_log"][0]["id"] == entry.json()["id"]
        assert len(exported.json()["ai_messages"]) == 2

        assert client.post("/api/v1/auth/signout", headers=write).status_code == 204
        assert client.get("/api/v1/me").status_code == 401
        signin = client.post("/api/v1/auth/signin", json={"email": "member@example.com", "password": password})
        assert signin.status_code == 200
        assert signin.json()["user"]["display_name"] == "Captain Cho"


def test_reset_consumes_all_outstanding_reset_tokens():
    with TestClient(app) as client:
        client.post(
            "/api/v1/auth/signup",
            json={"email": "recovery@example.com", "password": "RecoveryPass42", "display_name": "Recovery"},
        )
        first = client.post("/api/v1/auth/password/forgot", json={"email": "recovery@example.com"}).json()["development_token"]
        second = client.post("/api/v1/auth/password/forgot", json={"email": "recovery@example.com"}).json()["development_token"]
        reset = client.post(
            "/api/v1/auth/password/reset",
            json={"token": first, "new_password": "RecoveredPass43"},
        )
        assert reset.status_code == 200
        reused = client.post(
            "/api/v1/auth/password/reset",
            json={"token": second, "new_password": "ShouldNotWork44"},
        )
        assert reused.status_code == 400
