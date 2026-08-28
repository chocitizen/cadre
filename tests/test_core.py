import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace


test_database_directory = TemporaryDirectory()
test_database_path = Path(test_database_directory.name) / "cadre.db"
os.environ["CADRE_DATABASE_URL"] = f"sqlite:///{test_database_path}"
os.environ["CADRE_OPERATIONS_STATE_PATH"] = str(Path(test_database_directory.name) / "operations.json")
os.environ["CADRE_ADMIN_EMAILS"] = "captain@example.com"
os.environ["CADRE_AI_PROVIDER"] = "local"
api_tokens = {
    role: hashlib.sha256(f"cadre-test-token:{role}".encode()).hexdigest()
    for role in ("mission_control", "al", "arc", "invictus", "porter", "griot", "sentinel")
}
os.environ["CADRE_API_TOKENS_JSON"] = json.dumps(api_tokens)

from fastapi.testclient import TestClient

from app.main import app


def test_health_shell_and_core_crud():
    with TestClient(app) as client:
        mission_control = {"Authorization": f"Bearer {api_tokens['mission_control']}"}
        root = client.get("/")
        assert root.status_code == 200
        assert "text/html" in root.headers["content-type"]
        assert "default-src 'self'" in root.headers["content-security-policy"]
        assert root.headers["x-frame-options"] == "DENY"

        docs = client.get("/docs")
        assert docs.status_code == 200

        health = client.get("/api/v1/health")
        assert health.status_code == 200
        assert health.json()["status"] == "ok"
        assert health.json()["milestone"] == "M2"
        assert client.request("GET", "/healthz", content=b"unexpected").status_code == 400
        assert client.get("/off-the-chart").status_code == 404
        assert "text/html" in client.get("/off-the-chart").headers["content-type"]
        assert client.get("/api/v1/not-a-route").json() == {"detail": "Not found"}

        assert client.get("/api/v1/operations/state").status_code == 401
        operations = client.get("/api/v1/operations/state", headers=mission_control)
        assert operations.status_code == 200
        assert operations.json()["system"] == "DEGRADED"

        doctrine = client.get("/api/v1/doctrine", headers=mission_control)
        assert doctrine.status_code == 200
        assert any(x["key"] == "sovereignty" for x in doctrine.json())

        project = client.post("/api/v1/projects", headers=mission_control, json={
            "slug": "cadre-test",
            "name": "CADRE Test Project",
            "description": "M2 validation project",
        })
        assert project.status_code == 201
        project_id = project.json()["id"]

        brief = client.post("/api/v1/command-briefs", headers=mission_control, json={
            "project_id": project_id,
            "title": "Validate M2",
            "objective": "Prove project and command-brief persistence",
            "expected_outputs": ["validated core"],
            "validation_criteria": ["HTTP 201", "record persists"],
        })
        assert brief.status_code == 201
        assert brief.json()["project_id"] == project_id


def test_service_roles_are_domain_scoped_and_resource_bounded():
    with TestClient(app) as client:
        lower_privilege = {"Authorization": f"Bearer {api_tokens['invictus']}"}
        griot = {"Authorization": f"Bearer {api_tokens['griot']}"}
        writer = {"Authorization": f"Bearer {api_tokens['al']}"}

        assert client.get("/api/v1/projects", headers=lower_privilege).status_code == 403
        assert client.get("/api/v1/operations/state", headers=lower_privilege).status_code == 403
        assert client.get("/api/v1/doctrine", headers=griot).status_code == 200
        assert client.get("/api/v1/projects", headers=griot).status_code == 403
        denied = client.post("/api/v1/projects", headers=lower_privilege, json={"slug": "forbidden", "name": "Forbidden"})
        assert denied.status_code == 403

        oversized_field = client.post("/api/v1/projects", headers=writer, json={"slug": "oversized", "name": "Oversized", "description": "x" * 50_001})
        assert oversized_field.status_code == 422
        oversized_body = client.post("/api/v1/projects", headers=writer, content=b"x" * 1_048_577)
        assert oversized_body.status_code == 413
        assert client.get("/api/v1/projects?limit=101", headers=writer).status_code == 422


def test_complete_product_journey_and_persistence():
    password = "PassageSecure42"
    with TestClient(app) as client:
        assert client.get("/api/v1/library").status_code == 401
        signup = client.post("/api/v1/auth/signup", json={"email": "captain@example.com", "password": password, "display_name": "Captain"})
        assert signup.status_code == 201
        assert signup.json()["user"]["role"] == "admin"
        csrf = signup.json()["csrf_token"]
        write = {"X-CSRF-Token": csrf}

        session = client.get("/api/v1/auth/session").json()
        assert session["authenticated"] is True
        assert session["user"]["email"] == "captain@example.com"
        assert client.patch("/api/v1/me", json={"display_name": "No CSRF"}).status_code == 403
        assert client.patch("/api/v1/me", headers=write, json={"display_name": "Captain Cho"}).status_code == 200

        library = client.get("/api/v1/library")
        assert library.status_code == 200
        vessel = next(item for item in library.json() if item["slug"] == "vessel-mastering-the-ship-of-self")
        assert vessel["state"] == "draft"
        book = client.get(f"/api/v1/books/{vessel['slug']}").json()
        assert book["content_access"] == "awaiting_authorized_content"
        assert book["chapters"] == []

        chapter = client.post(
            f"/api/v1/admin/books/{vessel['id']}/chapters",
            headers=write,
            json={"title": "Authorized validation chapter", "position": 1, "body": "Authorized test fixture content."},
        )
        assert chapter.status_code == 201
        assert client.put(f"/api/v1/admin/books/{vessel['id']}/state", headers=write, json={"state": "available"}).status_code == 200
        user_id = signup.json()["user"]["id"]
        entitlement = client.post("/api/v1/admin/entitlements", headers=write, json={"user_id": user_id, "book_id": vessel["id"], "state": "active", "source": "test"})
        assert entitlement.status_code == 201
        book = client.get(f"/api/v1/books/{vessel['slug']}").json()
        assert len(book["chapters"]) == 1
        chapter_id = book["chapters"][0]["id"]

        progress = client.put(f"/api/v1/books/{vessel['id']}/progress", headers=write, json={"chapter_id": chapter_id, "percent": 35, "locator": "paragraph:2", "audio_seconds": 0, "playback_rate": 1})
        assert progress.status_code == 200
        assert progress.json()["percent"] == 35
        bookmark = client.post("/api/v1/bookmarks", headers=write, json={"book_id": vessel["id"], "chapter_id": chapter_id, "locator": "paragraph:2", "label": "Return here"})
        assert bookmark.status_code == 201
        note = client.post("/api/v1/notes", headers=write, json={"book_id": vessel["id"], "chapter_id": chapter_id, "locator": "paragraph:2", "body": "My private reading note"})
        assert note.status_code == 201

        journal = client.post("/api/v1/captains-log", headers=write, json={"title": "Present reality", "body": "The weather is changing.", "prompt": "What is true now?"})
        assert journal.status_code == 201
        journal_id = journal.json()["id"]
        updated = client.put(f"/api/v1/captains-log/{journal_id}", headers=write, json={"title": "Present reality", "body": "The weather changed; the course remains mine.", "prompt": "What is true now?"})
        assert updated.status_code == 200
        assert len(client.get("/api/v1/captains-log?query=course").json()) == 1

        voyages = client.get("/api/v1/voyages").json()
        voyage = voyages[0]
        enrolled = client.post(f"/api/v1/voyages/{voyage['id']}/enroll", headers=write)
        assert enrolled.status_code == 201
        for lesson in enrolled.json()["lessons"]:
            result = client.put(f"/api/v1/voyages/{voyage['id']}/lessons/{lesson['id']}/reflection", headers=write, json={"body": f"Reflection for {lesson['title']}", "complete": True})
            assert result.status_code == 200
        assert result.json()["enrollment"]["status"] == "completed"

        conversation = client.post("/api/v1/ai/conversations", headers=write, json={"title": "Course reflection", "context_kind": "notes", "context_id": None})
        assert conversation.status_code == 201
        ai = client.post(f"/api/v1/ai/conversations/{conversation.json()['id']}/messages", headers=write, json={"content": "Help me see the next action."})
        assert ai.status_code == 201
        assert ai.json()["run"]["status"] == "completed"
        assert ai.json()["run"]["provider"] == "local"
        assert "next" in ai.json()["message"]["content"].casefold() or "attention" in ai.json()["message"]["content"].casefold()

        mission = client.get("/api/v1/admin/mission-control")
        assert mission.status_code == 200
        assert mission.json()["counts"]["users"] >= 1
        assert any(item["key"] == "invictus" for item in mission.json()["specialists"])
        exported = client.get("/api/v1/me/export")
        assert exported.status_code == 200
        assert exported.json()["captains_log"][0]["id"] == journal_id

        assert client.post("/api/v1/auth/signout", headers=write).status_code == 204
        assert client.get("/api/v1/library").status_code == 401
        assert client.post("/api/v1/auth/signin", json={"email": "captain@example.com", "password": "IncorrectPass42"}).status_code == 401

        signin = client.post("/api/v1/auth/signin", json={"email": "captain@example.com", "password": password})
        assert signin.status_code == 200
        assert client.get("/api/v1/captains-log?query=course").json()[0]["id"] == journal_id
        assert client.get("/api/v1/books/vessel-mastering-the-ship-of-self").json()["progress"]["percent"] == 35


def test_user_owned_records_do_not_cross_accounts():
    with TestClient(app) as first:
        one = first.post("/api/v1/auth/signup", json={"email": "one@example.com", "password": "PrivatePassage42", "display_name": "One"}).json()
        entry = first.post("/api/v1/captains-log", headers={"X-CSRF-Token": one["csrf_token"]}, json={"title": "Only mine", "body": "Private", "prompt": ""}).json()
    with TestClient(app) as second:
        two = second.post("/api/v1/auth/signup", json={"email": "two@example.com", "password": "PrivatePassage43", "display_name": "Two"}).json()
        assert second.get("/api/v1/captains-log").json() == []
        assert second.put(f"/api/v1/captains-log/{entry['id']}", headers={"X-CSRF-Token": two["csrf_token"]}, json={"title": "Stolen", "body": "No", "prompt": ""}).status_code == 404


def test_ai_provider_failure_is_visible_and_recorded(monkeypatch):
    from app.api import product
    from app.services.ai import ProviderError

    async def unavailable(_message: str, _context: str):
        raise ProviderError("The configured AI provider is unavailable")

    monkeypatch.setattr(product, "route_completion", unavailable)
    with TestClient(app) as client:
        account = client.post("/api/v1/auth/signup", json={"email": "failure@example.com", "password": "PrivatePassage44", "display_name": "Failure Test"}).json()
        headers = {"X-CSRF-Token": account["csrf_token"]}
        conversation = client.post("/api/v1/ai/conversations", headers=headers, json={"title": "Failure path", "context_kind": "general", "context_id": None}).json()
        response = client.post(f"/api/v1/ai/conversations/{conversation['id']}/messages", headers=headers, json={"content": "Test failure handling"})
        assert response.status_code == 503
        assert response.json()["detail"] == "The configured AI provider is unavailable"


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
