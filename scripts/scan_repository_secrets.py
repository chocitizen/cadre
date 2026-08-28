#!/usr/bin/env python3
"""Fail safely when committed source contains a recognizable credential."""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_PARTS = {
    ".git",
    ".next",
    ".venv",
    ".venv-litellm",
    "__pycache__",
    ".mypy_cache",
    ".pytest_cache",
    "node_modules",
    "data",
    "playwright-report",
    "test-results",
}
PATTERNS = {
    "private-key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    "openai-key": re.compile(r"\bsk-(?:proj-)?[A-Za-z0-9_-]{20,}\b"),
    "github-token": re.compile(r"\b(?:gh[opsu]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,})\b"),
    "aws-access-key": re.compile(r"\b(?:AKIA|ASIA)[A-Z0-9]{16}\b"),
    "slack-token": re.compile(r"\bxox[baprs]-[A-Za-z0-9-]{20,}\b"),
}


def candidate_files() -> list[Path]:
    try:
        result = subprocess.run(
            ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
            cwd=ROOT,
            check=True,
            capture_output=True,
        )
        relative_paths = [Path(value.decode()) for value in result.stdout.split(b"\0") if value]
    except (OSError, subprocess.CalledProcessError, UnicodeDecodeError):
        relative_paths = [path.relative_to(ROOT) for path in ROOT.rglob("*") if path.is_file()]
    return sorted(
        ROOT / path
        for path in relative_paths
        if not (set(path.parts) & EXCLUDED_PARTS) and not path.name.startswith(".env")
    )


def scan() -> list[tuple[str, int, str]]:
    findings: list[tuple[str, int, str]] = []
    for path in candidate_files():
        try:
            if path.stat().st_size > 5_000_000:
                continue
            content = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_number, line in enumerate(content.splitlines(), start=1):
            for name, pattern in PATTERNS.items():
                if pattern.search(line):
                    findings.append((str(path.relative_to(ROOT)), line_number, name))
    return findings


def main() -> int:
    findings = scan()
    if findings:
        print("Repository credential scan: FAIL", file=sys.stderr)
        for path, line_number, kind in findings:
            print(f"- {path}:{line_number}: {kind}", file=sys.stderr)
        return 1
    print("Repository credential scan: PASS")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
