#!/usr/bin/env python3
"""Validate the promoted LANSEIR/CADRE foundation records and registry."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path
from typing import Any


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
PROVENANCE_ROOT = (
    REPOSITORY_ROOT / "provenance" / "LANSEIR_CADRE_FOUNDATION_SYNC_v1.0.0"
)
MANIFEST_PATH = PROVENANCE_ROOT / "manifest.json"
REGISTRY_PATH = REPOSITORY_ROOT / "source_of_truth_registry.json"
PATH_OVERRIDES = {"README.md": PROVENANCE_ROOT / "README.md"}
EXPECTED_RECORD_PATHS = {
    "00_governance/lanseir_identity_charter.md",
    "00_governance/lanseir_operating_character.md",
    "00_governance/promotion_rule.md",
    "01_intelligence/cadre_presence_orientation_standard.md",
    "01_intelligence/cadre_synthesis_standard.md",
    "01_intelligence/lanseir_expression_profile.md",
    "02_operations/institutional_rhythm_standard.md",
    "03_migration/lanseir_inheritance_pack_spec.md",
    "04_workspaces/vessel_product_direction.md",
}


def _load_json(path: Path) -> dict[str, Any]:
    with path.open(encoding="utf-8") as handle:
        return json.load(handle)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def _installed_path(relative_path: str) -> Path:
    if relative_path in PATH_OVERRIDES:
        return PATH_OVERRIDES[relative_path]
    return REPOSITORY_ROOT / relative_path


def validate() -> list[str]:
    errors: list[str] = []

    try:
        manifest = _load_json(MANIFEST_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        return [f"Cannot load {MANIFEST_PATH.relative_to(REPOSITORY_ROOT)}: {exc}"]

    expected_metadata = {
        "package": "LANSEIR_CADRE_FOUNDATION_SYNC",
        "version": "1.0.0",
        "status": "CANONICAL_PROMOTION_PACKAGE",
        "promotion_signal": "FULL SEND",
    }
    for field, expected in expected_metadata.items():
        if manifest.get(field) != expected:
            errors.append(
                f"Manifest {field} is {manifest.get(field)!r}; expected {expected!r}"
            )

    entries = manifest.get("files")
    if not isinstance(entries, list):
        return errors + ["Manifest files must be a list"]

    manifest_hashes: dict[str, str] = {}
    for entry in entries:
        if not isinstance(entry, dict):
            errors.append("Manifest contains a non-object file entry")
            continue
        relative_path = entry.get("path")
        expected_hash = entry.get("sha256")
        if not isinstance(relative_path, str) or not isinstance(expected_hash, str):
            errors.append(f"Invalid manifest entry: {entry!r}")
            continue
        if relative_path in manifest_hashes:
            errors.append(f"Duplicate manifest path: {relative_path}")
            continue
        manifest_hashes[relative_path] = expected_hash

        installed_path = _installed_path(relative_path)
        if not installed_path.is_file():
            errors.append(f"Missing promoted file: {relative_path}")
            continue
        actual_hash = _sha256(installed_path)
        if actual_hash != expected_hash:
            errors.append(
                f"SHA-256 mismatch for {relative_path}: "
                f"expected {expected_hash}, found {actual_hash}"
            )

    try:
        registry = _load_json(REGISTRY_PATH)
    except (OSError, json.JSONDecodeError) as exc:
        return errors + [f"Cannot load source_of_truth_registry.json: {exc}"]

    records = registry.get("records")
    if not isinstance(records, list):
        return errors + ["Registry records must be a list"]

    record_ids: list[str] = []
    record_paths: list[str] = []
    for record in records:
        if not isinstance(record, dict):
            errors.append("Registry contains a non-object record")
            continue
        record_id = record.get("id")
        record_path = record.get("path")
        if not isinstance(record_id, str) or not isinstance(record_path, str):
            errors.append(f"Invalid registry record: {record!r}")
            continue
        record_ids.append(record_id)
        record_paths.append(record_path)
        if record_path not in manifest_hashes:
            errors.append(f"Registry path absent from package manifest: {record_path}")

    if len(record_ids) != len(set(record_ids)):
        errors.append("Registry IDs are not unique")
    if len(record_paths) != len(set(record_paths)):
        errors.append("Registry paths are not unique")
    if set(record_paths) != EXPECTED_RECORD_PATHS:
        missing = sorted(EXPECTED_RECORD_PATHS - set(record_paths))
        unexpected = sorted(set(record_paths) - EXPECTED_RECORD_PATHS)
        errors.append(
            f"Registry record set changed; missing={missing}, unexpected={unexpected}"
        )

    migration_critical = {
        record.get("id")
        for record in records
        if isinstance(record, dict) and record.get("migration_critical") is True
    }
    if migration_critical != {"LNS-EXP-001", "LNS-INH-001"}:
        errors.append(
            "Migration-critical registry IDs must be LNS-EXP-001 and LNS-INH-001"
        )

    return errors


def main() -> int:
    errors = validate()
    if errors:
        print("LANSEIR/CADRE foundation sync validation: FAIL", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print("LANSEIR/CADRE foundation sync validation: PASS")
    print("9 registry records and 11 package-manifest files verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
