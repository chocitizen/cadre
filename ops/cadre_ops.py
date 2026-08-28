#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fcntl
import getpass
import gzip
import hashlib
import json
import os
import re
import shutil
import subprocess
import tarfile
import tempfile
import threading
import time
import urllib.parse
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any, BinaryIO, Iterator


RELEASE_RE = re.compile(r"^[0-9a-f]{40}$")
SERVICE_RE = re.compile(r"^[a-z0-9][a-z0-9-]{0,31}$")
BRANCH_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._/-]{0,127}$")
BACKUP_RE = re.compile(r"^\d{8}T\d{12}Z$")
MAX_OUTPUT = 64_000
SAFE_PATH = "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
SERVICE_TARGET_ACTIONS = frozenset({"restart", "logs"})
RELEASE_TARGET_ACTIONS = frozenset({"deploy"})
MUTATING_ACTIONS = frozenset({"deploy", "rollback", "restart", "backup", "restore-test", "security-audit"})
PROTECTED_READ_ACTIONS = frozenset({"logs"})
AUDIT_GATED_ACTIONS = MUTATING_ACTIONS | PROTECTED_READ_ACTIONS


class OperationError(RuntimeError):
    def __init__(self, message: str, exit_status: int = 1):
        super().__init__(message)
        self.exit_status = exit_status


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def atomic_json(path: Path, payload: dict[str, Any], mode: int = 0o640) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.chmod(temp_name, mode)
        os.replace(temp_name, path)
        fsync_directory(path.parent)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def fsync_directory(path: Path) -> None:
    flags = os.O_RDONLY
    if hasattr(os, "O_DIRECTORY"):
        flags |= os.O_DIRECTORY
    descriptor = os.open(path, flags)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def safe_release_id(value: str) -> str:
    if not RELEASE_RE.fullmatch(value):
        raise OperationError("Release ID must be a full 40-character lowercase Git commit SHA.", 64)
    return value


def safe_service(value: str) -> str:
    if not SERVICE_RE.fullmatch(value):
        raise OperationError("Invalid service target.", 64)
    return value


def safe_extract(
    archive: Path,
    destination: Path,
    *,
    max_archive_bytes: int = 268_435_456,
    max_expanded_bytes: int = 536_870_912,
    max_members: int = 10_000,
    max_file_bytes: int = 67_108_864,
) -> None:
    if archive.stat().st_size > max_archive_bytes:
        raise OperationError("Release archive exceeds the compressed-size policy.")
    with tarfile.open(archive, "r|*") as bundle:
        seen: set[str] = set()
        expanded = 0
        executable: set[str] = set()
        count = 0
        for member in bundle:
            count += 1
            if count > max_members:
                raise OperationError("Release archive exceeds the member-count policy.")
            relative = PurePosixPath(member.name)
            normalized = relative.as_posix().rstrip("/")
            if not normalized or relative.is_absolute() or ".." in relative.parts:
                raise OperationError("Release archive contains an unsafe path.")
            if normalized in seen:
                raise OperationError("Release archive contains duplicate paths.")
            seen.add(normalized)
            if not (member.isfile() or member.isdir()):
                raise OperationError("Release archive contains a disallowed entry type.")
            if member.mode & 0o7000:
                raise OperationError("Release archive contains privileged mode bits.")
            if member.isfile():
                if member.size > max_file_bytes:
                    raise OperationError("Release archive contains an oversized file.")
                expanded += member.size
                if member.mode & 0o111:
                    executable.add(normalized)
            if expanded > max_expanded_bytes:
                raise OperationError("Release archive exceeds the expanded-size policy.")
            bundle.extract(member, path=destination, set_attrs=False, filter="data")
        if count == 0:
            raise OperationError("Release archive is empty.")

    for extracted in destination.rglob("*"):
        try:
            extracted.resolve(strict=True).relative_to(destination.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise OperationError("Release extraction escaped its staging directory.") from exc
        relative = extracted.relative_to(destination).as_posix()
        if extracted.is_dir():
            extracted.chmod(0o750)
        elif extracted.is_file():
            extracted.chmod(0o750 if relative in executable else 0o640)
        else:
            raise OperationError("Release extraction produced an unsupported file type.")


def _read_bounded_tail(handle: BinaryIO, limit: int = MAX_OUTPUT) -> bytes:
    handle.flush()
    handle.seek(0, os.SEEK_END)
    size = handle.tell()
    handle.seek(max(0, size - limit))
    return handle.read(limit)


class Runner:
    def run(
        self,
        command: list[str],
        *,
        cwd: Path | None = None,
        input_bytes: bytes | None = None,
        timeout: int = 300,
        env: dict[str, str] | None = None,
    ) -> subprocess.CompletedProcess[bytes]:
        with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
            try:
                process = subprocess.Popen(
                    command,
                    cwd=str(cwd) if cwd else None,
                    env=env,
                    stdin=subprocess.PIPE if input_bytes is not None else subprocess.DEVNULL,
                    stdout=stdout,
                    stderr=stderr,
                )
                try:
                    process.communicate(input=input_bytes, timeout=timeout)
                    returncode = process.returncode
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.communicate()
                    returncode = 124
                    stderr.write(b"\nOperation timed out and the subprocess was terminated.\n")
            except OSError as exc:
                return subprocess.CompletedProcess(command, 126, b"", str(exc).encode("utf-8", "replace")[-MAX_OUTPUT:])
            return subprocess.CompletedProcess(
                command,
                returncode,
                _read_bounded_tail(stdout),
                _read_bounded_tail(stderr),
            )

    def stream_stdout_to_gzip(
        self,
        command: list[str],
        destination: Path,
        *,
        timeout: int,
        env: dict[str, str],
        max_input_bytes: int | None = None,
        minimum_free_bytes: int = 0,
    ) -> tuple[int, str]:
        with tempfile.TemporaryFile() as stderr, gzip.open(destination, "wb", compresslevel=9) as compressed:
            process = subprocess.Popen(command, env=env, stdout=subprocess.PIPE, stderr=stderr)
            assert process.stdout is not None
            timer = threading.Timer(timeout, process.kill)
            timer.start()
            total = 0
            try:
                for block in iter(lambda: process.stdout.read(1024 * 1024), b""):
                    total += len(block)
                    if max_input_bytes is not None and total > max_input_bytes:
                        process.kill()
                        returncode = 75
                        stderr.write(b"Database backup exceeded the configured size ceiling.\n")
                        break
                    if minimum_free_bytes and shutil.disk_usage(destination.parent).free < minimum_free_bytes:
                        process.kill()
                        returncode = 75
                        stderr.write(b"Database backup reached the configured free-space reserve.\n")
                        break
                    compressed.write(block)
                else:
                    returncode = process.wait()
                process.stdout.close()
                if process.poll() is None:
                    process.wait()
            finally:
                timer.cancel()
            error = _read_bounded_tail(stderr).decode("utf-8", "replace")
        return returncode, error

    def stream_gzip_to_stdin(
        self,
        source: Path,
        command: list[str],
        *,
        timeout: int,
        env: dict[str, str],
    ) -> tuple[int, str]:
        with tempfile.TemporaryFile() as stderr, gzip.open(source, "rb") as compressed:
            process = subprocess.Popen(command, env=env, stdin=subprocess.PIPE, stderr=stderr)
            assert process.stdin is not None
            timer = threading.Timer(timeout, process.kill)
            timer.start()
            try:
                try:
                    for block in iter(lambda: compressed.read(1024 * 1024), b""):
                        process.stdin.write(block)
                except BrokenPipeError:
                    pass
                finally:
                    process.stdin.close()
                returncode = process.wait()
            finally:
                timer.cancel()
            error = _read_bounded_tail(stderr).decode("utf-8", "replace")
        return returncode, error


class AuditLedger:
    def __init__(self, path: Path, max_bytes: int = 67_108_864):
        self.path = path
        self.head_path = path.with_name(f"{path.stem}.head.json")
        self.max_bytes = max_bytes

    def _head(self, current_size: int) -> dict[str, Any]:
        if not self.head_path.exists():
            if current_size == 0:
                return {"entries": 0, "last_hash": "GENESIS", "byte_size": 0}
            raise OperationError("Audit head checkpoint is missing; operations are fail-closed.")
        try:
            head = json.loads(self.head_path.read_text(encoding="utf-8"))
            entries = int(head["entries"])
            byte_size = int(head["byte_size"])
            last_hash = str(head["last_hash"])
        except (OSError, KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise OperationError("Audit head checkpoint is invalid; operations are fail-closed.") from exc
        if entries < 0 or byte_size != current_size or not re.fullmatch(r"GENESIS|[0-9a-f]{64}", last_hash):
            raise OperationError("Audit ledger and head checkpoint disagree; operations are fail-closed.")
        return {"entries": entries, "last_hash": last_hash, "byte_size": byte_size}

    def assert_ready(self, reserve_bytes: int = 32_768) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o640)
        with os.fdopen(fd, "r+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            size = os.fstat(handle.fileno()).st_size
            self._head(size)
            if size + reserve_bytes > self.max_bytes:
                raise OperationError("Audit capacity is exhausted; externally anchor and rotate before continuing.")

    def append(self, record: dict[str, Any]) -> dict[str, Any]:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT | os.O_APPEND
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.path, flags, 0o640)
        with os.fdopen(fd, "r+", encoding="utf-8") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            size = os.fstat(handle.fileno()).st_size
            head = self._head(size)
            chained = {**record, "sequence": head["entries"] + 1, "previous_hash": head["last_hash"]}
            encoded = json.dumps(chained, sort_keys=True, separators=(",", ":")).encode("utf-8")
            chained["record_hash"] = hashlib.sha256(encoded).hexdigest()
            line = (json.dumps(chained, sort_keys=True) + "\n").encode("utf-8")
            if size + len(line) > self.max_bytes:
                raise OperationError("Audit capacity is exhausted; externally anchor and rotate before continuing.")
            written = 0
            while written < len(line):
                count = os.write(handle.fileno(), line[written:])
                if count <= 0:
                    raise OperationError("Audit ledger append did not complete")
                written += count
            os.fsync(handle.fileno())
            atomic_json(
                self.head_path,
                {
                    "entries": chained["sequence"],
                    "last_hash": chained["record_hash"],
                    "byte_size": size + len(line),
                    "updated_at": utc_now(),
                },
            )
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
        return chained

    def verify(self) -> dict[str, Any]:
        if not self.path.exists() and not self.head_path.exists():
            return {"valid": True, "entries": 0, "last_hash": "GENESIS", "initialized": False}
        if not self.path.exists() or not self.head_path.exists():
            return {"valid": False, "entries": 0, "reason": "ledger or head checkpoint missing"}
        previous = "GENESIS"
        count = 0
        try:
            with self.path.open(encoding="utf-8") as handle:
                for line in handle:
                    if not line.strip():
                        continue
                    item = json.loads(line)
                    actual_hash = item.pop("record_hash")
                    if item.get("sequence") != count + 1 or item.get("previous_hash") != previous:
                        return {"valid": False, "entries": count, "reason": "chain discontinuity"}
                    encoded = json.dumps(item, sort_keys=True, separators=(",", ":")).encode("utf-8")
                    if hashlib.sha256(encoded).hexdigest() != actual_hash:
                        return {"valid": False, "entries": count, "reason": "record hash mismatch"}
                    previous = actual_hash
                    count += 1
            head = self._head(self.path.stat().st_size)
        except (OSError, OperationError, KeyError, json.JSONDecodeError) as exc:
            return {"valid": False, "entries": count, "reason": str(exc)}
        if head["entries"] != count or head["last_hash"] != previous:
            return {"valid": False, "entries": count, "reason": "terminal checkpoint mismatch"}
        return {"valid": True, "entries": count, "last_hash": previous, "initialized": True}


class Controller:
    def __init__(
        self,
        root: Path,
        config_dir: Path,
        actor: str,
        *,
        runner: Runner | None = None,
    ):
        self.root = root.resolve()
        self.config_dir = config_dir.resolve()
        self.actor = actor
        self.runner = runner or Runner()
        self.roles = self._load_json("roles.json")
        self.actors = self._load_json("actors.json")
        self.services = self._load_json("services.json")
        self.limits = self._load_json("limits.json")
        self.repository = self._load_json("repository.json")
        self.role = self.actors.get(actor)
        self.state_path = self.root / "cadre" / "state" / "mission-control.json"
        self.rate_path = self.root / "cadre" / "state" / "invocation-rate.json"
        self.operation_lock_path = self.root / "logs" / "operations.lock"
        self.audit = AuditLedger(
            self.root / "logs" / "audit" / "operations.jsonl",
            max_bytes=int(self.limits["audit_max_bytes"]),
        )
        self.releases = self.root / "releases"
        self.current_link = self.root / "apps" / "cadre" / "current"
        self.previous_link = self.root / "apps" / "cadre" / "previous"
        self.secrets_file = self.root / "secrets" / "cadre.env"
        self.compose_file = self.config_dir / "docker-compose.prod.yml"
        self.repository_url, self.repository_branch, self.repository_mirror = self._repository_policy()

    def _load_json(self, name: str) -> dict[str, Any]:
        path = self.config_dir / name
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise OperationError(f"Operations configuration unavailable: {name}") from exc
        if not isinstance(payload, dict):
            raise OperationError(f"Operations configuration is invalid: {name}")
        return payload

    def _repository_policy(self) -> tuple[str, str, Path]:
        url = str(self.repository.get("url", ""))
        branch = str(self.repository.get("branch", ""))
        mirror = Path(str(self.repository.get("mirror_path", "")))
        parsed = urllib.parse.urlsplit(url)
        if (
            parsed.scheme != "https"
            or parsed.hostname != "github.com"
            or parsed.username
            or parsed.password
            or parsed.query
            or parsed.fragment
            or not parsed.path.endswith(".git")
        ):
            raise OperationError("Canonical repository policy must use a credential-free GitHub HTTPS URL.")
        if not BRANCH_RE.fullmatch(branch) or branch != "main":
            raise OperationError("Canonical deployment branch must be main.")
        if not mirror.is_absolute():
            raise OperationError("Canonical repository mirror path must be absolute.")
        try:
            mirror.resolve().relative_to((self.root / "shared").resolve())
        except ValueError as exc:
            raise OperationError("Canonical repository mirror must remain under the LANSEIR shared root.") from exc
        return url, branch, mirror.resolve()

    @contextmanager
    def _operation_guard(self) -> Iterator[None]:
        self.operation_lock_path.parent.mkdir(parents=True, exist_ok=True)
        flags = os.O_RDWR | os.O_CREAT
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        fd = os.open(self.operation_lock_path, flags, 0o640)
        with os.fdopen(fd, "r+") as handle:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
            fcntl.flock(handle.fileno(), fcntl.LOCK_UN)

    def _enforce_rate(self, action: str) -> None:
        intervals = self.limits.get("action_min_interval_seconds", {})
        interval = float(intervals.get(action, self.limits.get("default_action_min_interval_seconds", 1)))
        if interval <= 0:
            return
        try:
            state = json.loads(self.rate_path.read_text(encoding="utf-8")) if self.rate_path.exists() else {}
        except (OSError, json.JSONDecodeError) as exc:
            raise OperationError("Invocation-rate state is unavailable; operations are fail-closed.") from exc
        key = f"{self.actor}:{action}"
        now = time.time()
        last = float(state.get(key, 0))
        remaining = interval - (now - last)
        if remaining > 0:
            time.sleep(min(remaining, interval))
            now = time.time()
        state[key] = now
        atomic_json(self.rate_path, state)

    def _initial_state(self) -> dict[str, Any]:
        agents = []
        for role_id, config in self.roles.items():
            agents.append(
                {
                    "agent_id": role_id,
                    "name": config["name"],
                    "role": config["role"],
                    "capabilities": config.get("capabilities", []),
                    "permissions": config.get("actions", []),
                    "model_policy": config.get("model_policy", "local-first"),
                    "tools": config.get("tools", []),
                    "status": config.get("status", "AVAILABLE"),
                    "current_assignment": None,
                    "last_activity": None,
                }
            )
        return {
            "system": "DEGRADED",
            "deployment": "QUEUED",
            "current_release": self.current_release(),
            "last_known_good_release": self._read_release_link(self.previous_link),
            "last_operation": None,
            "updated_at": utc_now(),
            "agents": agents,
        }

    def read_state(self) -> dict[str, Any]:
        if self.state_path.is_file():
            try:
                return json.loads(self.state_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                pass
        return self._initial_state()

    def write_state(self, **updates: Any) -> dict[str, Any]:
        state = self.read_state()
        state.update(updates)
        state["updated_at"] = utc_now()
        for agent in state.get("agents", []):
            if agent.get("agent_id") == self.role:
                agent["last_activity"] = state["updated_at"]
                agent["current_assignment"] = updates.get("last_operation")
        atomic_json(self.state_path, state, mode=0o644)
        return state

    def _read_release_link(self, link: Path) -> str | None:
        if not link.is_symlink():
            return None
        try:
            resolved = link.resolve(strict=True)
            resolved.relative_to(self.releases.resolve())
        except (OSError, ValueError):
            return None
        return resolved.name if RELEASE_RE.fullmatch(resolved.name) else None

    def current_release(self) -> str | None:
        return self._read_release_link(self.current_link)

    def authorize(self, action: str, target: str | None) -> None:
        if not self.role or self.role not in self.roles:
            raise OperationError("Actor is not mapped to an operations role.", 77)
        policy = self.roles[self.role]
        if action not in policy.get("actions", []):
            raise OperationError(f"Role {self.role} is not permitted to run {action}.", 77)
        if action in SERVICE_TARGET_ACTIONS:
            service_name = safe_service(target or "")
            service = self.services.get(service_name)
            if not service or not service.get("enabled", False):
                raise OperationError("Target is not an enabled allowlisted service.", 77)
            if service_name not in policy.get("service_targets", []):
                raise OperationError(f"Role {self.role} is not permitted to target {service_name}.", 77)
        elif action in RELEASE_TARGET_ACTIONS:
            safe_release_id(target or "")
        elif target is not None:
            raise OperationError(f"Action {action} does not accept a target.", 64)

    def _read_env_file(self) -> dict[str, str]:
        if not self.secrets_file.is_file():
            raise OperationError("Production secret file is missing.")
        mode = self.secrets_file.stat().st_mode & 0o777
        expected_uid = 0 if os.geteuid() == 0 else os.getuid()
        if mode != 0o600 or self.secrets_file.stat().st_uid != expected_uid:
            raise OperationError("Production secret file owner or mode is unsafe.")
        values: dict[str, str] = {}
        for raw_line in self.secrets_file.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#"):
                continue
            key, separator, value = line.partition("=")
            if not separator or not key:
                raise OperationError("Production secret file contains an invalid assignment.")
            values[key] = value
        return values

    def validate_secrets(self) -> dict[str, Any]:
        values = self._read_env_file()
        required = {
            "CADRE_DB_PASSWORD",
            "CADRE_DATABASE_URL",
            "CADRE_PUBLIC_HOST",
            "CADRE_ACME_EMAIL",
            "CADRE_ADMIN_EMAILS",
            "CADRE_API_TOKENS_JSON",
        }
        missing = sorted(name for name in required if not values.get(name))
        if missing:
            raise OperationError(f"Production secret file is missing required names: {', '.join(missing)}")
        lowered = "\n".join(values[name].lower() for name in required)
        if any(marker in lowered for marker in ("change_me", "replace_with", "example.com")):
            raise OperationError("Production secret file still contains template values.")
        if any("$" in values[name] or any(character.isspace() for character in values[name]) for name in required):
            raise OperationError("Production secret values may not contain interpolation or whitespace syntax.")

        password = values["CADRE_DB_PASSWORD"]
        if len(password) < 24 or len(set(password)) < 10 or max(password.count(character) for character in set(password)) > len(password) // 3:
            raise OperationError("Database password does not meet the production length policy.")
        try:
            parsed = urllib.parse.urlsplit(values["CADRE_DATABASE_URL"])
            database_port = parsed.port
        except ValueError as exc:
            raise OperationError("Database URL is inconsistent with the fixed production database policy.") from exc
        if (
            parsed.scheme != "postgresql+psycopg"
            or parsed.username != "cadre"
            or parsed.hostname != "db"
            or database_port not in {None, 5432}
            or parsed.path != "/cadre"
            or parsed.query
            or parsed.fragment
            or urllib.parse.unquote(parsed.password or "") != password
        ):
            raise OperationError("Database URL is inconsistent with the fixed production database policy.")
        host = values["CADRE_PUBLIC_HOST"]
        email = values["CADRE_ACME_EMAIL"]
        admin_emails = values["CADRE_ADMIN_EMAILS"].split(",")
        if (
            not re.fullmatch(r"(?=.{1,253}\Z)(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", host)
            or not re.fullmatch(r"[^@\s]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", email)
            or not admin_emails
            or any(not re.fullmatch(r"[^@\s]+@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+[A-Za-z]{2,63}", item) for item in admin_emails)
        ):
            raise OperationError("Production host or operator email policy is invalid.")

        try:
            tokens = json.loads(values["CADRE_API_TOKENS_JSON"])
        except json.JSONDecodeError as exc:
            raise OperationError("API service-token policy is not valid JSON.") from exc
        required_roles = {"mission_control", "al", "invictus", "porter", "griot", "sentinel"}
        allowed_roles = required_roles | {"arc"}
        if not isinstance(tokens, dict) or not required_roles.issubset(tokens) or set(tokens) - allowed_roles:
            raise OperationError("API service-token policy is missing required roles.")
        token_values = []
        for role in tokens:
            token = tokens.get(role)
            if (
                not isinstance(token, str)
                or len(token) < 32
                or len(set(token)) < 10
                or max(token.count(character) for character in set(token)) > len(token) // 3
                or "change" in token.lower()
                or "replace" in token.lower()
                or "$" in token
            ):
                raise OperationError("API service-token policy contains an unsafe token.")
            token_values.append(token)
        if len(set(token_values)) != len(token_values):
            raise OperationError("API service tokens must be unique per role.")
        return {"valid": True, "required_names": sorted(required), "token_roles": sorted(tokens)}

    def _compose_command(self, *arguments: str) -> tuple[list[str], dict[str, str]]:
        if not self.compose_file.is_file():
            raise OperationError("Root-owned production Compose policy is missing.")
        self.validate_secrets()
        command = [
            "docker",
            "compose",
            "--project-name",
            "lanseir-cadre",
            "--env-file",
            str(self.secrets_file),
            "-f",
            str(self.compose_file),
            *arguments,
        ]
        env = {
            "PATH": SAFE_PATH,
            "DOCKER_HOST": "unix:///var/run/docker.sock",
            "CADRE_RELEASE_PATH": str(self.current_link),
            "CADRE_RELEASE_ID": self.current_release() or "none",
        }
        return command, env

    def _compose(self, *arguments: str, timeout: int = 600, input_bytes: bytes | None = None):
        command, env = self._compose_command(*arguments)
        return self.runner.run(command, env=env, input_bytes=input_bytes, timeout=timeout)

    @staticmethod
    def _result(completed: subprocess.CompletedProcess[bytes]) -> dict[str, Any]:
        stdout = completed.stdout.decode("utf-8", "replace")[-MAX_OUTPUT:]
        stderr = completed.stderr.decode("utf-8", "replace")[-MAX_OUTPUT:]
        return {"ok": completed.returncode == 0, "exit_status": completed.returncode, "stdout": stdout, "stderr": stderr}

    def _health(self) -> dict[str, Any]:
        expected = self.current_release()
        if not expected:
            return {"healthy": False, "error": "No active release is selected."}
        running = self._result(self._compose("ps", "--status", "running", "--services", "api", timeout=60))
        if not running["ok"] or "api" not in running["stdout"].splitlines():
            return {"healthy": False, "error": "Compose API service is not running.", "service": running}
        script = (
            "import json,urllib.request;"
            "r=urllib.request.urlopen('http://127.0.0.1:8000/api/v1/health',timeout=3);"
            "print(json.dumps(json.load(r)))"
        )
        completed = self._compose("exec", "-T", "api", "python", "-c", script, timeout=30)
        result = self._result(completed)
        if not result["ok"]:
            return {"healthy": False, "error": "Compose API health request failed.", "service": result}
        try:
            payload = json.loads(result["stdout"].strip().splitlines()[-1])
        except (IndexError, json.JSONDecodeError):
            return {"healthy": False, "error": "Compose API returned invalid health data."}
        healthy = payload.get("status") == "ok" and payload.get("release") == expected
        return {"healthy": healthy, "release": expected, "payload": payload}

    def _wait_for_health(self, attempts: int = 30) -> dict[str, Any]:
        result: dict[str, Any] = {"healthy": False}
        for _ in range(attempts):
            result = self._health()
            if result.get("healthy"):
                return result
            time.sleep(2)
        return result

    def _atomic_link(self, target: Path, link: Path) -> None:
        link.parent.mkdir(parents=True, exist_ok=True)
        temp_link = link.parent / f".{link.name}.{os.getpid()}"
        if temp_link.exists() or temp_link.is_symlink():
            temp_link.unlink()
        temp_link.symlink_to(target)
        os.replace(temp_link, link)
        fsync_directory(link.parent)

    def _remove_release_link(self, link: Path) -> None:
        if link.exists() or link.is_symlink():
            link.unlink()
            fsync_directory(link.parent)

    def _git_env(self) -> dict[str, str]:
        return {
            "PATH": SAFE_PATH,
            "GIT_TERMINAL_PROMPT": "0",
            "GIT_CONFIG_NOSYSTEM": "1",
            "HOME": "/nonexistent",
        }

    def _git(self, *arguments: str, timeout: int = 300) -> subprocess.CompletedProcess[bytes]:
        return self.runner.run(["git", *arguments], env=self._git_env(), timeout=timeout)

    def _require_git_success(self, completed: subprocess.CompletedProcess[bytes], message: str) -> str:
        if completed.returncode != 0:
            detail = completed.stderr.decode("utf-8", "replace")[-MAX_OUTPUT:]
            raise OperationError(f"{message}: {detail or 'git command failed'}")
        return completed.stdout.decode("utf-8", "replace").strip()

    def _fetch_canonical_release(self, release: str) -> None:
        self.repository_mirror.parent.mkdir(parents=True, exist_ok=True)
        if not self.repository_mirror.exists():
            initialized = self._git("init", "--bare", str(self.repository_mirror))
            self._require_git_success(initialized, "Unable to initialize canonical repository mirror")
            added = self._git("--git-dir", str(self.repository_mirror), "remote", "add", "origin", self.repository_url)
            self._require_git_success(added, "Unable to configure canonical repository origin")
        if not self.repository_mirror.is_dir():
            raise OperationError("Canonical repository mirror path is not a directory.")
        origin = self._git("--git-dir", str(self.repository_mirror), "remote", "get-url", "origin")
        if self._require_git_success(origin, "Unable to inspect canonical repository origin") != self.repository_url:
            raise OperationError("Canonical repository origin does not match root-owned policy.")
        remote_ref = f"refs/remotes/origin/{self.repository_branch}"
        fetch = self._git(
            "--git-dir",
            str(self.repository_mirror),
            "fetch",
            "--force",
            "--prune",
            "origin",
            f"+refs/heads/{self.repository_branch}:{remote_ref}",
            timeout=900,
        )
        self._require_git_success(fetch, "Unable to fetch canonical deployment branch")
        resolved = self._git("--git-dir", str(self.repository_mirror), "rev-parse", f"{release}^{{commit}}")
        if self._require_git_success(resolved, "Release commit is absent from canonical repository") != release:
            raise OperationError("Release ID did not resolve to the exact canonical commit.")
        ancestry = self._git("--git-dir", str(self.repository_mirror), "merge-base", "--is-ancestor", release, remote_ref)
        if ancestry.returncode != 0:
            raise OperationError("Release commit is not an ancestor of canonical main.")

    def _materialize_release(self, release: str) -> Path:
        destination = self.releases / release
        if destination.exists():
            provenance = destination / "RELEASE_PROVENANCE.json"
            try:
                data = json.loads(provenance.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise OperationError("Existing release lacks valid provenance and will not be reused.") from exc
            if data.get("commit") != release or data.get("repository") != self.repository_url:
                raise OperationError("Existing release provenance does not match requested canonical commit.")
            return destination

        self.releases.mkdir(parents=True, exist_ok=True)
        staging = self.releases / f".{release}.staging-{os.getpid()}"
        if staging.exists():
            raise OperationError("Release staging path already exists.")
        staging.mkdir(mode=0o750)
        fd, archive_name = tempfile.mkstemp(prefix=f".{release}.", suffix=".tar", dir=self.releases)
        os.close(fd)
        archive = Path(archive_name)
        try:
            generated = self._git(
                "--git-dir",
                str(self.repository_mirror),
                "archive",
                "--format=tar",
                f"--output={archive}",
                release,
                timeout=900,
            )
            self._require_git_success(generated, "Unable to generate canonical release archive")
            safe_extract(
                archive,
                staging,
                max_archive_bytes=int(self.limits["release_max_archive_bytes"]),
                max_expanded_bytes=int(self.limits["release_max_expanded_bytes"]),
                max_members=int(self.limits["release_max_members"]),
                max_file_bytes=int(self.limits["release_max_file_bytes"]),
            )
            required = ["app/main.py", "pyproject.toml", "VERSION"]
            missing = [name for name in required if not (staging / name).is_file()]
            if missing:
                raise OperationError(f"Release is missing required files: {', '.join(missing)}")
            shutil.copy2(self.config_dir / "Dockerfile.prod", staging / "Dockerfile.ops")
            atomic_json(
                staging / "RELEASE_PROVENANCE.json",
                {
                    "repository": self.repository_url,
                    "branch": self.repository_branch,
                    "commit": release,
                    "fetched_at": utc_now(),
                },
            )
            os.rename(staging, destination)
        except Exception:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        finally:
            archive.unlink(missing_ok=True)
        return destination

    def status(self, _: str | None) -> dict[str, Any]:
        completed = self._compose("ps", "--format", "json", timeout=60)
        result = self._result(completed)
        return {
            "system": "HEALTHY" if result["ok"] and self._health().get("healthy") else "DEGRADED",
            "current_release": self.current_release(),
            "services": result,
            "audit": self.audit.verify(),
        }

    def health(self, _: str | None) -> dict[str, Any]:
        return self._health()

    def system_health(self, _: str | None) -> dict[str, Any]:
        usage = shutil.disk_usage(self.root)
        return {
            "disk": {
                "total_bytes": usage.total,
                "used_bytes": usage.used,
                "free_bytes": usage.free,
                "percent_used": round((usage.used / usage.total) * 100, 2),
            },
            "load_average": list(os.getloadavg()) if hasattr(os, "getloadavg") else None,
            "application": self._health(),
            "current_release": self.current_release(),
            "audit": self.audit.verify(),
        }

    def validate(self, _: str | None) -> dict[str, Any]:
        secret_policy = self.validate_secrets()
        compose = self._result(self._compose("config", "--quiet", timeout=60))
        health = self._health()
        return {
            "valid": secret_policy["valid"] and compose["ok"] and health.get("healthy", False),
            "secrets": secret_policy,
            "compose": compose,
            "health": health,
        }

    def deploy(self, release_id: str | None) -> dict[str, Any]:
        release = safe_release_id(release_id or "")
        self.validate_secrets()
        self._fetch_canonical_release(release)
        destination = self._materialize_release(release)

        old_release = self.current_release()
        if old_release:
            self._atomic_link(self.releases / old_release, self.previous_link)
        self._atomic_link(destination, self.current_link)
        self.write_state(deployment="BUILDING", current_release=release, last_operation="deploy")

        build = {"ok": False, "exit_status": 1, "stdout": "", "stderr": "build not started"}
        up = {"ok": False, "exit_status": 1, "stdout": "", "stderr": "startup not started"}
        try:
            build = self._result(self._compose("build", "api", timeout=1200))
            up = (
                self._result(self._compose("up", "-d", "--remove-orphans", timeout=600))
                if build["ok"]
                else {"ok": False, "exit_status": 1, "stdout": "", "stderr": "build failed"}
            )
            health = self._wait_for_health() if up["ok"] else {"healthy": False, "error": "compose startup failed"}
        except Exception as exc:
            health = {"healthy": False, "error": f"activation exception: {type(exc).__name__}"}

        if not health.get("healthy"):
            rollback = None
            rollback_health = {"healthy": False, "error": "no previous release"}
            shutdown = None
            try:
                if old_release:
                    self._atomic_link(self.releases / old_release, self.current_link)
                    rollback = self._result(self._compose("up", "-d", "--remove-orphans", timeout=600))
                    if rollback["ok"]:
                        rollback_health = self._wait_for_health()
                else:
                    shutdown = self._result(self._compose("down", "--remove-orphans", timeout=600))
                    if shutdown["ok"]:
                        self._remove_release_link(self.current_link)
            except Exception as exc:
                rollback_health = {"healthy": False, "error": f"recovery exception: {type(exc).__name__}"}
            recovered = bool(old_release and rollback and rollback["ok"] and rollback_health.get("healthy"))
            clean_first_failure = bool(not old_release and shutdown and shutdown["ok"] and self.current_release() is None)
            self.write_state(
                system="DEGRADED" if recovered else "FAILED",
                deployment="ROLLED_BACK" if recovered else ("FAILED" if clean_first_failure else "RECOVERY_REQUIRED"),
                current_release=self.current_release(),
                last_known_good_release=old_release if recovered else self.read_state().get("last_known_good_release"),
                last_operation="deploy",
            )
            raise OperationError(
                json.dumps(
                    {
                        "build_ok": build["ok"],
                        "up_ok": up["ok"],
                        "health": health,
                        "rollback_ok": rollback["ok"] if rollback else False,
                        "rollback_health": rollback_health,
                        "recovered": recovered,
                        "clean_first_failure": clean_first_failure,
                    }
                )
            )

        self.write_state(
            system="HEALTHY",
            deployment="LIVE",
            current_release=release,
            last_known_good_release=release,
            last_operation="deploy",
        )
        return {"deployed": True, "release": release, "previous_release": old_release, "health": health}

    def rollback(self, _: str | None) -> dict[str, Any]:
        previous = self._read_release_link(self.previous_link)
        current = self.current_release()
        if not previous:
            raise OperationError("No validated previous release is available for rollback.")
        self._atomic_link(self.releases / previous, self.current_link)
        try:
            result = self._result(self._compose("up", "-d", "--remove-orphans", timeout=600))
            health = self._wait_for_health() if result["ok"] else {"healthy": False}
        except Exception as exc:
            result = {"ok": False, "exit_status": 1, "stdout": "", "stderr": type(exc).__name__}
            health = {"healthy": False, "error": f"rollback exception: {type(exc).__name__}"}
        if not health.get("healthy"):
            restored = False
            restoration_health = {"healthy": False}
            try:
                if current:
                    self._atomic_link(self.releases / current, self.current_link)
                    restoration = self._result(self._compose("up", "-d", "--remove-orphans", timeout=600))
                    restoration_health = self._wait_for_health() if restoration["ok"] else {"healthy": False}
                    restored = bool(restoration["ok"] and restoration_health.get("healthy"))
                else:
                    shutdown = self._result(self._compose("down", "--remove-orphans", timeout=600))
                    if shutdown["ok"]:
                        self._remove_release_link(self.current_link)
            except Exception as exc:
                restoration_health = {"healthy": False, "error": f"restoration exception: {type(exc).__name__}"}
            self.write_state(
                system="DEGRADED" if restored else "FAILED",
                deployment="LIVE" if restored else "RECOVERY_REQUIRED",
                current_release=self.current_release(),
                last_operation="rollback",
            )
            raise OperationError(
                "Rollback candidate failed; original release was restored and verified."
                if restored
                else "Rollback candidate failed and original release could not be verified; recovery is required."
            )
        if current:
            self._atomic_link(self.releases / current, self.previous_link)
        self.write_state(
            system="HEALTHY",
            deployment="ROLLED_BACK",
            current_release=previous,
            last_known_good_release=previous,
            last_operation="rollback",
        )
        return {"rolled_back": True, "current_release": previous, "replaced_release": current}

    def restart(self, target: str | None) -> dict[str, Any]:
        service = safe_service(target or "")
        result = self._result(self._compose("restart", service, timeout=180))
        if not result["ok"]:
            raise OperationError(result["stderr"] or "Service restart failed.", result["exit_status"])
        return {"restarted": service, "health": self._health()}

    def logs(self, target: str | None) -> dict[str, Any]:
        service = safe_service(target or "")
        result = self._result(self._compose("logs", "--no-color", "--tail", "200", service, timeout=60))
        if not result["ok"]:
            raise OperationError(result["stderr"] or "Unable to read service logs.", result["exit_status"])
        return {"service": service, "logs": result["stdout"]}

    def release_current(self, _: str | None) -> dict[str, Any]:
        return {"current_release": self.current_release(), "previous_release": self._read_release_link(self.previous_link)}

    def release_history(self, _: str | None) -> dict[str, Any]:
        releases = (
            sorted(
                (path.name for path in self.releases.iterdir() if path.is_dir() and RELEASE_RE.fullmatch(path.name)),
                reverse=True,
            )
            if self.releases.exists()
            else []
        )
        return {"releases": releases, "current_release": self.current_release()}

    def _completed_backups(self) -> list[Path]:
        root = self.root / "backups"
        if not root.exists():
            return []
        return sorted(
            (path for path in root.iterdir() if path.is_dir() and BACKUP_RE.fullmatch(path.name)),
            reverse=True,
        )

    def _partial_backups(self) -> list[Path]:
        root = self.root / "backups"
        if not root.exists():
            return []
        return sorted(
            (
                path
                for path in root.iterdir()
                if path.is_dir() and path.name.startswith(".") and path.name.endswith(".partial")
            ),
            key=lambda path: path.stat().st_mtime,
            reverse=True,
        )

    def _backup_preflight(self) -> dict[str, Any]:
        backups = self._completed_backups()
        partials = self._partial_backups()
        all_sets = sorted((*backups, *partials), key=lambda path: path.stat().st_mtime, reverse=True)
        maximum = int(self.limits["backup_max_local_sets"])
        if len(all_sets) >= maximum:
            raise OperationError("Local backup limit reached; verify off-server copy before authorized pruning.")
        usage = shutil.disk_usage(self.root)
        required_free = max(
            int(self.limits["backup_min_free_bytes"]),
            int(usage.total * (float(self.limits["backup_min_free_percent"]) / 100)),
        )
        if usage.free < required_free:
            raise OperationError("Insufficient free space for a governed backup.")
        if all_sets:
            minimum_interval = int(self.limits["backup_min_interval_seconds"])
            age = time.time() - all_sets[0].stat().st_mtime
            if age < minimum_interval:
                raise OperationError(f"Backup frequency limit active; retry after {int(minimum_interval - age) + 1} seconds.", 75)
        return {
            "count": len(all_sets),
            "complete_count": len(backups),
            "partial_count": len(partials),
            "maximum": maximum,
            "free_bytes": usage.free,
            "required_free_bytes": required_free,
        }

    def backup(self, _: str | None) -> dict[str, Any]:
        policy = self._backup_preflight()
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        backup_root = self.root / "backups"
        backup_root.mkdir(parents=True, exist_ok=True)
        destination = backup_root / stamp
        staging = backup_root / f".{stamp}.partial"
        staging.mkdir(mode=0o750)
        database_path = staging / "cadre-postgres.sql.gz"
        try:
            command, env = self._compose_command("exec", "-T", "db", "pg_dump", "-U", "cadre", "-d", "cadre")
            returncode, error = self.runner.stream_stdout_to_gzip(
                command,
                database_path,
                timeout=900,
                env=env,
                max_input_bytes=int(self.limits["backup_max_database_dump_bytes"]),
                minimum_free_bytes=int(policy["required_free_bytes"]),
            )
            if returncode != 0:
                raise OperationError(error or "Database backup failed.")

            state_archive = staging / "operations-state.tar.gz"
            with tarfile.open(state_archive, "w:gz") as bundle:
                for source, name in (
                    (self.root / "cadre" / "state", "cadre-state"),
                    (self.root / "logs" / "audit", "audit"),
                    (self.config_dir, "operations-policy"),
                ):
                    if source.exists():
                        bundle.add(source, arcname=name, recursive=True)
            manifest = {
                "created_at": utc_now(),
                "release": self.current_release(),
                "files": {
                    database_path.name: sha256_file(database_path),
                    state_archive.name: sha256_file(state_archive),
                },
                "secrets_included": False,
                "off_server_copy": "REQUIRED",
            }
            atomic_json(staging / "manifest.json", manifest)
            os.rename(staging, destination)
        except BaseException:
            shutil.rmtree(staging, ignore_errors=True)
            raise
        return {"backup": stamp, "manifest": manifest, "policy": policy}

    def backup_status(self, _: str | None) -> dict[str, Any]:
        backups = self._completed_backups()
        usage = shutil.disk_usage(self.root)
        return {
            "latest": backups[0].name if backups else None,
            "count": len(backups),
            "maximum_local_sets": int(self.limits["backup_max_local_sets"]),
            "free_bytes": usage.free,
            "off_server_copy": "REQUIRED",
        }

    def _latest_backup(self) -> Path:
        backups = self._completed_backups()
        if not backups:
            raise OperationError("No complete backup is available.")
        return backups[0]

    def backup_verify(self, _: str | None) -> dict[str, Any]:
        backup = self._latest_backup()
        manifest = json.loads((backup / "manifest.json").read_text(encoding="utf-8"))
        checks = {}
        for name, expected in manifest["files"].items():
            if PurePosixPath(name).name != name:
                raise OperationError("Backup manifest contains an unsafe filename.")
            path = backup / name
            checks[name] = path.is_file() and sha256_file(path) == expected
        with gzip.open(backup / "cadre-postgres.sql.gz", "rb") as handle:
            while handle.read(1024 * 1024):
                pass
        if not all(checks.values()):
            raise OperationError("Backup integrity verification failed.")
        return {"backup": backup.name, "verified": True, "checks": checks}

    def restore_test(self, _: str | None) -> dict[str, Any]:
        backup = self._latest_backup()
        self.backup_verify(None)
        restore_db = f"cadre_restore_{uuid.uuid4().hex[:12]}"
        create = self._result(self._compose("exec", "-T", "db", "createdb", "-U", "cadre", restore_db, timeout=120))
        if not create["ok"]:
            raise OperationError(create["stderr"] or "Unable to create isolated restore database.")
        try:
            command, env = self._compose_command(
                "exec",
                "-T",
                "db",
                "psql",
                "-v",
                "ON_ERROR_STOP=1",
                "-U",
                "cadre",
                "-d",
                restore_db,
            )
            returncode, error = self.runner.stream_gzip_to_stdin(
                backup / "cadre-postgres.sql.gz", command, timeout=900, env=env
            )
            verify = self._result(
                self._compose("exec", "-T", "db", "psql", "-U", "cadre", "-d", restore_db, "-tAc", "SELECT 1", timeout=60)
            )
            if returncode != 0 or not verify["ok"] or verify["stdout"].strip() != "1":
                raise OperationError(error or "Isolated restore test failed.")
            return {"backup": backup.name, "restore_test": "PASSED"}
        finally:
            self._compose("exec", "-T", "db", "dropdb", "-U", "cadre", "--if-exists", restore_db, timeout=120)

    def security_audit(self, _: str | None) -> dict[str, Any]:
        commands = {
            "sshd": ["/usr/sbin/sshd", "-T"],
            "firewall": ["ufw", "status", "verbose"],
            "fail2ban": ["fail2ban-client", "status"],
            "listening_ports": ["ss", "-lntup"],
            "docker": ["docker", "info", "--format", "{{json .SecurityOptions}}"],
        }
        checks: dict[str, Any] = {}
        safe_env = {"PATH": SAFE_PATH, "DOCKER_HOST": "unix:///var/run/docker.sock"}
        for name, command in commands.items():
            executable = command[0]
            if not (Path(executable).is_file() if executable.startswith("/") else shutil.which(executable, path=SAFE_PATH)):
                checks[name] = {"available": False}
                continue
            result = self.runner.run(command, timeout=60, env=safe_env)
            checks[name] = {
                "available": True,
                "exit_status": result.returncode,
                "output": result.stdout.decode("utf-8", "replace")[-MAX_OUTPUT:],
                "error": result.stderr.decode("utf-8", "replace")[-MAX_OUTPUT:],
            }
        permission_checks = {}
        for path, expected in ((self.root / "secrets", 0o700), (self.config_dir, 0o750)):
            if path.exists():
                permission_checks[str(path)] = {
                    "mode": oct(path.stat().st_mode & 0o777),
                    "expected": oct(expected),
                    "pass": (path.stat().st_mode & 0o777) == expected,
                }
        report = {"created_at": utc_now(), "checks": checks, "permissions": permission_checks}
        report_path = self.root / "logs" / "security" / f"audit-{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}.json"
        atomic_json(report_path, report)
        return {"report": str(report_path), "checks": checks, "permissions": permission_checks}

    def _safe_summary(self, result: dict[str, Any]) -> dict[str, Any]:
        excluded = {"logs", "stdout", "stderr", "checks", "payload", "service"}
        summary = {key: value for key, value in result.items() if key not in excluded}
        if "error" in summary:
            summary["error"] = "operation failed; inspect protected command output"
        return summary

    def execute(self, action: str, target: str | None = None) -> tuple[int, dict[str, Any]]:
        operation_id = hashlib.sha256(f"{utc_now()}:{self.actor}:{action}:{target}:{uuid.uuid4().hex}".encode()).hexdigest()[:16]
        started = utc_now()
        intent: dict[str, Any] | None = None
        result: dict[str, Any]
        exit_status = 1
        outcome = "FAILED"
        with self._operation_guard():
            try:
                self.authorize(action, target)
                self._enforce_rate(action)
                if action in AUDIT_GATED_ACTIONS:
                    self.audit.assert_ready()
                    intent = self.audit.append(
                        {
                            "operation_id": operation_id,
                            "timestamp": started,
                            "actor": self.actor,
                            "role": self.role,
                            "action": action,
                            "target": target,
                            "phase": "INTENT",
                            "result": "PENDING",
                        }
                    )
                self.write_state(last_operation=action)
                handlers = {
                    "status": self.status,
                    "health": self.health,
                    "deploy": self.deploy,
                    "validate": self.validate,
                    "rollback": self.rollback,
                    "restart": self.restart,
                    "logs": self.logs,
                    "backup": self.backup,
                    "backup-status": self.backup_status,
                    "backup-verify": self.backup_verify,
                    "restore-test": self.restore_test,
                    "release-current": self.release_current,
                    "release-history": self.release_history,
                    "system-health": self.system_health,
                    "security-audit": self.security_audit,
                    "audit-verify": lambda _: self.audit.verify(),
                }
                if action not in handlers:
                    raise OperationError("Unknown operation.", 64)
                result = handlers[action](target)
                exit_status = 0
                outcome = "SUCCESS"
            except OperationError as exc:
                result = {"error": str(exc)}
                exit_status = exc.exit_status
                outcome = "REJECTED" if exit_status in {64, 75, 77} else "FAILED"
            except Exception as exc:  # fail closed; do not expose command internals in the receipt
                result = {"error": f"{type(exc).__name__}: {exc}"}
                exit_status = 1
                outcome = "FAILED"

            try:
                record = self.audit.append(
                    {
                        "operation_id": operation_id,
                        "timestamp": started,
                        "completed_at": utc_now(),
                        "actor": self.actor,
                        "role": self.role,
                        "action": action,
                        "target": target,
                        "phase": "TERMINAL",
                        "result": outcome,
                        "exit_status": exit_status,
                        "current_release": self.current_release(),
                        "summary": self._safe_summary(result),
                    }
                )
                result["receipt"] = {
                    "operation_id": operation_id,
                    "intent_hash": intent["record_hash"] if intent else None,
                    "record_hash": record["record_hash"],
                }
            except Exception as audit_error:
                if action in AUDIT_GATED_ACTIONS:
                    result = {
                        "error": (
                            "Audit durability unavailable; protected output was suppressed."
                            if action in PROTECTED_READ_ACTIONS
                            else "Audit durability unavailable; privileged result was suppressed."
                        )
                    }
                else:
                    result["audit_error"] = "Audit terminal receipt could not be completed; inspect protected audit state."
                exit_status = 1
        return exit_status, result


def default_paths() -> tuple[Path, Path]:
    if os.geteuid() == 0:
        return Path("/opt/lanseir"), Path("/etc/lanseir/operations")
    return (
        Path(os.environ.get("LANSEIR_ROOT", "/opt/lanseir")),
        Path(os.environ.get("LANSEIR_OPS_CONFIG", "/etc/lanseir/operations")),
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Governed LANSEIR/CADRE host operations")
    parser.add_argument(
        "action",
        choices=(
            "status",
            "health",
            "deploy",
            "validate",
            "rollback",
            "restart",
            "logs",
            "backup",
            "backup-status",
            "backup-verify",
            "restore-test",
            "release-current",
            "release-history",
            "system-health",
            "security-audit",
            "audit-verify",
        ),
    )
    parser.add_argument("target", nargs="?")
    args = parser.parse_args()
    root, config_dir = default_paths()
    actor = os.environ.get("SUDO_USER") or getpass.getuser()
    controller = Controller(root, config_dir, actor)
    exit_status, result = controller.execute(args.action, args.target)
    print(json.dumps(result, indent=2, sort_keys=True))
    return exit_status


if __name__ == "__main__":
    raise SystemExit(main())
