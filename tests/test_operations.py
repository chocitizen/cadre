from __future__ import annotations

import io
import json
import gzip
import hashlib
import os
import subprocess
import sys
import tarfile
from pathlib import Path

import pytest

from ops.cadre_ops import AuditLedger, Controller, OperationError, Runner, safe_extract, safe_release_id


def make_controller(tmp_path: Path, actor: str = "lanseir-deploy") -> Controller:
    config_dir = tmp_path / "config"
    config_dir.mkdir(parents=True)
    source = Path(__file__).parents[1] / "ops" / "config"
    for name in (
        "roles.json",
        "actors.json",
        "services.json",
        "limits.json",
        "repository.json",
        "docker-compose.prod.yml",
        "Dockerfile.prod",
    ):
        (config_dir / name).write_bytes((source / name).read_bytes())
    root = tmp_path / "lanseir"
    (root / "logs" / "audit").mkdir(parents=True)
    (root / "cadre" / "state").mkdir(parents=True)
    (root / "releases").mkdir(parents=True)
    (root / "apps" / "cadre").mkdir(parents=True)
    (root / "shared").mkdir(parents=True)
    (root / "secrets").mkdir(parents=True)
    password = "Cadre-Test-9fA2kL7mQ4vN8xR6"
    tokens = {
        role: hashlib.sha256(f"cadre-operations-test:{role}".encode()).hexdigest()
        for role in ("mission_control", "al", "invictus", "porter", "griot", "sentinel")
    }
    secret_file = root / "secrets" / "cadre.env"
    secret_file.write_text(
        "\n".join(
            (
                f"CADRE_DB_PASSWORD={password}",
                f"CADRE_DATABASE_URL=postgresql+psycopg://cadre:{password}@db:5432/cadre",
                "CADRE_PUBLIC_HOST=cadre.test.internal",
                "CADRE_PUBLIC_URL=https://cadre.test.internal",
                "CADRE_ACME_EMAIL=ops@cadre.test.internal",
                "CADRE_ADMIN_EMAILS=owner@cadre.test.internal",
                f"CADRE_API_TOKENS_JSON={json.dumps(tokens, separators=(',', ':'))}",
            )
        )
        + "\n",
        encoding="utf-8",
    )
    secret_file.chmod(0o600)
    repository = json.loads((config_dir / "repository.json").read_text(encoding="utf-8"))
    repository["mirror_path"] = str(root / "shared" / "cadre-repository.git")
    (config_dir / "repository.json").write_text(json.dumps(repository), encoding="utf-8")
    return Controller(root, config_dir, actor)


def test_role_policy_allows_only_declared_actions_and_targets(tmp_path: Path):
    al = make_controller(tmp_path)
    al.authorize("deploy", "a" * 40)
    with pytest.raises(OperationError):
        al.authorize("deploy", None)
    al.authorize("restart", "api")
    with pytest.raises(OperationError):
        al.authorize("backup", None)
    with pytest.raises(OperationError):
        al.authorize("restart", "db")


def test_deferred_arc_target_fails_closed(tmp_path: Path):
    arc = make_controller(tmp_path, "lanseir-arc")
    with pytest.raises(OperationError):
        arc.authorize("restart", "litellm")


def test_unmapped_actor_is_rejected_and_audited(tmp_path: Path):
    controller = make_controller(tmp_path, "unknown-user")
    exit_status, result = controller.execute("release-current")
    assert exit_status == 77
    assert "not mapped" in result["error"]
    verification = controller.audit.verify()
    assert verification["valid"] is True
    assert verification["entries"] == 1


def test_state_contains_configuration_driven_agent_registry(tmp_path: Path):
    controller = make_controller(tmp_path, "lanseir-griot")
    exit_status, result = controller.execute("release-current")
    assert exit_status == 0
    assert result["current_release"] is None
    state = json.loads(controller.state_path.read_text(encoding="utf-8"))
    by_id = {agent["agent_id"]: agent for agent in state["agents"]}
    assert set(by_id) == {"mission_control", "al", "arc", "invictus", "porter", "griot", "sentinel"}
    assert by_id["arc"]["status"] == "BLOCKED"
    for agent in by_id.values():
        assert {
            "agent_id",
            "name",
            "role",
            "capabilities",
            "permissions",
            "model_policy",
            "tools",
            "status",
            "current_assignment",
            "last_activity",
        } <= set(agent)


def test_audit_ledger_detects_tampering(tmp_path: Path):
    path = tmp_path / "operations.jsonl"
    ledger = AuditLedger(path)
    ledger.append({"action": "one"})
    ledger.append({"action": "two"})
    assert ledger.verify()["valid"] is True
    lines = path.read_text(encoding="utf-8").splitlines()
    altered = json.loads(lines[0])
    altered["action"] = "changed"
    lines[0] = json.dumps(altered, sort_keys=True)
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    assert ledger.verify()["valid"] is False


def test_audit_ledger_uses_constant_time_head_checkpoint(tmp_path: Path):
    path = tmp_path / "operations.jsonl"
    ledger = AuditLedger(path)
    first = ledger.append({"action": "one"})
    second = ledger.append({"action": "two"})
    head = json.loads(ledger.head_path.read_text(encoding="utf-8"))
    assert head["entries"] == 2
    assert head["last_hash"] == second["record_hash"]
    assert second["previous_hash"] == first["record_hash"]
    head["byte_size"] -= 1
    ledger.head_path.write_text(json.dumps(head), encoding="utf-8")
    with pytest.raises(OperationError):
        ledger.append({"action": "three"})


def test_release_identifier_is_exact_commit_sha():
    release = "a" * 40
    assert safe_release_id(release) == release
    for invalid in ("main", "A" * 40, "a" * 39, "a" * 41, "../release"):
        with pytest.raises(OperationError):
            safe_release_id(invalid)


def test_release_archive_rejects_path_traversal(tmp_path: Path):
    archive = tmp_path / "unsafe.tar.gz"
    with tarfile.open(archive, "w:gz") as bundle:
        payload = b"unsafe"
        member = tarfile.TarInfo("../escape")
        member.size = len(payload)
        bundle.addfile(member, io.BytesIO(payload))
    with pytest.raises(OperationError):
        safe_extract(archive, tmp_path / "destination")
    assert not (tmp_path / "escape").exists()


def test_release_archive_enforces_resource_policy(tmp_path: Path):
    archive = tmp_path / "large.tar"
    with tarfile.open(archive, "w") as bundle:
        payload = b"x" * 128
        member = tarfile.TarInfo("payload.bin")
        member.size = len(payload)
        bundle.addfile(member, io.BytesIO(payload))
    with pytest.raises(OperationError):
        safe_extract(archive, tmp_path / "destination", max_file_bytes=64)

    member_archive = tmp_path / "members.tar"
    with tarfile.open(member_archive, "w") as bundle:
        for name in ("one", "two", "three"):
            member = tarfile.TarInfo(name)
            member.size = 0
            bundle.addfile(member, io.BytesIO())
    with pytest.raises(OperationError, match="member-count"):
        safe_extract(member_archive, tmp_path / "member-destination", max_members=2)


def test_real_deploy_shape_reaches_typed_handler(tmp_path: Path, monkeypatch):
    controller = make_controller(tmp_path)
    release = "b" * 40
    observed = {}

    def fake_deploy(target):
        observed["target"] = target
        return {"deployed": True, "release": target}

    monkeypatch.setattr(controller, "deploy", fake_deploy)
    exit_status, result = controller.execute("deploy", release)
    assert exit_status == 0
    assert result["release"] == release
    assert observed["target"] == release
    assert result["receipt"]["intent_hash"]


def test_canonical_fetch_requires_main_ancestry(tmp_path: Path):
    class GitRunner(Runner):
        def __init__(self, release: str, ancestry_returncode: int):
            self.release = release
            self.ancestry_returncode = ancestry_returncode

        def run(self, command, **kwargs):
            rendered = " ".join(command)
            if "remote get-url origin" in rendered:
                stdout = b"https://github.com/chocitizen/cadre.git\n"
                return subprocess.CompletedProcess(command, 0, stdout, b"")
            if "rev-parse" in rendered:
                return subprocess.CompletedProcess(command, 0, f"{self.release}\n".encode(), b"")
            if "merge-base --is-ancestor" in rendered:
                return subprocess.CompletedProcess(command, self.ancestry_returncode, b"", b"")
            return subprocess.CompletedProcess(command, 0, b"", b"")

    release = "c" * 40
    rejected = make_controller(tmp_path / "rejected")
    rejected.repository_mirror.mkdir()
    rejected.runner = GitRunner(release, 1)
    with pytest.raises(OperationError, match="ancestor"):
        rejected._fetch_canonical_release(release)

    accepted = make_controller(tmp_path / "accepted")
    accepted.repository_mirror.mkdir()
    accepted.runner = GitRunner(release, 0)
    accepted._fetch_canonical_release(release)


def test_health_is_bound_to_compose_service_and_release(tmp_path: Path, monkeypatch):
    controller = make_controller(tmp_path, "lanseir-sentinel")
    release = "d" * 40
    release_dir = controller.releases / release
    release_dir.mkdir()
    controller._atomic_link(release_dir, controller.current_link)

    def matching_compose(*arguments, **_):
        if arguments[:3] == ("ps", "--status", "running"):
            return subprocess.CompletedProcess(arguments, 0, b"api\n", b"")
        payload = json.dumps({"status": "ok", "release": release}).encode() + b"\n"
        return subprocess.CompletedProcess(arguments, 0, payload, b"")

    monkeypatch.setattr(controller, "_compose", matching_compose)
    assert controller._health()["healthy"] is True

    def mismatched_compose(*arguments, **_):
        if arguments[:3] == ("ps", "--status", "running"):
            return subprocess.CompletedProcess(arguments, 0, b"api\n", b"")
        payload = json.dumps({"status": "ok", "release": "e" * 40}).encode() + b"\n"
        return subprocess.CompletedProcess(arguments, 0, payload, b"")

    monkeypatch.setattr(controller, "_compose", mismatched_compose)
    assert controller._health()["healthy"] is False


def test_audit_failure_prevents_mutating_handler(tmp_path: Path, monkeypatch):
    controller = make_controller(tmp_path)
    controller.audit.max_bytes = 1
    invoked = False

    def fake_restart(_):
        nonlocal invoked
        invoked = True
        return {"restarted": "api"}

    monkeypatch.setattr(controller, "restart", fake_restart)
    exit_status, result = controller.execute("restart", "api")
    assert exit_status == 1
    assert invoked is False
    assert "Audit durability unavailable" in result["error"]


def test_terminal_audit_failure_suppresses_protected_logs(tmp_path: Path, monkeypatch):
    controller = make_controller(tmp_path, "lanseir-invictus")
    calls = 0

    def fail_terminal(_payload):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"record_hash": "a" * 64}
        raise OSError("ledger unavailable")

    monkeypatch.setattr(controller.audit, "append", fail_terminal)
    monkeypatch.setattr(controller.audit, "assert_ready", lambda: None)
    monkeypatch.setattr(controller, "logs", lambda _: {"logs": "sensitive service output"})
    exit_status, result = controller.execute("logs", "api")
    assert exit_status == 1
    assert result == {"error": "Audit durability unavailable; protected output was suppressed."}


def test_placeholder_secrets_fail_closed(tmp_path: Path):
    controller = make_controller(tmp_path)
    controller.secrets_file.write_text(
        "CADRE_DB_PASSWORD=replace_with_a_strong_unique_password\n"
        "CADRE_DATABASE_URL=postgresql+psycopg://cadre:replace_with_url_encoded_password@db:5432/cadre\n"
        "CADRE_PUBLIC_HOST=cadre.example.com\n"
        "CADRE_PUBLIC_URL=https://cadre.example.com\n"
        "CADRE_ACME_EMAIL=operations@example.com\n"
        "CADRE_ADMIN_EMAILS=owner@example.com\n"
        "CADRE_API_TOKENS_JSON={}\n",
        encoding="utf-8",
    )
    controller.secrets_file.chmod(0o600)
    with pytest.raises(OperationError, match="template values"):
        controller.validate_secrets()

    weak_tokens = make_controller(tmp_path / "weak-tokens")
    values = weak_tokens.secrets_file.read_text(encoding="utf-8").splitlines()
    tokens = {role: character * 32 for role, character in zip(
        ("mission_control", "al", "invictus", "porter", "griot", "sentinel"),
        "ABCDEF",
        strict=True,
    )}
    values[-1] = f"CADRE_API_TOKENS_JSON={json.dumps(tokens, separators=(',', ':'))}"
    weak_tokens.secrets_file.write_text("\n".join(values) + "\n", encoding="utf-8")
    weak_tokens.secrets_file.chmod(0o600)
    with pytest.raises(OperationError, match="unsafe token"):
        weak_tokens.validate_secrets()


@pytest.mark.parametrize(
    ("password", "database_url", "expected"),
    (
        (
            "A" * 24,
            f"postgresql+psycopg://cadre:{'A' * 24}@db:5432/cadre",
            "length policy",
        ),
        (
            "Cadre-Test-9fA2kL7mQ4vN8xR6",
            "postgresql+psycopg://cadre:Cadre-Test-9fA2kL7mQ4vN8xR6@db:9999/cadre",
            "inconsistent",
        ),
        (
            "${CADRE_RELEASE_ID:-public-value}",
            "postgresql+psycopg://cadre:${CADRE_RELEASE_ID:-public-value}@db:5432/cadre",
            "interpolation",
        ),
    ),
)
def test_weak_or_interpolated_secrets_fail_closed(tmp_path: Path, password: str, database_url: str, expected: str):
    controller = make_controller(tmp_path)
    values = controller.secrets_file.read_text(encoding="utf-8").splitlines()
    values[0] = f"CADRE_DB_PASSWORD={password}"
    values[1] = f"CADRE_DATABASE_URL={database_url}"
    controller.secrets_file.write_text("\n".join(values) + "\n", encoding="utf-8")
    controller.secrets_file.chmod(0o600)
    with pytest.raises(OperationError, match=expected):
        controller.validate_secrets()


def test_backup_count_and_frequency_are_bounded(tmp_path: Path):
    controller = make_controller(tmp_path, "lanseir-porter")
    controller.limits["backup_max_local_sets"] = 1
    backup = controller.root / "backups" / "20260828T010203000000Z"
    backup.mkdir(parents=True)
    with pytest.raises(OperationError, match="backup limit"):
        controller._backup_preflight()

    interrupted = make_controller(tmp_path / "interrupted", "lanseir-porter")
    partial = interrupted.root / "backups" / ".20260828T010203000000Z.partial"
    partial.mkdir(parents=True)
    with pytest.raises(OperationError, match="frequency limit"):
        interrupted._backup_preflight()


def test_streaming_runner_round_trip(tmp_path: Path):
    runner = Runner()
    destination = tmp_path / "payload.gz"
    env = os.environ.copy()
    payload_size = 2_000_000
    returncode, error = runner.stream_stdout_to_gzip(
        [sys.executable, "-c", f"import sys; sys.stdout.buffer.write(b'x' * {payload_size})"],
        destination,
        timeout=30,
        env=env,
    )
    assert returncode == 0, error

    bounded_destination = tmp_path / "bounded.gz"
    returncode, error = runner.stream_stdout_to_gzip(
        [sys.executable, "-c", f"import sys; sys.stdout.buffer.write(b'x' * {payload_size})"],
        bounded_destination,
        timeout=30,
        env=env,
        max_input_bytes=1_000_000,
    )
    assert returncode == 75
    assert "size ceiling" in error
    with gzip.open(destination, "rb") as handle:
        assert sum(len(block) for block in iter(lambda: handle.read(65_536), b"")) == payload_size

    returncode, error = runner.stream_gzip_to_stdin(
        destination,
        [
            sys.executable,
            "-c",
            f"import sys; data=sys.stdin.buffer.read(); raise SystemExit(0 if len(data)=={payload_size} else 2)",
        ],
        timeout=30,
        env=env,
    )
    assert returncode == 0, error


def test_runner_bounds_output_and_converts_timeout(tmp_path: Path):
    runner = Runner()
    completed = runner.run(
        [sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'x' * 200000)"],
        timeout=30,
        env=os.environ.copy(),
    )
    assert completed.returncode == 0
    assert len(completed.stdout) == 64_000

    timed_out = runner.run(
        [sys.executable, "-c", "import time; time.sleep(5)"],
        timeout=1,
        env=os.environ.copy(),
    )
    assert timed_out.returncode == 124
    assert b"timed out" in timed_out.stderr


def test_failed_first_deploy_clears_unverified_release_pointer(tmp_path: Path, monkeypatch):
    controller = make_controller(tmp_path)
    release = "f" * 40
    destination = controller.releases / release
    destination.mkdir()
    monkeypatch.setattr(controller, "_fetch_canonical_release", lambda _: None)
    monkeypatch.setattr(controller, "_materialize_release", lambda _: destination)
    monkeypatch.setattr(controller, "_wait_for_health", lambda: {"healthy": False})

    def compose(*arguments, **_):
        return subprocess.CompletedProcess(arguments, 0, b"", b"")

    monkeypatch.setattr(controller, "_compose", compose)
    with pytest.raises(OperationError):
        controller.deploy(release)
    assert controller.current_release() is None
    state = controller.read_state()
    assert state["current_release"] is None
    assert state["deployment"] == "FAILED"


def test_deploy_activation_exception_restores_verified_previous_release(tmp_path: Path, monkeypatch):
    controller = make_controller(tmp_path)
    previous = "1" * 40
    candidate = "2" * 40
    previous_path = controller.releases / previous
    candidate_path = controller.releases / candidate
    previous_path.mkdir()
    candidate_path.mkdir()
    controller._atomic_link(previous_path, controller.current_link)
    monkeypatch.setattr(controller, "_fetch_canonical_release", lambda _: None)
    monkeypatch.setattr(controller, "_materialize_release", lambda _: candidate_path)
    monkeypatch.setattr(controller, "_wait_for_health", lambda: {"healthy": True, "release": previous})
    calls = 0

    def compose(*arguments, **_):
        nonlocal calls
        calls += 1
        if calls == 1:
            raise subprocess.TimeoutExpired(arguments, 1)
        return subprocess.CompletedProcess(arguments, 0, b"", b"")

    monkeypatch.setattr(controller, "_compose", compose)
    with pytest.raises(OperationError):
        controller.deploy(candidate)
    assert controller.current_release() == previous
    state = controller.read_state()
    assert state["deployment"] == "ROLLED_BACK"
    assert state["current_release"] == previous
