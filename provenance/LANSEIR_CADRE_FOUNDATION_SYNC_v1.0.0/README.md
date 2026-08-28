# LANSEIR / CADRE Foundation Sync — v1.0.0

Canonical promotion package generated from the FULL SEND approval on 2026-08-26.

## KISS placement
1. Place ZIP at the CADRE repository root.
2. Extract into a staging branch/location first.
3. Reconcile these logical paths with the repository's existing canonical folder names.
4. Register promoted records in the existing Source-of-Truth Registry.
5. Validate hashes and confirm no newer canonical record is overwritten.
6. Commit as one atomic foundation-sync change.

## Critical rule
Do not create a parallel doctrine tree if equivalent canonical folders already exist. Merge by authority and registry ID.

## Migration-critical records
- `01_intelligence/lanseir_expression_profile.md`
- `03_migration/lanseir_inheritance_pack_spec.md`
- associated governance and source-of-truth records

## Validation
Confirm all files in `manifest.json` exist and SHA-256 hashes match.
